from __future__ import annotations

from pathlib import Path

import pytest

from modules.cognition_router.src.de_escalation import (
    DeEscalationLearner,
    TierLearningRecord,
    MIN_SUCCESSES_FOR_DE_ESCALATION,
)


class _FakeIdentityStore:
    def __init__(self):
        self._data: dict = {}

    def read(self) -> dict:
        return dict(self._data)

    def write(self, data: dict) -> None:
        self._data = dict(data)


class TestDeEscalationLearner:
    def test_learn_stores_record(self):
        learner = DeEscalationLearner()
        learner.learn("build-app", 3, 0, success=True)
        records = learner.get_all_records()
        assert len(records) == 1
        key = "build-app::tier3"
        assert key in records
        assert records[key].total_attempts == 1
        assert records[key].total_successes == 1

    def test_multiple_learns_accumulate(self):
        learner = DeEscalationLearner()
        sig = "deploy"
        for i in range(10):
            learner.learn(sig, 3, 0, success=True)
        key = f"{sig}::tier3"
        assert learner.get_all_records()[key].total_attempts == 10
        assert learner.get_all_records()[key].total_successes == 10

    def test_fewer_than_5_successes_returns_none(self):
        learner = DeEscalationLearner()
        sig = "test-task"
        for i in range(4):
            learner.learn(sig, 3, 0, success=True)
        suggested = learner.get_suggested_tier(sig)
        assert suggested is None

    def test_after_5_successes_suggests_lower_tier(self):
        learner = DeEscalationLearner()
        sig = "list-task"
        for i in range(5):
            learner.learn(sig, 3, 0, success=True)
        suggested = learner.get_suggested_tier(sig)
        assert suggested is not None
        assert suggested <= 0

    def test_requires_90_percent_success_rate_for_de_escalation(self):
        learner = DeEscalationLearner()
        sig = "mixed-task"
        for i in range(5):
            if i < 3:
                learner.learn(sig, 2, 0, success=True)
            else:
                learner.learn(sig, 2, 0, success=False)
        suggested = learner.get_suggested_tier(sig)
        assert suggested is None

    def test_get_suggested_tier_by_index_returns_lower(self):
        learner = DeEscalationLearner()
        sig = "optimized-task"
        for i in range(5):
            learner.learn(sig, 4, 1, success=True)
        result = learner.get_suggested_tier_by_index(sig, 4)
        assert result < 4

    def test_get_suggested_tier_by_index_returns_default_when_no_learning(self):
        learner = DeEscalationLearner()
        result = learner.get_suggested_tier_by_index("unknown", 3)
        assert result == 3

    def test_persistence_via_identity_store(self):
        store = _FakeIdentityStore()
        learner = DeEscalationLearner(store)
        learner.learn("persist-task", 3, 0, success=True)
        learner.learn("persist-task", 3, 0, success=True)
        learner2 = DeEscalationLearner(store)
        key = "persist-task::tier3"
        records = learner2.get_all_records()
        assert key in records
        assert records[key].total_attempts == 2

    def test_identity_store_io_error_does_not_crash(self):
        class _BrokenStore:
            def read(self) -> dict:
                raise RuntimeError("disk failure")
            def write(self, data: dict) -> None:
                raise RuntimeError("disk failure")
        learner = DeEscalationLearner(_BrokenStore())
        learner.learn("crash-test", 2, 0, success=True)
        assert len(learner.get_all_records()) == 1

    def test_tier_learning_record_dataclass(self):
        r = TierLearningRecord(
            task_signature="test",
            assigned_tier=3,
            actual_tier=1,
            total_attempts=5,
            total_successes=5,
        )
        assert r.task_signature == "test"
        assert r.assigned_tier == 3
        assert r.actual_tier == 1
        assert r.total_attempts == 5
        assert r.total_successes == 5

    def test_constant_is_correct(self):
        assert MIN_SUCCESSES_FOR_DE_ESCALATION == 5

    def test_learn_with_failure_updates_counters(self):
        learner = DeEscalationLearner()
        learner.learn("fail-task", 2, 2, success=False)
        records = learner.get_all_records()
        key = "fail-task::tier2"
        assert records[key].total_failures == 1
        assert records[key].total_successes == 0
        assert records[key].total_attempts == 1
