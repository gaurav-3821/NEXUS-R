from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite
import httpx

logger = logging.getLogger("nexus-r.golden_memory")

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768
DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"
SIMILARITY_THRESHOLD = 0.75  # Minimum similarity for dedup
MAX_GOLDEN_EXAMPLES = 200
RETRIEVAL_TOP_K = 3


@dataclass
class GoldenExample:
    id: str = ""
    query: str = ""
    query_embedding: list[float] | None = None
    reasoning_steps: str = ""
    final_result: str = ""
    task_type: str = "general"
    model_used: str = ""
    success_score: float = 1.0
    created_at: float = 0.0
    use_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class GoldenMemory:
    """Episodic memory for storing and retrieving 'golden examples' from cloud model responses.

    When the cloud model successfully handles a complex task, store the
    {query, reasoning, result} triplet as a Golden Example. Before the local
    model attempts a hard query, retrieve similar examples and inject the
    cloud's reasoning as few-shot context.
    """

    def __init__(
        self,
        db_path: str | Path,
        ollama_base: str = DEFAULT_OLLAMA_BASE,
    ):
        self.db_path = str(Path(db_path))
        self.ollama_base = ollama_base.rstrip("/")
        self._db: aiosqlite.Connection | None = None
        self._initialized = False
        self._embed_cache: dict[str, list[float]] = {}
        self._embed_cache_order: list[str] = []

    async def _ensure_db(self):
        if self._initialized:
            return
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS golden_memories (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                query_embedding_json TEXT,
                reasoning_steps TEXT NOT NULL DEFAULT '',
                final_result TEXT NOT NULL DEFAULT '',
                task_type TEXT NOT NULL DEFAULT 'general',
                model_used TEXT NOT NULL DEFAULT '',
                success_score REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                use_count INTEGER DEFAULT 0,
                metadata_json TEXT
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_golden_task_type ON golden_memories(task_type)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_golden_created ON golden_memories(created_at)"
        )
        await self._db.commit()
        self._initialized = True
        logger.info("GoldenMemory initialized (db=%s)", self.db_path)

    async def close(self):
        if self._db is not None:
            await self._db.close()
            self._db = None
        self._initialized = False

    async def store(
        self,
        query: str,
        reasoning_steps: str,
        final_result: str,
        task_type: str = "general",
        model_used: str = "",
        success_score: float = 1.0,
        metadata: dict | None = None,
    ) -> str | None:
        """Store a new golden example. Returns the example ID if stored, None if skipped (duplicate/low quality)."""
        if not query.strip() or not final_result.strip():
            return None
        if success_score < 0.3:
            logger.debug("Skipping golden memory: success_score too low (%.2f)", success_score)
            return None

        embedding = await self._embed(query)
        if await self._is_duplicate(embedding, query):
            logger.debug("Skipping golden memory: duplicate (similar query already exists)")
            return None

        await self._ensure_db()
        now = time.time()
        import uuid
        example_id = f"golden_{uuid.uuid4().hex[:12]}"

        count = await self._count()
        if count >= MAX_GOLDEN_EXAMPLES:
            await self._prune_oldest()

        await self._db.execute("""
            INSERT INTO golden_memories
                (id, query, query_embedding_json, reasoning_steps, final_result,
                 task_type, model_used, success_score, created_at, use_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            example_id,
            query.strip(),
            json.dumps(embedding),
            reasoning_steps,
            final_result,
            task_type,
            model_used,
            success_score,
            now,
            json.dumps(metadata or {}),
        ))
        await self._db.commit()
        logger.info("Stored golden example %s (task_type=%s, score=%.2f)", example_id, task_type, success_score)
        return example_id

    async def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[GoldenExample]:
        """Find the most similar golden examples for a given query."""
        await self._ensure_db()
        query_emb = await self._embed(query)

        async with self._db.execute("""
            SELECT id, query, query_embedding_json, reasoning_steps, final_result,
                   task_type, model_used, success_score, created_at, use_count, metadata_json
            FROM golden_memories
            ORDER BY created_at DESC
            LIMIT 100
        """) as cursor:
            rows = await cursor.fetchall()

        scored: list[tuple[float, GoldenExample]] = []
        for row in rows:
            emb_json = row["query_embedding_json"]
            if not emb_json:
                continue
            emb = json.loads(emb_json)
            sim = self._cosine_similarity(query_emb, emb)
            if sim > 0.3:
                scored.append((sim, GoldenExample(
                    id=row["id"],
                    query=row["query"],
                    reasoning_steps=row["reasoning_steps"],
                    final_result=row["final_result"],
                    task_type=row["task_type"],
                    model_used=row["model_used"],
                    success_score=row["success_score"],
                    created_at=row["created_at"],
                    use_count=row["use_count"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [ex for _, ex in scored[:top_k]]

        for ex in results:
            await self._db.execute(
                "UPDATE golden_memories SET use_count = use_count + 1 WHERE id = ?",
                (ex.id,),
            )
        await self._db.commit()

        return results

    async def format_few_shot(self, query: str, max_examples: int = 2) -> str:
        """Retrieve similar golden examples and format them as a few-shot prompt injection."""
        examples = await self.retrieve(query, top_k=max_examples)
        if not examples:
            return ""

        lines = [
            "<GOLDEN_EXAMPLES>",
            "The following are examples of how similar tasks were previously handled successfully.",
            "Study the approach shown and apply similar reasoning to the current query.",
            "",
        ]
        for i, ex in enumerate(examples, 1):
            lines.append(f"--- Example {i} (task: {ex.task_type}) ---")
            lines.append(f"User Query: {ex.query}")
            if ex.reasoning_steps:
                lines.append(f"Reasoning Approach:")
                lines.append(ex.reasoning_steps)
            lines.append(f"Result: {ex.final_result}")
            lines.append("")

        lines.append("</GOLDEN_EXAMPLES>")
        return "\n".join(lines)

    async def delete(self, example_id: str) -> bool:
        await self._ensure_db()
        cursor = await self._db.execute("DELETE FROM golden_memories WHERE id = ?", (example_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_stats(self) -> dict[str, Any]:
        await self._ensure_db()
        async with self._db.execute("SELECT COUNT(*) as count FROM golden_memories") as cursor:
            row = await cursor.fetchone()
            count = row["count"] if row else 0
        async with self._db.execute(
            "SELECT COUNT(*) as count FROM golden_memories WHERE use_count > 0"
        ) as cursor:
            row = await cursor.fetchone()
            used_count = row["count"] if row else 0
        async with self._db.execute(
            "SELECT task_type, COUNT(*) as cnt FROM golden_memories GROUP BY task_type ORDER BY cnt DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            by_type = {row["task_type"]: row["cnt"] for row in rows}
        return {
            "total_examples": count,
            "used_examples": used_count,
            "by_task_type": by_type,
        }

    async def clear(self):
        await self._ensure_db()
        await self._db.execute("DELETE FROM golden_memories")
        await self._db.commit()

    async def _count(self) -> int:
        async with self._db.execute("SELECT COUNT(*) as cnt FROM golden_memories") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def _prune_oldest(self):
        async with self._db.execute(
            "SELECT id FROM golden_memories ORDER BY use_count ASC, created_at ASC LIMIT 10"
        ) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            await self._db.execute("DELETE FROM golden_memories WHERE id = ?", (row["id"],))
        await self._db.commit()
        logger.info("Pruned %d oldest golden examples", len(rows))

    async def _embed(self, text: str) -> list[float]:
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
                        self._embed_cache[text] = embedding
                        self._embed_cache_order.append(text)
                        if len(self._embed_cache_order) > 100:
                            oldest = self._embed_cache_order.pop(0)
                            self._embed_cache.pop(oldest, None)
                        return embedding
        except Exception as e:
            logger.debug("Ollama embedding failed in GoldenMemory, using fallback: %s", e)

        fallback = self._fallback_embed(text)
        self._embed_cache[text] = fallback
        self._embed_cache_order.append(text)
        if len(self._embed_cache_order) > 100:
            oldest = self._embed_cache_order.pop(0)
            self._embed_cache.pop(oldest, None)
        return fallback

    def _fallback_embed(self, text: str, dim: int = 384) -> list[float]:
        vector = [0.0] * dim
        text_lower = text.lower()
        words = text_lower.split()
        for i, word in enumerate(words):
            for j in range(max(1, len(word) - 2)):
                trigram = word[j:j+3]
                idx = hash(trigram) % dim
                vector[idx] += 1.0 / (1 + i * 0.01)
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector

    async def _is_duplicate(self, embedding: list[float], query: str) -> bool:
        await self._ensure_db()
        async with self._db.execute(
            "SELECT query, query_embedding_json FROM golden_memories"
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            if row["query_embedding_json"]:
                existing_emb = json.loads(row["query_embedding_json"])
                sim = self._cosine_similarity(embedding, existing_emb)
                if sim > SIMILARITY_THRESHOLD:
                    return True
        return False

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
