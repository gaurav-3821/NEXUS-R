from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from uuid import uuid4

import pytest

from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.distiller import ToolStep
from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry
from modules.workflow_engine.src.invalidator import (
    ETDInvalidator,
    ETDInvalidationRule,
    FAILURE_CASCADE_LIMIT,
    STALE_ZERO_HIT_DAYS,
    STALE_DEPRIORITIZE_DAYS,
)


def _make_entry(sig: str = "test") -> ETDEntry:
    embedding: list[float] = [0.1] * 128
    return ETDEntry(
        id=f"etd_{uuid4().hex[:12]}",
        intent_signature=sig,
        intent_embedding=embedding,
        input_schema={},
        output_schema={},
        tool_sequence=[ToolStep(tool="terminal", action="echo hi", verify="passed")],
        parameter_slots=[],
        invariant_checks=[],
        success_count=1,
        failure_count=0,
        generalization_success_rate=1.0,
        last_validated=datetime.now(timezone.utc).isoformat(),
    )


def _store_with(entries: list[IndexedETDEntry] | None = None) -> ETDStore:
    s = ETDStore()
    if entries:
        for e in entries:
            s.add(e)
    return s


class TestETDInvalidator:
    def test_fresh_entry_no_invalidation(self) -> None:
        store = _store_with()
        inv = ETDInvalidator(store)
        assert inv.check_ttl() is None
        assert inv.check_failure_cascade() is None
        assert inv.check_stale() is None

    def test_ttl_exceeded_invalidates(self) -> None:
        entry = _make_entry()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=old, ttl_days=1)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rule = inv.check_ttl()
        assert rule is not None
        assert rule.trigger == "ttl_exceeded"
        assert entry.id in rule.entry_ids
        assert store.get(entry.id) is not None
        assert store.get(entry.id).invalidated is True

    def test_ttl_not_exceeded_does_not_invalidate(self) -> None:
        entry = _make_entry()
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, ttl_days=365)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        assert inv.check_ttl() is None
        assert store.get(entry.id).invalidated is False

    def test_failure_cascade_invalidates_after_limit(self) -> None:
        entry = _make_entry()
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, consecutive_failures=FAILURE_CASCADE_LIMIT)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rule = inv.check_failure_cascade()
        assert rule is not None
        assert rule.trigger == "failure_cascade"
        assert store.get(entry.id).invalidated is True

    def test_failure_cascade_below_limit_does_not_invalidate(self) -> None:
        entry = _make_entry()
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, consecutive_failures=FAILURE_CASCADE_LIMIT - 1)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        assert inv.check_failure_cascade() is None
        assert store.get(entry.id).invalidated is False

    def test_manual_invalidate_marks_entry(self) -> None:
        entry = _make_entry()
        indexed = IndexedETDEntry(entry=entry)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rule = inv.manual_invalidate(entry.id, "bad behavior")
        assert rule.trigger == "manual"
        assert entry.id in rule.entry_ids
        assert store.get(entry.id).invalidated is True
        assert store.get(entry.id).invalidation_reason == "bad behavior"

    def test_manual_invalidate_nonexistent_entry(self) -> None:
        store = _store_with()
        inv = ETDInvalidator(store)
        rule = inv.manual_invalidate("nonexistent", "cleanup")
        assert rule.trigger == "manual"
        assert "nonexistent" in rule.entry_ids

    def test_manual_invalidate_already_invalidated_is_noop(self) -> None:
        entry = _make_entry()
        indexed = IndexedETDEntry(entry=entry, invalidated=True, invalidation_reason="already_bad")
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rule = inv.manual_invalidate(entry.id, "again")
        indexed = store.get(entry.id)
        assert indexed.invalidated is True
        assert indexed.invalidation_reason == "already_bad"

    def test_stale_zero_hit_invalidates_after_limit(self) -> None:
        entry = _make_entry()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=old, hit_count=0)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rule = inv.check_stale()
        assert rule is not None
        assert rule.trigger == "stale_zero_hit"
        assert store.get(entry.id).invalidated is True

    def test_stale_recent_entry_not_invalidated(self) -> None:
        entry = _make_entry()
        now = datetime.now(timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=now, hit_count=0)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        assert inv.check_stale() is None
        assert store.get(entry.id).invalidated is False

    def test_stale_hit_count_greater_than_zero_skips(self) -> None:
        entry = _make_entry()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=old, hit_count=1)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        assert inv.check_stale() is None

    def test_stale_old_entry_below_limit_skips(self) -> None:
        entry = _make_entry()
        created = datetime(2026, 5, 1, tzinfo=timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=created, hit_count=0)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        assert inv.check_stale() is None

    def test_run_all_runs_all_checks(self) -> None:
        entry = _make_entry()
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        indexed = IndexedETDEntry(entry=entry, created_at=old, ttl_days=1)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        rules = inv.run_all()
        assert len(rules) >= 1

    def test_record_failure_increments(self) -> None:
        entry = _make_entry()
        indexed = IndexedETDEntry(entry=entry)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        inv.record_failure(entry.id)
        assert store.get(entry.id).consecutive_failures == 1
        inv.record_failure(entry.id)
        assert store.get(entry.id).consecutive_failures == 2

    def test_record_success_resets_and_increments_hit(self) -> None:
        entry = _make_entry()
        indexed = IndexedETDEntry(entry=entry, consecutive_failures=3, hit_count=0)
        store = _store_with([indexed])
        inv = ETDInvalidator(store)
        inv.record_success(entry.id)
        indexed = store.get(entry.id)
        assert indexed.consecutive_failures == 0
        assert indexed.hit_count == 1
        assert indexed.last_hit_at

    def test_record_failure_nonexistent_entry(self) -> None:
        store = _store_with()
        inv = ETDInvalidator(store)
        inv.record_failure("nonexistent")
        inv.record_success("nonexistent")
