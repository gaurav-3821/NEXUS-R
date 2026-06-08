"""MemoryManager — core CRUD, extraction, optimisation, and BlackboardState logic.

Uses SQLite for persistence via the ``Database`` class (aiosqlite).
"""

from __future__ import annotations

import difflib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from nexus_r.memory.database import Database
from nexus_r.memory.models import BlackboardState, MemoryStats, UserFact
from nexus_r.memory.vector_store import VectorStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Toggle state — used by routes.py toggle endpoints
# ---------------------------------------------------------------------------

_toggles: dict[str, bool] = {
    "persistent_mode": True,
    "smart_mode": True,
}


def get_toggles() -> dict[str, bool]:
    return dict(_toggles)


def set_toggle(name: str, value: bool) -> dict[str, bool]:
    if name in _toggles:
        _toggles[name] = value
    return get_toggles()


_ACTIVE_FORGETTING_DAYS = 30

# ---------------------------------------------------------------------------
# LLM extraction — uses litellm with fallback: cloud → local Ollama
# ---------------------------------------------------------------------------

_DEEPSEEK_MODEL = "openai/deepseek-chat"
_DEEPSEEK_BASE = "https://api.deepseek.com"
_OLLAMA_BASE = "http://127.0.0.1:11434"


def _get_deepseek_key() -> str | None:
    import os
    return os.environ.get("NEXUS_OPENCODE_API_KEY") or os.environ.get("NEXUS_BYOK_API_KEY") or None


