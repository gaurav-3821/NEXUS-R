from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import math
from typing import Sequence

from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry


@dataclass
class RetrievalQuery:
    normalized_input: str
    action_type: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    max_results: int = 10
    min_score: float = 0.3


@dataclass
class RankedETDEntry:
    entry: IndexedETDEntry
    score: float
    matched_fields: list[str] = field(default_factory=list)


W1_TEXT_SIM = 0.50
W2_TYPE_MATCH = 0.25
W3_RECENCY = 0.15
W4_STALENESS = 0.10


class ETDRetriever:
    def __init__(self, store: ETDStore) -> None:
        self._store = store

    def retrieve(self, query: RetrievalQuery) -> list[RankedETDEntry]:
        candidates = self._store.list_active()
        if not candidates:
            return []
        query_embedding = self._compute_embedding(query.normalized_input)
        scored: list[RankedETDEntry] = []
        for candidate in candidates:
            score, fields = self._compute_score(candidate, query, query_embedding)
            if score >= query.min_score:
                scored.append(RankedETDEntry(
                    entry=candidate,
                    score=round(score, 4),
                    matched_fields=fields,
                ))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:query.max_results]

    def _compute_score(
        self,
        candidate: IndexedETDEntry,
        query: RetrievalQuery,
        query_embedding: list[float],
    ) -> tuple[float, list[str]]:
        fields: list[str] = []
        text_sim = self._cosine_similarity(query_embedding, candidate.entry.intent_embedding)
        if text_sim > 0.0:
            fields.append("text_similarity")
        type_match = 1.0 if self._action_type_matches(candidate, query) else 0.0
        if type_match > 0.0:
            fields.append("type_match")
        recency = self._compute_recency(candidate)
        if recency > 0.0:
            fields.append("recency")
        stale_penalty = self._compute_stale_penalty(candidate)
        if stale_penalty > 0.0:
            fields.append("staleness_penalty")
        score = (
            W1_TEXT_SIM * text_sim
            + W2_TYPE_MATCH * type_match
            + W3_RECENCY * recency
            - W4_STALENESS * stale_penalty
        )
        return max(0.0, score), fields

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def _action_type_matches(self, candidate: IndexedETDEntry, query: RetrievalQuery) -> bool:
        if not query.action_type:
            return False
        candidate_sig = candidate.entry.intent_signature.lower()
        query_type = query.action_type.lower()
        query_normalized = query_type.replace("_", "-").replace(" ", "-")
        candidate_normalized = candidate_sig.replace("_", "-").replace(" ", "-")
        return query_normalized in candidate_normalized or candidate_normalized.startswith(query_normalized)

    def _compute_recency(self, candidate: IndexedETDEntry) -> float:
        try:
            created = datetime.fromisoformat(candidate.created_at)
        except (ValueError, TypeError):
            return 0.0
        now = datetime.now(timezone.utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days = (now - created).days
        ttl = candidate.ttl_days
        if ttl <= 0:
            return 1.0
        return 1.0 - min(days / ttl, 1.0)

    def _compute_stale_penalty(self, candidate: IndexedETDEntry) -> float:
        if candidate.hit_count == 0:
            try:
                created = datetime.fromisoformat(candidate.created_at)
            except (ValueError, TypeError):
                return 0.1
            now = datetime.now(timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days = (now - created).days
            if days >= 60:
                return 0.1
        return 0.0

    def _compute_embedding(self, text: str) -> list[float]:
        return compute_embedding(text)


def compute_embedding(text: str) -> list[float]:
    h = hashlib.sha256(text.encode()).hexdigest()
    seed = int(h[:8], 16)
    rng = _SimpleRNG(seed)
    return [rng.next() for _ in range(128)]


class _SimpleRNG:
    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next(self) -> float:
        self._state = (self._state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._state >> 16) / 65536.0 * 2.0 - 1.0
