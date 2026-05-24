from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import IntentResult, PermissionTier
from modules.cognition_router.src.router import CognitionRouter, CAR_TIERS, complexity_to_tier_index
from modules.cognition_router.src.capability_profiler import CapabilityProfiler
from modules.cognition_router.src.parallel_probe import ParallelProber, ParallelProbeResult
from modules.cognition_router.src.de_escalation import DeEscalationLearner
from nexus_r.model_registry import ModelInvocationResult


@pytest.fixture
def router(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="nexus_router_test_", dir=Path.cwd()))
    monkeypatch.setenv("NEXUS_BYOK_API_KEY", "dummy")
    config = NEXUSConfig.default(tmp)
    from modules.state_core.src.event_store import EventStore
    store = EventStore(config.database.path)
    from modules.trust_layer.src.secret_registry import SecretRegistry
    secrets = SecretRegistry(config.app_name)
    secrets.bootstrap_from_environment(config.models.byok_secret_name, config.models.byok_api_key_env)
    r = CognitionRouter(config, store, secrets)
    yield r
    try:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass


class TestTierAssignment:
    def test_complexity_maps_to_correct_tier(self):
        assert complexity_to_tier_index(0.1) == 0
        assert complexity_to_tier_index(0.35) == 1
        assert complexity_to_tier_index(0.55) == 2
        assert complexity_to_tier_index(0.7) == 3
        assert complexity_to_tier_index(0.85) == 4
        assert complexity_to_tier_index(0.99) == 5


@pytest.mark.asyncio
async def test_router_never_jumps_more_than_one_tier(router):
    intent = IntentResult(
        raw_input="complex analysis",
        normalized_input="complex analysis",
        task_type="general_llm",
        complexity=0.9,
        confidence=0.9,
        parameters={},
        suggested_tier=PermissionTier.T3,
    )
    decision = await router.route(intent)
    assert decision.car_tier == 4
    assert decision.car_tier_name == "byok_frontier"
    assert decision.requires_approval is False


@pytest.mark.asyncio
async def test_managed_premium_requires_approval(router):
    result = await router._resolve_tier(
        IntentResult(raw_input="x", normalized_input="x", task_type="general_llm",
                     complexity=0.99, confidence=0.99, parameters={},
                     suggested_tier=PermissionTier.T4),
        base_tier=5,
    )
    assert result.requires_approval is True
    assert result.tier_name == "managed_premium"


@pytest.mark.asyncio
async def test_cost_cap_enforces_at_tier(router):
    cap = router._cost_cap_for_task(
        IntentResult(raw_input="x", normalized_input="x", task_type="run_terminal",
                     complexity=0.1, confidence=0.9, parameters={},
                     suggested_tier=PermissionTier.T1)
    )
    assert cap == 0.05
    capped = router._apply_cost_cap(5, IntentResult(
        raw_input="x", normalized_input="x", task_type="run_terminal",
        complexity=0.99, confidence=0.9, parameters={},
        suggested_tier=PermissionTier.T1,
    ))
    assert capped < 5


class TestDeEscalation:
    def test_de_escalation_reduces_tier_over_repeated_tasks(self):
        learner = DeEscalationLearner()
        task_sig = "task_type:list_files"
        for i in range(6):
            learner.learn(task_sig, assigned_tier=3, actual_tier=0, success=True)
        suggested = learner.get_suggested_tier(task_sig)
        assert suggested is not None
        assert suggested <= 1

    def test_de_escalation_requires_five_successes(self):
        learner = DeEscalationLearner()
        task_sig = "task_type:build_app"
        for i in range(3):
            learner.learn(task_sig, assigned_tier=3, actual_tier=0, success=True)
        suggested = learner.get_suggested_tier(task_sig)
        assert suggested is None


class TestParallelProbe:
    @pytest.mark.asyncio
    async def test_parallel_probe_discards_higher_tier(self):
        class _FakeTierExecutor:
            async def execute_tier(self, prompt, tier):
                return ModelInvocationResult(
                    text=f"result from tier {tier}",
                    model_name=CAR_TIERS[tier]["model"],
                    estimated_cost=CAR_TIERS[tier]["cost"],
                    latency_ms=10.0,
                    used_mock=True,
                    fallback_used=False,
                )
        prober = ParallelProber()
        result = await prober.probe("hello", 1, 2, _FakeTierExecutor())
        assert result.winning_tier == 1
        assert result.probe_used is True
        assert result.total_cost == CAR_TIERS[1]["cost"]

    @pytest.mark.asyncio
    async def test_no_probe_when_adjacent_same_as_base(self):
        class _FakeTierExecutor:
            async def execute_tier(self, prompt, tier):
                return ModelInvocationResult(
                    text="result", model_name="test", estimated_cost=0.001,
                    latency_ms=10.0, used_mock=True, fallback_used=False,
                )
        prober = ParallelProber()
        result = await prober.probe("test", 2, 2, _FakeTierExecutor())
        assert result.winning_tier == 2
        assert result.probe_used is False


@pytest.mark.asyncio
async def test_record_outcome_updates_profiler_and_learner(router):
    router.record_outcome("general_llm", 2, 2, True, cost=0.005, latency_ms=100.0)
    router.record_outcome("general_llm", 2, 2, True, cost=0.005, latency_ms=100.0)
    router.record_outcome("general_llm", 2, 2, True, cost=0.005, latency_ms=100.0)
    router.record_outcome("general_llm", 2, 2, True, cost=0.005, latency_ms=100.0)
    router.record_outcome("general_llm", 2, 2, True, cost=0.005, latency_ms=100.0)
    profiles = router.profiler.get_all_profiles()
    assert "general_llm" in profiles
    assert profiles["general_llm"].total_attempts == 5
    task_sig = "task_type:general_llm"
    suggested = router.learner.get_suggested_tier(task_sig)
    assert suggested is not None


class TestCapabilityProfiler:
    def test_tier_weight_returns_default_for_insufficient_data(self):
        profiler = CapabilityProfiler()
        profiler.record_outcome("test_task", 0, True, 0.001, 10.0)
        assert profiler.get_tier_weight("test_task", 0) == 1.0

    def test_preferred_tier_none_without_data(self):
        profiler = CapabilityProfiler()
        assert profiler.get_preferred_tier("unknown") is None


@pytest.mark.asyncio
async def test_router_rationale_mentions_tier(router):
    intent = IntentResult(
        raw_input="hello world",
        normalized_input="hello world",
        task_type="general_llm",
        complexity=0.1,
        confidence=0.9,
        parameters={},
        suggested_tier=PermissionTier.T1,
    )
    decision = await router.route(intent)
    assert f"tier {decision.car_tier}" in decision.rationale
