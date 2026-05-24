from __future__ import annotations

from dataclasses import dataclass, field

from modules.cognition_router.src.capability_profiler import CAR_TIER_NAMES


MIN_SUCCESSES_FOR_DE_ESCALATION = 5


@dataclass
class TierLearningRecord:
    task_signature: str
    assigned_tier: int
    actual_tier: int
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_tier: int | None = None
    current_tier: int | None = None


@dataclass
class LearningData:
    records: dict[str, TierLearningRecord] = field(default_factory=dict)


class DeEscalationLearner:
    def __init__(self, identity_store: object | None = None) -> None:
        self._identity_store = identity_store
        self._records: dict[str, TierLearningRecord] = {}
        self._load()

    def learn(self, task_signature: str, assigned_tier: int, actual_tier: int, success: bool) -> None:
        key = self._key(task_signature, assigned_tier)
        if key not in self._records:
            self._records[key] = TierLearningRecord(
                task_signature=task_signature,
                assigned_tier=assigned_tier,
                actual_tier=actual_tier,
            )
        record = self._records[key]
        record.total_attempts += 1
        if success:
            record.total_successes += 1
        else:
            record.total_failures += 1
        self._check_de_escalation(record)
        self._save()

    def get_suggested_tier(self, task_signature: str) -> int | None:
        candidates: list[TierLearningRecord] = []
        for key, record in self._records.items():
            if record.task_signature == task_signature and record.total_successes >= MIN_SUCCESSES_FOR_DE_ESCALATION:
                candidates.append(record)
        if not candidates:
            return None
        candidates.sort(key=lambda r: r.current_tier if r.current_tier is not None else r.assigned_tier)
        best = candidates[0]
        return best.current_tier if best.current_tier is not None else best.assigned_tier

    def get_suggested_tier_by_index(self, task_signature: str, default_tier: int) -> int:
        suggested = self.get_suggested_tier(task_signature)
        if suggested is not None and suggested < default_tier:
            return suggested
        return default_tier

    def get_all_records(self) -> dict[str, TierLearningRecord]:
        return dict(self._records)

    def _key(self, task_signature: str, assigned_tier: int) -> str:
        return f"{task_signature}::tier{assigned_tier}"

    def _check_de_escalation(self, record: TierLearningRecord) -> None:
        if record.total_successes < MIN_SUCCESSES_FOR_DE_ESCALATION:
            return
        if record.actual_tier < record.assigned_tier:
            success_rate = record.total_successes / record.total_attempts
            if success_rate >= 0.90:
                record.current_tier = record.actual_tier

    def _load(self) -> None:
        if self._identity_store is None:
            return
        try:
            data = self._identity_store.read()
            raw = data.get("de_escalation_learning", {})
            for key, vals in raw.items():
                self._records[key] = TierLearningRecord(**vals)
        except Exception:
            self._records = {}

    def _save(self) -> None:
        if self._identity_store is None:
            return
        try:
            existing = self._identity_store.read()
            raw: dict[str, dict] = {}
            for key, record in self._records.items():
                raw[key] = {
                    "task_signature": record.task_signature,
                    "assigned_tier": record.assigned_tier,
                    "actual_tier": record.actual_tier,
                    "total_attempts": record.total_attempts,
                    "total_successes": record.total_successes,
                    "total_failures": record.total_failures,
                    "last_tier": record.last_tier,
                    "current_tier": record.current_tier,
                }
            existing["de_escalation_learning"] = raw
            self._identity_store.write(existing)
        except Exception:
            pass
