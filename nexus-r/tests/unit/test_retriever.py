from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from uuid import uuid4

import pytest

from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.distiller import ToolStep
from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry
from modules.workflow_engine.src.retriever import (
    ETDRetriever,
    RetrievalQuery,
    RankedETDEntry,
)


def _make_rng(seed_text: str) -> list[float]:
    h = hashlib.sha256(seed_text.encode()).hexdigest()
    seed = int(h[:8], 16)
    state = seed & 0xFFFFFFFF
    vec: list[float] = []
    for _ in range(128):
        state = (state * 1103515245 + 12345) & 0xFFFFFFFF
        vec.append(((state >> 16) / 65536.0 * 2.0 - 1.0))
    return vec


def _make_entry(
    sig: str = "test",
    params: list[str] | None = None,
    actions: list[str] | None = None,
) -> ETDEntry:
    embedding = _make_rng(sig)
    return ETDEntry(
        id=f"etd_{uuid4().hex[:12]}",
        intent_signature=sig,
        intent_embedding=embedding,
        input_schema={},
        output_schema={},
        tool_sequence=[ToolStep(tool="terminal", action=a or "echo hi", verify="passed") for a in (actions or ["echo hi"])],
        parameter_slots=params or [],
        invariant_checks=[],
        success_count=1,
        failure_count=0,
        generalization_success_rate=1.0,
        last_validated=datetime.now(timezone.utc).isoformat(),
    )


def _store_with(entries: list[IndexedETDEntry]) -> ETDStore:
    s = ETDStore()
    for e in entries:
        s.add(e)
    return s


class TestETDRetriever:
    def test_empty_store_returns_empty(self) -> None:
        store = ETDStore()
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build"))
        assert result == []

    def test_exact_match_embedding_gives_high_score(self) -> None:
        sig = "build-node-app"
        entry = _make_entry(sig=sig)
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=5)
        store = _store_with([indexed])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input=sig))
        assert len(result) == 1
        assert result[0].score > 0.4
        assert "text_similarity" in result[0].matched_fields

    def test_different_embeddings_give_lower_score(self) -> None:
        query_emb = _make_rng("deploy")
        opposite_emb = [-x for x in query_emb]
        entry_high = _make_entry(sig="deploy-python-app")
        entry_high.intent_embedding = query_emb
        entry_low = _make_entry(sig="completely-unrelated")
        entry_low.intent_embedding = opposite_emb
        now = datetime.now(timezone.utc).isoformat()
        idx_high = IndexedETDEntry(entry=entry_high, created_at=now, hit_count=5)
        idx_low = IndexedETDEntry(entry=entry_low, created_at=now, hit_count=5)
        store = _store_with([idx_high, idx_low])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="deploy", max_results=10, min_score=0.0))
        assert len(result) == 2
        assert result[0].entry.entry.intent_signature == "deploy-python-app"
        assert result[0].score > result[1].score

    def test_action_type_match_adds_score(self) -> None:
        entry = _make_entry(sig="npm-build")
        other = _make_entry(sig="pip-install")
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=5)
        indexed2 = IndexedETDEntry(entry=other, created_at=now, hit_count=5)
        store = _store_with([indexed, indexed2])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build", action_type="npm", max_results=10, min_score=0.0))
        assert result[0].entry.entry.intent_signature == "npm-build"
        assert "type_match" in result[0].matched_fields

    def test_recency_older_entry_scores_lower(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        entry_new = _make_entry(sig="build-app")
        entry_old = _make_entry(sig="build-app")
        idx_new = IndexedETDEntry(entry=entry_new, created_at=now, hit_count=5)
        idx_old = IndexedETDEntry(entry=entry_old, created_at=old, hit_count=5)
        store = _store_with([idx_new, idx_old])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build-app", max_results=10, min_score=0.0))
        assert result[0].entry.entry.id == entry_new.id
        assert "recency" in result[0].matched_fields

    def test_stale_zero_hit_penalty(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        entry_hit = _make_entry(sig="build-app")
        entry_stale = _make_entry(sig="build-app")
        idx_hit = IndexedETDEntry(entry=entry_hit, created_at=now, hit_count=5)
        idx_stale = IndexedETDEntry(entry=entry_stale, created_at=old, hit_count=0)
        store = _store_with([idx_hit, idx_stale])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build-app", max_results=10, min_score=0.0))
        assert result[0].entry.entry.id == entry_hit.id

    def test_min_score_filters_low_scores(self) -> None:
        entry = _make_entry(sig="build-app")
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=5)
        store = _store_with([indexed])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="completely-unrelated", min_score=0.9))
        assert len(result) == 0

    def test_max_results_limits_return(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        entries = [_make_entry(sig=f"build-{i}") for i in range(5)]
        indexed = [IndexedETDEntry(entry=e, created_at=now, hit_count=5) for e in entries]
        store = _store_with(indexed)
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build", max_results=2, min_score=0.0))
        assert len(result) == 2

    def test_results_sorted_by_score_descending(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        e1 = _make_entry(sig="build-node-app")
        e2 = _make_entry(sig="deploy-python-app")
        i1 = IndexedETDEntry(entry=e1, created_at=now, hit_count=5)
        i2 = IndexedETDEntry(entry=e2, created_at=now, hit_count=5)
        store = _store_with([i1, i2])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build", max_results=10, min_score=0.0))
        assert result[0].score >= result[1].score

    def test_cosine_similarity_edge_cases(self) -> None:
        r = ETDRetriever(ETDStore())
        assert r._cosine_similarity([], []) == 0.0
        assert r._cosine_similarity([1.0], []) == 0.0
        assert r._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_no_action_type_no_type_match(self) -> None:
        entry = _make_entry(sig="npm-build")
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=5)
        store = _store_with([indexed])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="npm", action_type="", min_score=0.0))
        assert "type_match" not in result[0].matched_fields

    def test_invalidated_entries_excluded(self) -> None:
        entry = _make_entry(sig="build-app")
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=5, invalidated=True)
        store = _store_with([indexed])
        r = ETDRetriever(store)
        result = r.retrieve(RetrievalQuery(normalized_input="build-app"))
        assert len(result) == 0
