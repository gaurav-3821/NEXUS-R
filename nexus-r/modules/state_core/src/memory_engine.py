"""Semantic Episodic Memory Engine for NEXUS-R.

Provides persistent semantic memory with embedding-based retrieval,
importance scoring, temporal decay, and hybrid ranking. Operates
fully offline using Ollama embeddings or lightweight TF-IDF fallback.

Storage: SQLite table `semantic_memories` in the existing events database.
Embeddings: Ollama /api/embeddings (nomic-embed-text) or TF-IDF fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite
import httpx

logger = logging.getLogger("nexus-r.memory")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MEMORY_CATEGORIES = (
    "preference", "project", "workflow", "skill",
    "goal", "frustration", "general",
)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "preference": [
        "i prefer", "i like", "i want", "always use", "i hate",
        "don't use", "never use", "my favorite", "i love",
    ],
    "project": [
        "i'm building", "my project", "working on", "my app",
        "my codebase", "my repo", "developing", "i created",
    ],
    "workflow": [
        "my workflow", "i usually", "my process", "i typically",
        "my routine", "my pipeline", "every time i",
    ],
    "skill": [
        "i know", "i'm experienced", "i'm familiar", "my expertise",
        "i specialize", "my background", "i studied",
    ],
    "goal": [
        "i want to", "my goal", "i'm trying to", "i need to",
        "i plan to", "aiming for", "target is",
    ],
    "frustration": [
        "i'm frustrated", "i hate when", "annoying", "keeps failing",
        "doesn't work", "broken", "confused by",
    ],
}

# Importance scoring weights
IMPORTANCE_WEIGHTS = {
    "response_length": 0.15,
    "technical_terms": 0.20,
    "user_preference": 0.25,
    "project_goal": 0.20,
    "novelty": 0.20,
}

IMPORTANCE_THRESHOLD = 0.35
MAX_MEMORIES = 500
EMBEDDING_DIM_DEFAULT = 768
DEDUP_SIMILARITY_THRESHOLD = 0.85
DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"
EMBEDDING_MODEL = "nomic-embed-text"


class SemanticMemoryEngine:
    """Adaptive semantic memory with embedding-based retrieval.
    
    Provides:
    - Memory extraction from conversations (importance-filtered)
    - Embedding generation via Ollama
    - Semantic similarity search for context retrieval
    - Temporal decay and confidence-based ranking
    - Deduplication via cosine similarity
    - Full CRUD for memory management
    """

    def __init__(
        self,
        db_path: str | Path,
        ollama_base: str = DEFAULT_OLLAMA_BASE,
    ) -> None:
        self.db_path = str(Path(db_path))
        self.ollama_base = ollama_base
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._db: aiosqlite.Connection | None = None
        self._embed_dim: int | None = None
        self._embed_cache: dict[str, list[float]] = {}
        self._embed_cache_order: list[str] = []
        self._injection_cache: dict[str, tuple[float, str]] = {}

    async def initialize(self) -> None:
        """Create the semantic_memories table if it doesn't exist."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self.db_path, timeout=5)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA busy_timeout=5000")
            await self._db.execute("PRAGMA synchronous=NORMAL")
            await self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding_json TEXT,
                    confidence REAL DEFAULT 0.5,
                    created_at REAL NOT NULL,
                    reinforced_at REAL NOT NULL,
                    reinforcement_count INTEGER DEFAULT 1,
                    conversation_id TEXT,
                    source TEXT DEFAULT 'extracted',
                    metadata_json TEXT
                )
                """
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_category ON semantic_memories(category)"
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_source ON semantic_memories(source)"
            )
            await self._db.commit()
            self._initialized = True
            logger.info("Semantic memory engine initialized (db=%s)", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    async def _embed(self, text: str) -> list[float]:
        """Generate embedding vector via Ollama API.
        
        Falls back to simple TF-IDF-like hash vector if Ollama is unavailable.
        """
        if text in self._embed_cache:
            return self._embed_cache[text]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.ollama_base}/api/embeddings",
                    json={"model": EMBEDDING_MODEL, "prompt": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        if self._embed_dim is None:
                            self._embed_dim = len(embedding)
                        
                        self._embed_cache[text] = embedding
                        self._embed_cache_order.append(text)
                        if len(self._embed_cache_order) > 100:
                            oldest = self._embed_cache_order.pop(0)
                            self._embed_cache.pop(oldest, None)
                        
                        return embedding
        except Exception as e:
            logger.debug("Ollama embedding failed, using fallback: %s", e)

        # Fallback: deterministic hash-based vector (for offline operation)
        fallback = self._fallback_embed(text)
        self._embed_cache[text] = fallback
        self._embed_cache_order.append(text)
        if len(self._embed_cache_order) > 100:
            oldest = self._embed_cache_order.pop(0)
            self._embed_cache.pop(oldest, None)
        return fallback

    def _fallback_embed(self, text: str, dim: int = 384) -> list[float]:
        """Simple deterministic embedding fallback using character trigram hashing."""
        vector = [0.0] * dim
        text_lower = text.lower()
        words = text_lower.split()
        for i, word in enumerate(words):
            for j in range(max(1, len(word) - 2)):
                trigram = word[j:j+3]
                idx = hash(trigram) % dim
                vector[idx] += 1.0 / (1 + i * 0.01)
        # Normalize
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # ------------------------------------------------------------------
    # Memory Extraction
    # ------------------------------------------------------------------

    async def extract_memories(
        self,
        user_msg: str,
        assistant_msg: str,
        conversation_id: str | None = None,
    ) -> list[str]:
        """Extract and store meaningful memories from a conversation turn.
        
        Returns list of created memory IDs.
        """
        await self.initialize()

        importance = self._score_importance(user_msg, assistant_msg)
        if importance < IMPORTANCE_THRESHOLD:
            logger.debug(
                "Conversation below importance threshold (%.2f < %.2f), skipping",
                importance, IMPORTANCE_THRESHOLD,
            )
            return []

        # Build memory content — focus on what the USER said/revealed
        memory_content = self._extract_memory_text(user_msg, assistant_msg)
        if not memory_content or len(memory_content) < 10:
            return []

        category = self._classify_category(user_msg)
        embedding = await self._embed(memory_content)

        # Deduplication check
        is_dup = await self._is_duplicate(embedding, memory_content)
        if is_dup:
            logger.debug("Memory deduplicated (too similar to existing)")
            return []

        # Enforce memory cap
        await self._enforce_memory_cap()

        # Store
        memory_id = str(uuid4())
        now = time.time()
        confidence = min(1.0, importance * 1.2)

        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO semantic_memories
                (id, category, content, embedding_json, confidence,
                 created_at, reinforced_at, reinforcement_count,
                 conversation_id, source, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                category,
                memory_content,
                json.dumps(embedding),
                round(confidence, 4),
                now,
                now,
                1,
                conversation_id,
                "extracted",
                json.dumps({
                    "importance_score": round(importance, 3),
                    "user_msg_preview": user_msg[:100],
                }),
            ),
        )
        await self._db.commit()

        logger.info(
            "Stored memory [%s] category=%s confidence=%.2f: %s",
            memory_id[:8], category, confidence, memory_content[:60],
        )
        return [memory_id]

    def _score_importance(self, user_msg: str, assistant_msg: str) -> float:
        """Score the importance of a conversation turn [0.0, 1.0]."""
        scores: dict[str, float] = {}

        # Response length
        resp_len = len(assistant_msg)
        scores["response_length"] = min(resp_len / 500.0, 1.0) if resp_len > 50 else 0.0

        # Technical terms
        technical_patterns = [
            r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\bfunction\b",
            r"\bapi\b", r"\bdatabase\b", r"\balgorithm\b", r"\bmodel\b",
            r"\bembedding\b", r"\bvector\b", r"\bquery\b", r"\bschema\b",
            r"\btensor\b", r"\bgradient\b", r"\bneural\b", r"\bpipeline\b",
        ]
        user_lower = user_msg.lower()
        tech_count = sum(1 for p in technical_patterns if re.search(p, user_lower))
        scores["technical_terms"] = min(tech_count / 4.0, 1.0)

        # User preference language
        pref_patterns = CATEGORY_KEYWORDS.get("preference", [])
        pref_count = sum(1 for p in pref_patterns if p in user_lower)
        scores["user_preference"] = min(pref_count / 2.0, 1.0)

        # Project/goal language
        proj_patterns = (
            CATEGORY_KEYWORDS.get("project", [])
            + CATEGORY_KEYWORDS.get("goal", [])
        )
        proj_count = sum(1 for p in proj_patterns if p in user_lower)
        scores["project_goal"] = min(proj_count / 2.0, 1.0)

        # Novelty placeholder (will be computed during dedup check)
        scores["novelty"] = 0.6  # Default moderate novelty

        total = sum(
            scores[k] * IMPORTANCE_WEIGHTS[k]
            for k in IMPORTANCE_WEIGHTS
            if k in scores
        )
        return min(total, 1.0)

    def _extract_memory_text(self, user_msg: str, assistant_msg: str) -> str:
        """Extract the most memorable content from the exchange.
        
        Focuses on what the user revealed about themselves, their projects,
        and their preferences rather than raw Q&A content.
        """
        user_lower = user_msg.lower()

        # Check for explicit preference/project statements
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in user_lower:
                    # Use user message directly as memory
                    return f"[{category}] {user_msg.strip()}"

        # For general technical exchanges, summarize the topic
        words = user_msg.split()
        if len(words) > 15:
            return f"[general] User discussed: {' '.join(words[:30])}..."
        elif len(words) > 5:
            return f"[general] User asked about: {user_msg.strip()}"

        return ""

    def _classify_category(self, user_msg: str) -> str:
        """Classify memory into a category based on keyword matching."""
        user_lower = user_msg.lower()
        best_category = "general"
        best_score = 0

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in user_lower)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    async def _is_duplicate(
        self, embedding: list[float], content: str
    ) -> bool:
        """Check if a similar memory already exists."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT id, embedding_json, content, reinforcement_count, confidence FROM semantic_memories"
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            if row["embedding_json"]:
                existing_emb = json.loads(row["embedding_json"])
                sim = self._cosine_similarity(embedding, existing_emb)
                if sim > DEDUP_SIMILARITY_THRESHOLD:
                    # Reinforce existing memory instead of creating duplicate
                    now = time.time()
                    new_count = (row["reinforcement_count"] or 1) + 1
                    new_confidence = min(1.0, (row["confidence"] or 0.5) * 0.8 + 0.2)
                    await self._db.execute(
                        """
                        UPDATE semantic_memories
                        SET reinforced_at = ?, reinforcement_count = ?, confidence = ?
                        WHERE id = ?
                        """,
                        (now, new_count, round(new_confidence, 4), row["id"]),
                    )
                    await self._db.commit()
                    logger.debug(
                        "Reinforced existing memory %s (sim=%.2f, count=%d)",
                        row["id"][:8], sim, new_count,
                    )
                    return True

        return False

    async def _enforce_memory_cap(self) -> None:
        """Remove oldest low-confidence memories if at capacity."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM semantic_memories"
        ) as cursor:
            row = await cursor.fetchone()
            count = row["cnt"] if row else 0

        if count >= MAX_MEMORIES:
            # Delete lowest-scored memories
            to_delete = count - MAX_MEMORIES + 10  # Free some headroom
            await self._db.execute(
                f"""
                DELETE FROM semantic_memories WHERE id IN (
                    SELECT id FROM semantic_memories
                    ORDER BY confidence * (1.0 / (1.0 + (({time.time()} - reinforced_at) / 86400.0)))
                    ASC LIMIT ?
                )
                """,
                (to_delete,),
            )
            await self._db.commit()
            logger.info("Pruned %d low-value memories (cap=%d)", to_delete, MAX_MEMORIES)

    # ------------------------------------------------------------------
    # Memory Retrieval
    # ------------------------------------------------------------------

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.35,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant memories for a query using semantic similarity.
        
        Returns top-K memories ranked by hybrid score (similarity + recency + confidence).
        """
        await self.initialize()
        assert self._db is not None

        query_embedding = await self._embed(query)

        async with self._db.execute(
            """
            SELECT id, category, content, embedding_json, confidence,
                   created_at, reinforced_at, reinforcement_count,
                   conversation_id, source, metadata_json
            FROM semantic_memories
            """
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return []

        candidates = []
        now = time.time()

        for row in rows:
            if not row["embedding_json"]:
                continue

            emb = json.loads(row["embedding_json"])
            sim = self._cosine_similarity(query_embedding, emb)

            if sim < min_similarity * 0.5:
                # Skip very low similarity to avoid noise
                continue

            age_days = (now - (row["reinforced_at"] or row["created_at"])) / 86400.0
            freshness = 0.5 ** (age_days / 14.0)  # 14-day half-life
            confidence = (row["confidence"] or 0.5) * (
                1 + 0.05 * min(row["reinforcement_count"] or 1, 10)
            )
            confidence = min(confidence, 1.0)

            # Conversation continuity bonus
            conv_bonus = 0.15 if (
                conversation_id
                and row["conversation_id"] == conversation_id
            ) else 0.0

            final_score = (
                0.40 * sim
                + 0.20 * freshness
                + 0.20 * confidence
                + 0.10 * self._category_relevance(query, row["category"])
                + 0.10 * conv_bonus
            )

            if final_score >= min_similarity:
                candidates.append({
                    "id": row["id"],
                    "category": row["category"],
                    "content": row["content"],
                    "similarity": round(sim, 3),
                    "freshness": round(freshness, 3),
                    "confidence": round(row["confidence"] or 0.5, 3),
                    "final_score": round(final_score, 3),
                    "age_days": round(age_days, 1),
                    "reinforcement_count": row["reinforcement_count"] or 1,
                    "conversation_id": row["conversation_id"],
                    "source": row["source"],
                })

        # Sort by final score descending, take top K
        candidates.sort(key=lambda m: m["final_score"], reverse=True)
        return candidates[:top_k]

    def _category_relevance(self, query: str, category: str) -> float:
        """Score category relevance based on query content."""
        query_lower = query.lower()
        if category == "general":
            return 0.3
        keywords = CATEGORY_KEYWORDS.get(category, [])
        matches = sum(1 for kw in keywords if kw in query_lower)
        return min(matches * 0.3, 1.0)

    async def get_context_injection(
        self,
        query: str,
        max_memories: int = 5,
        conversation_id: str | None = None,
    ) -> str:
        """Generate a prompt context block from relevant memories.
        
        Returns a formatted string ready for injection into the LLM prompt,
        or empty string if no relevant memories found.
        """
        # Skip for trivial/short messages to save massive latency
        if len(query.split()) < 5:
            return ""

        # Check 5s TTL cache
        cache_key = f"{conversation_id}:{query}:{max_memories}"
        if cache_key in self._injection_cache:
            mtime, result = self._injection_cache[cache_key]
            if time.time() - mtime < 5.0:
                return result

        memories = await self.recall(
            query, top_k=max_memories, conversation_id=conversation_id
        )
        if not memories:
            return ""

        lines = ["[CONTEXTUAL MEMORY]", "Relevant past context:"]
        for mem in memories:
            sim_pct = int(mem["similarity"] * 100)
            age_str = self._format_age(mem["age_days"])
            content = mem["content"].replace("[general] ", "").replace("[preference] ", "")
            lines.append(f"- ({sim_pct}% match, {age_str}) {content}")

        lines.append("[/CONTEXTUAL MEMORY]")
        result = "\n".join(lines)
        self._injection_cache[cache_key] = (time.time(), result)
        
        # Keep cache size bounded (max 50)
        if len(self._injection_cache) > 50:
            oldest = min(self._injection_cache.keys(), key=lambda k: self._injection_cache[k][0])
            del self._injection_cache[oldest]
            
        return result

    @staticmethod
    def _format_age(age_days: float) -> str:
        """Format age into human-readable string."""
        if age_days < 0.04:  # ~1 hour
            return "just now"
        elif age_days < 1:
            hours = int(age_days * 24)
            return f"{hours}h ago"
        elif age_days < 7:
            return f"{int(age_days)}d ago"
        elif age_days < 30:
            weeks = int(age_days / 7)
            return f"{weeks}w ago"
        else:
            months = int(age_days / 30)
            return f"{months}mo ago"

    # ------------------------------------------------------------------
    # Memory Management (CRUD)
    # ------------------------------------------------------------------

    async def add_explicit_memory(
        self,
        content: str,
        category: str = "preference",
        conversation_id: str | None = None,
    ) -> str:
        """Add an explicit user-created memory."""
        await self.initialize()
        assert self._db is not None

        memory_id = str(uuid4())
        now = time.time()
        embedding = await self._embed(content)

        # Check for dedup
        is_dup = await self._is_duplicate(embedding, content)
        if is_dup:
            logger.info("Explicit memory deduplicated — reinforced existing")
            return "reinforced"

        await self._db.execute(
            """
            INSERT INTO semantic_memories
                (id, category, content, embedding_json, confidence,
                 created_at, reinforced_at, reinforcement_count,
                 conversation_id, source, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id, category, content, json.dumps(embedding),
                0.9,  # Explicit memories get high confidence
                now, now, 1, conversation_id, "explicit", "{}",
            ),
        )
        await self._db.commit()
        return memory_id

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        await self.initialize()
        assert self._db is not None
        result = await self._db.execute(
            "DELETE FROM semantic_memories WHERE id = ?", (memory_id,)
        )
        await self._db.commit()
        return result.rowcount > 0

    async def get_all_memories(
        self, include_embeddings: bool = False
    ) -> list[dict[str, Any]]:
        """Get all stored memories for the Memory Center UI."""
        await self.initialize()
        assert self._db is not None

        async with self._db.execute(
            """
            SELECT id, category, content, confidence, created_at,
                   reinforced_at, reinforcement_count, conversation_id,
                   source, metadata_json
            FROM semantic_memories
            ORDER BY reinforced_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()

        now = time.time()
        results = []
        for row in rows:
            age_days = (now - (row["reinforced_at"] or row["created_at"])) / 86400.0
            decay = 0.5 ** (age_days / 14.0)
            effective_confidence = (row["confidence"] or 0.5) * decay

            results.append({
                "id": row["id"],
                "category": row["category"],
                "content": row["content"],
                "confidence": round(row["confidence"] or 0.5, 3),
                "effective_confidence": round(effective_confidence, 3),
                "created_at": row["created_at"],
                "reinforced_at": row["reinforced_at"],
                "age_days": round(age_days, 1),
                "reinforcement_count": row["reinforcement_count"] or 1,
                "conversation_id": row["conversation_id"],
                "source": row["source"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            })

        return results

    async def get_stats(self) -> dict[str, Any]:
        """Get memory statistics for the dashboard."""
        await self.initialize()
        assert self._db is not None

        async with self._db.execute(
            "SELECT COUNT(*) as total FROM semantic_memories"
        ) as cursor:
            total = (await cursor.fetchone())["total"]

        async with self._db.execute(
            """
            SELECT category, COUNT(*) as cnt
            FROM semantic_memories
            GROUP BY category
            """
        ) as cursor:
            categories = {
                row["category"]: row["cnt"]
                async for row in cursor
            }

        async with self._db.execute(
            """
            SELECT source, COUNT(*) as cnt
            FROM semantic_memories
            GROUP BY source
            """
        ) as cursor:
            sources = {
                row["source"]: row["cnt"]
                async for row in cursor
            }

        async with self._db.execute(
            "SELECT AVG(confidence) as avg_conf FROM semantic_memories"
        ) as cursor:
            avg_conf = (await cursor.fetchone())["avg_conf"] or 0.0

        async with self._db.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) as total_bytes FROM semantic_memories"
        ) as cursor:
            total_bytes = (await cursor.fetchone())["total_bytes"]

        async with self._db.execute(
            "SELECT MIN(created_at) as oldest, MAX(created_at) as newest FROM semantic_memories"
        ) as cursor:
            row = await cursor.fetchone()
            oldest_ts = row["oldest"] if row else None
            newest_ts = row["newest"] if row else None

        def _fmt_ts(ts: float | None) -> str | None:
            if ts is None:
                return None
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        return {
            "total_memories": total,
            "total_size_bytes": total_bytes,
            "oldest_memory_date": _fmt_ts(oldest_ts),
            "newest_memory_date": _fmt_ts(newest_ts),
            "max_capacity": MAX_MEMORIES,
            "categories": categories,
            "sources": sources,
            "average_confidence": round(avg_conf, 3),
            "embedding_model": EMBEDDING_MODEL,
        }

    async def clear_all(self) -> int:
        """Delete all memories. Returns count deleted."""
        await self.initialize()
        assert self._db is not None
        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM semantic_memories"
        ) as cursor:
            count = (await cursor.fetchone())["cnt"]
        await self._db.execute("DELETE FROM semantic_memories")
        await self._db.commit()
        return count

    async def rebuild_index(self) -> int:
        """Re-embed all stored memories via Ollama.
        
        Returns count of successfully re-embedded memories.
        """
        await self.initialize()
        assert self._db is not None

        async with self._db.execute(
            "SELECT id, content FROM semantic_memories"
        ) as cursor:
            rows = await cursor.fetchall()

        rebuilt = 0
        for row in rows:
            embedding = await self._embed(row["content"])
            await self._db.execute(
                "UPDATE semantic_memories SET embedding_json = ? WHERE id = ?",
                (json.dumps(embedding), row["id"]),
            )
            rebuilt += 1

        if rebuilt:
            await self._db.commit()
            logger.info("Rebuilt embeddings for %d memories", rebuilt)
        return rebuilt

    async def optimize(self) -> dict[str, int]:
        """Run both decay-and-prune and cache clear.
        
        Returns dict with counts of pruned and remaining memories.
        """
        pruned = await self.decay_and_prune()
        self._embed_cache.clear()
        self._embed_cache_order.clear()
        self._injection_cache.clear()
        stats = await self.get_stats()
        return {
            "pruned": pruned,
            "remaining": stats["total_memories"],
        }

    async def decay_and_prune(self, min_effective_confidence: float = 0.15) -> int:
        """Prune memories that have decayed below threshold.
        
        Returns count of pruned memories.
        """
        await self.initialize()
        assert self._db is not None
        now = time.time()

        async with self._db.execute(
            "SELECT id, confidence, reinforced_at FROM semantic_memories"
        ) as cursor:
            rows = await cursor.fetchall()

        to_delete = []
        for row in rows:
            age_days = (now - (row["reinforced_at"] or now)) / 86400.0
            decay = 0.5 ** (age_days / 14.0)
            effective = (row["confidence"] or 0.5) * decay
            if effective < min_effective_confidence:
                to_delete.append(row["id"])

        if to_delete:
            placeholders = ",".join("?" for _ in to_delete)
            await self._db.execute(
                f"DELETE FROM semantic_memories WHERE id IN ({placeholders})",
                to_delete,
            )
            await self._db.commit()
            logger.info("Pruned %d decayed memories", len(to_delete))

        return len(to_delete)