async def _call_llm(system: str, user: str) -> str | None:
    """Call an LLM via litellm (cloud), falling back to local Ollama."""
    key = _get_deepseek_key()
    if key:
        try:
            from litellm import acompletion
            resp = await acompletion(
                model=_DEEPSEEK_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                api_key=key,
                api_base=_DEEPSEEK_BASE,
                temperature=0.0,
                timeout=30,
            )
            return resp.choices[0].message.content
        except Exception:
            pass

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_OLLAMA_BASE}/api/chat",
                json={
                    "model": "llama3.2:3b",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content")
    except Exception:
        return None


async def _extract_facts_from_messages(history: list[str], max_facts: int = 15) -> list[dict]:
    """Extract facts from a batch of chat messages via LLM."""
    if not history:
        return []

    conversation = "\n".join(
        f"{'User' if i % 2 == 0 else 'Assistant'}: {msg}"
        for i, msg in enumerate(history)
    )
    system = (
        "You are a memory extraction system. Extract factual statements about the user "
        "from the conversation below. Output ONLY a valid JSON array of objects:\n"
        "  - fact_text (string): the factual statement\n"
        "  - importance_score (float 0.0-1.0)\n"
        "  - confidence (float 0.0-1.0)\n"
        "  - type (string): \"semantic\", \"golden\", \"persistent\", or \"smart\"\n\n"
        "Rules:\n"
        "- Only facts about the user: preferences, habits, identity, explicit requests\n"
        "- Be conservative; prefer shorter atomic statements\n"
        "- Default type is \"semantic\"\n"
        "- Return [] if no useful facts found"
    )
    content = await _call_llm(system, f"Conversation:\n{conversation}")
    if content:
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            facts = json.loads(content)
            if isinstance(facts, list):
                return [
                    {**f, "importance_score": f.get("importance_score", 0.5),
                     "confidence": f.get("confidence", 0.5), "type": f.get("type", "semantic")}
                    for f in facts[:max_facts] if isinstance(f, dict) and isinstance(f.get("fact_text"), str)
                ]
        except json.JSONDecodeError:
            pass

    return _fallback_extract_facts(history, max_facts)


async def _generate_summary(facts: list[UserFact], prior_summary: str = "") -> str:
    """Generate a 3-sentence summary from extracted facts via LLM."""
    if not facts:
        return prior_summary or (
            "No information has been extracted yet. "
            "The system is still learning from conversations. "
            "Check back after more interactions."
        )

    top = sorted(facts, key=lambda f: f.importance_score, reverse=True)[:10]
    system = "You are a memory compression system. Compress the following facts into exactly 3 concise sentences. Output ONLY the 3 sentences."
    user = f"Existing summary:\n{prior_summary}\n\nFacts:\n" + "\n".join(f"- {f.fact_text}" for f in top) if prior_summary else "Facts:\n" + "\n".join(f"- {f.fact_text}" for f in top)

    content = await _call_llm(system, user)
    if content:
        content = content.strip().replace("```", "").strip()
        return _coerce_three_sentences(content, top)

    return _fallback_summary(facts, prior_summary)


# ---------------------------------------------------------------------------
# Fallback heuristics (used when no LLM is available)
# ---------------------------------------------------------------------------

def _fallback_extract_facts(history: list[str], max_facts: int = 15) -> list[dict]:
    facts: list[dict] = []
    for msg in history:
        sentences = [s.strip() for s in msg.split(".") if len(s.strip()) > 20]
        for i, sent in enumerate(sentences[:2]):
            if len(facts) >= max_facts:
                break
            facts.append({
                "fact_text": sent,
                "importance_score": round(0.3 + (i * 0.15), 2),
                "confidence": round(0.5 + (i * 0.1), 2),
                "type": "semantic",
            })
        if len(facts) >= max_facts:
            break
    return facts


def _fallback_summary(facts: list[UserFact], prior_summary: str = "") -> str:
    if not facts:
        return prior_summary or (
            "No information has been extracted yet. "
            "The system is still learning from conversations. "
            "Check back after more interactions."
        )
    top = sorted(facts, key=lambda f: f.importance_score, reverse=True)[:5]
    summaries: list[str] = []
    for f in top:
        words = f.fact_text.split()
        if len(words) > 5:
            sentence = " ".join(words[:12]) + "."
            if sentence not in summaries:
                summaries.append(sentence)
        if len(summaries) >= 3:
            break
    while len(summaries) < 3:
        summaries.append(f"Memory stores {len(facts)} key facts across conversations.")
    return " ".join(summaries[:3])


def _coerce_three_sentences(text: str, top: list[UserFact]) -> str:
    sentences = [s.strip().rstrip(".") for s in text.replace("\n", ". ").split(". ") if s.strip()]
    if not sentences:
        return _fallback_summary(top)
    return ". ".join(sentences[:3]) + "."


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """Manages fact persistence, retrieval, stats, optimisation, and lifecycle.

    Each public method maps 1:1 to a FastAPI endpoint expected by the frontend.
    All data is persisted to a SQLite database via the ``Database`` class.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.
    vector_store : VectorStore or None
        Optional ChromaDB vector store for semantic search. If omitted,
        ``search_memories()`` falls back to full-text scan.
    """

    def __init__(self, db_path: str, vector_store: VectorStore | None = None) -> None:
        self._db = Database(db_path)
        self._vector_store = vector_store

    async def initialize(self) -> None:
        """Create tables. Safe to call multiple times."""
        await self._db.initialize()

    async def close(self) -> None:
        """Close the database connection."""
        await self._db.close()

    # ------------------------------------------------------------------ CRUD

    async def get_all(self, conversation_id: str | None = None) -> list[UserFact]:
        return await self._db.get_all_facts(conversation_id)

    async def get_by_id(self, fact_id: str) -> UserFact | None:
        return await self._db.get_fact(fact_id)

    async def save_fact(self, fact: UserFact) -> UserFact:
        saved = await self._db.upsert_fact(fact)
        if self._vector_store is not None:
            self._vector_store.add_fact(saved.id, saved.fact_text)
        return saved

    async def save_facts_bulk(self, facts: list[UserFact]) -> list[UserFact]:
        saved = await self._db.upsert_facts_bulk(facts)
        if self._vector_store is not None:
            self._vector_store.add_facts_bulk([(f.id, f.fact_text) for f in saved])
        return saved

    async def delete(self, fact_id: str) -> bool:
        deleted = await self._db.delete_fact(fact_id)
        if self._vector_store is not None:
            self._vector_store.delete_fact(fact_id)
        return deleted

    async def _delete_facts_by_ids(self, fact_ids: set[str]) -> None:
        await self._db.delete_facts_by_ids(fact_ids)
        if self._vector_store is not None:
            self._vector_store.delete_facts_by_ids(fact_ids)

    async def clear_all(self) -> int:
        fact_count = await self._db.delete_all_facts()
        await self._db.delete_all_boards()
        if self._vector_store is not None:
            self._vector_store.reset()
        return fact_count

    # ------------------------------------------------------------------ Stats

    async def get_stats(self) -> MemoryStats:
        facts = await self.get_all()
        return MemoryStats.from_facts(facts)

    # ------------------------------------------------------- touch / recency

    async def touch_fact(self, fact_id: str) -> bool:
        return await self._db.touch_fact(fact_id)

    # --------------------------------------------------------- vector search

    async def search_memories(self, query: str, limit: int = 3) -> list[UserFact]:
        """Semantically search stored facts and return full ``UserFact`` objects.

        Uses the ChromaDB vector store when available; falls back to a simple
        keyword-based scan if no vector store is configured.
        """
        if not query.strip():
            return []

        if self._vector_store is not None:
            ids = self._vector_store.query_facts(query, n_results=limit)
            if ids:
                facts = []
                for fid in ids:
                    f = await self._db.get_fact(fid)
                    if f is not None:
                        facts.append(f)
                return facts
            return []

        # Fallback: keyword scan over SQLite
        all_facts = await self._db.get_all_facts()
        scored = []
        query_lower = query.lower()
        for f in all_facts:
            score = f.relevance_score()
            if query_lower in f.fact_text.lower():
                score += 0.3
            scored.append((score, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:limit]]

    # --------------------------------------------------------- auto-extract

    async def auto_extract_and_compress(
        self,
        raw_chat_history: list[str],
        conversation_id: str = "__default__",
    ) -> BlackboardState:
        recent = raw_chat_history[-10:]

        raw_facts = await _extract_facts_from_messages(recent)
        new_facts = [
            UserFact(**rf, source_conversation_id=conversation_id)
            for rf in raw_facts
        ]
        await self.save_facts_bulk(new_facts)

        board = await self.get_or_create_board(conversation_id)
        board.extracted_facts.extend(new_facts)
        board.trim_facts_to_budget(board.current_task)
        board.compressed_summary = await _generate_summary(board.extracted_facts)
        board.updated_at = _utcnow()
        await self._db.upsert_board(board)
        return board

    # -------------------------------------------------------- score & prune

    async def score_and_prune(self, facts: list[UserFact]) -> list[UserFact]:
        now = _utcnow()
        max_age_seconds = _ACTIVE_FORGETTING_DAYS * 24 * 3600
        surviving_ids: set[str] = set()

        for fact in facts:
            ref = fact.last_referenced_at or fact.created_at
            age_seconds = (now - ref).total_seconds()
            recency_factor = max(0.0, 1.0 - (age_seconds / max_age_seconds))
            composite = (
                (fact.importance_score * fact.confidence) * 0.6
                + recency_factor * 0.4
            )
            if composite >= 0.2:
                surviving_ids.add(fact.id)

        pruned_ids = {f.id for f in facts} - surviving_ids
        await self._delete_facts_by_ids(pruned_ids)

        boards = await self._db.get_all_boards()
        for board in boards:
            board_facts = [
                f for f in (await self.get_all(board.conversation_id))
                if f.id in surviving_ids
            ]
            board.extracted_facts = board_facts
            board.trim_facts_to_budget(board.current_task)
            await self._db.upsert_board(board)

        return [f for f in facts if f.id in surviving_ids]

    # --------------------------------------------------------------- Rebuild

    async def rebuild(self, conversation_id: str | None = None) -> int:
        if conversation_id:
            board = await self._db.get_board(conversation_id)
            targets = [board] if board else []
        else:
            targets = await self._db.get_all_boards()

        rebuilt_count = 0
        for board in targets:
            raw_facts = await _extract_facts_from_messages(
                [board.compressed_summary] if board.compressed_summary else []
            )
            new_facts = [
                UserFact(**rf, source_conversation_id=board.conversation_id)
                for rf in raw_facts
            ]
            for f in new_facts:
                await self.save_fact(f)
            board.extracted_facts = await self.get_all(board.conversation_id)
            board.trim_facts_to_budget(board.current_task)
            await self._db.upsert_board(board)
            rebuilt_count += len(new_facts)

        return rebuilt_count

    # -------------------------------------------------------------- Optimise

    async def optimize(self) -> dict[str, int]:
        facts = await self.get_all()
        merged_ids: set[str] = set()
        kept: list[UserFact] = []
        merge_count = 0

        for i, a in enumerate(facts):
            if a.id in merged_ids:
                continue
            best_b = None
            best_ratio = 0.0
            for j, b in enumerate(facts):
                if i == j or b.id in merged_ids:
                    continue
                ratio = difflib.SequenceMatcher(
                    None, a.fact_text, b.fact_text
                ).ratio()
                if ratio >= 0.8 and ratio > best_ratio:
                    best_ratio = ratio
                    best_b = b

            if best_b is not None:
                merged = self._merge_facts(a, best_b)
                await self.delete(best_b.id)
                merged_ids.add(a.id)
                merged_ids.add(best_b.id)
                kept.append(merged)
                merge_count += 1
            else:
                kept.append(a)

        pruned_count = 0
        final: list[UserFact] = []
        for f in kept:
            if f.importance_score < 0.2:
                await self.delete(f.id)
                pruned_count += 1
            else:
                final.append(f)

        for f in final:
            if f.id not in {ff.id for ff in facts}:
                await self.save_fact(f)

        boards = await self._db.get_all_boards()
        for board in boards:
            surviving = [
                f for f in final
                if f.source_conversation_id == board.conversation_id
            ]
            board.extracted_facts = surviving
            board.trim_facts_to_budget(board.current_task)
            await self._db.upsert_board(board)

        return {"pruned": merge_count + pruned_count, "remaining": len(final)}

    # -------------------------------------------------------------- Helpers

    @staticmethod
    def _merge_facts(a: UserFact, b: UserFact) -> UserFact:
        now = _utcnow()
        return UserFact(
            id=a.id,
            fact_text=(
                a.fact_text if len(a.fact_text) >= len(b.fact_text)
                else b.fact_text
            ),
            importance_score=max(a.importance_score, b.importance_score),
            confidence=max(a.confidence, b.confidence),
            type=b.type if b.importance_score > a.importance_score else a.type,
            source_conversation_id=(
                a.source_conversation_id or b.source_conversation_id
            ),
            source_message_id=(
                a.source_message_id or b.source_message_id
            ),
            created_at=min(a.created_at, b.created_at),
            updated_at=now,
            expires_at=(
                max(a.expires_at, b.expires_at)
                if a.expires_at and b.expires_at
                else (a.expires_at or b.expires_at)
            ),
            last_referenced_at=(
                max(a.last_referenced_at, b.last_referenced_at)
                if a.last_referenced_at and b.last_referenced_at
                else (a.last_referenced_at or b.last_referenced_at)
            ),
        )

    # ------------------------------------------------------- Blackboard state

    async def get_or_create_board(self, conversation_id: str) -> BlackboardState:
        board = await self._db.get_board(conversation_id)
        if board:
            return board
        board = BlackboardState(conversation_id=conversation_id)
        await self._db.upsert_board(board)
        return board
