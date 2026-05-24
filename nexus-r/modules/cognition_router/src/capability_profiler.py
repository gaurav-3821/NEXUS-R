from __future__ import annotations

from dataclasses import dataclass, field


CAR_TIERS: list[dict] = [
    {"name": "local_7b", "model": "ollama/qwen2.5:1.5b-instruct", "cost": 0.001, "kind": "local", "mock": "mock-local"},
    {"name": "local_14b", "model": "ollama/qwen2.5:7b", "cost": 0.002, "kind": "local", "mock": "mock-local"},
    {"name": "local_70b", "model": "ollama/llama3:70b", "cost": 0.005, "kind": "local", "mock": "mock-local"},
    {"name": "byok_budget", "model": "groq/llama-3.3-70b-versatile", "cost": 0.02, "kind": "byok", "mock": "mock-byok"},
    {"name": "byok_frontier", "model": "groq/mixtral-8x7b-32768", "cost": 0.10, "kind": "byok", "mock": "mock-byok"},
    {"name": "managed_premium", "model": "managed/human-review", "cost": 0.50, "kind": "managed", "mock": "mock-managed"},
]


CAR_TIER_NAMES = [t["name"] for t in CAR_TIERS]


def complexity_to_tier_index(complexity: float) -> int:
    if complexity < 0.30:
        return 0
    if complexity < 0.50:
        return 1
    if complexity < 0.65:
        return 2
    if complexity < 0.80:
        return 3
    if complexity < 0.95:
        return 4
    return 5


def tier_index_by_name(name: str) -> int:
    for i, t in enumerate(CAR_TIERS):
        if t["name"] == name:
            return i
    return 0


@dataclass
class TierProfile:
    tier_index: int
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0


@dataclass
class TaskTypeProfile:
    task_type: str
    per_tier: dict[int, TierProfile] = field(default_factory=dict)
    total_attempts: int = 0
    preferred_tier: int | None = None
    preferred_tier_confidence: float = 0.0


class CapabilityProfiler:
    def __init__(self) -> None:
        self._profiles: dict[str, TaskTypeProfile] = {}

    def record_outcome(self, task_type: str, tier_index: int, success: bool, cost: float = 0.0, latency_ms: float = 0.0) -> None:
        if task_type not in self._profiles:
            self._profiles[task_type] = TaskTypeProfile(task_type=task_type)
        profile = self._profiles[task_type]
        if tier_index not in profile.per_tier:
            profile.per_tier[tier_index] = TierProfile(tier_index=tier_index)
        tp = profile.per_tier[tier_index]
        tp.total_attempts += 1
        tp.total_cost += cost
        tp.total_successes += 1 if success else 0
        tp.total_failures += 1 if not success else 0
        tp.success_rate = tp.total_successes / tp.total_attempts if tp.total_attempts > 0 else 0.0
        tp.avg_latency_ms = ((tp.avg_latency_ms * (tp.total_attempts - 1)) + latency_ms) / tp.total_attempts
        profile.total_attempts += 1
        self._recompute_preferred(profile)

    def get_tier_weight(self, task_type: str, tier_index: int) -> float:
        profile = self._profiles.get(task_type)
        if profile is None:
            return 1.0
        tp = profile.per_tier.get(tier_index)
        if tp is None or tp.total_attempts < 3:
            return 1.0
        return tp.success_rate

    def get_preferred_tier(self, task_type: str) -> int | None:
        profile = self._profiles.get(task_type)
        if profile is None:
            return None
        return profile.preferred_tier

    def get_all_profiles(self) -> dict[str, TaskTypeProfile]:
        return dict(self._profiles)

    def _recompute_preferred(self, profile: TaskTypeProfile) -> None:
        best_idx: int | None = None
        best_rate = 0.0
        for idx, tp in profile.per_tier.items():
            if tp.total_attempts >= 5 and tp.success_rate >= 0.90:
                if tp.success_rate > best_rate or (tp.success_rate == best_rate and idx < (best_idx or 999)):
                    best_rate = tp.success_rate
                    best_idx = idx
        profile.preferred_tier = best_idx
        profile.preferred_tier_confidence = best_rate
