from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from nexus_r.model_registry import ModelInvocationResult
from modules.cognition_router.src.parallel_probe import ParallelProber, ParallelProbeResult
from modules.cognition_router.src.capability_profiler import CAR_TIERS


class _ControllableExecutor:
    def __init__(self):
        self.calls = []
        self.results = {}
        self.delays = {}

    async def execute_tier(self, prompt, tier):
        self.calls.append(tier)
        delay = self.delays.get(tier, 0.0)
        if delay > 0:
            await asyncio.sleep(delay)
        result = self.results.get(tier)
        if result is None:
            return ModelInvocationResult(
                text=f"tier {tier} result",
                model_name=CAR_TIERS[tier]["model"],
                estimated_cost=CAR_TIERS[tier]["cost"],
                latency_ms=10.0,
                used_mock=True,
                fallback_used=False,
            )
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_base_tier_succeeds_returns_base_discards_adjacent():
    executor = _ControllableExecutor()
    executor.delays = {0: 0.01, 1: 0.1}
    prober = ParallelProber()
    result = await prober.probe("test", 0, 1, executor)
    assert result.winning_tier == 0
    assert result.probe_used is True
    assert result.total_cost == CAR_TIERS[0]["cost"]
    assert result.discarded_tier == 1
    assert 0 in executor.calls
    assert 1 in executor.calls


@pytest.mark.asyncio
async def test_base_tier_fails_returns_adjacent():
    executor = _ControllableExecutor()
    executor.results[0] = RuntimeError("base tier failed")
    prober = ParallelProber()
    result = await prober.probe("test", 0, 1, executor)
    assert result.winning_tier == 1
    assert result.probe_used is True
    assert result.total_cost == CAR_TIERS[1]["cost"]


@pytest.mark.asyncio
async def test_both_tiers_fail_raises():
    executor = _ControllableExecutor()
    executor.results[0] = RuntimeError("base failed")
    executor.results[1] = RuntimeError("adjacent failed")
    prober = ParallelProber()
    with pytest.raises(RuntimeError, match="Parallel probe failed"):
        await prober.probe("test", 0, 1, executor)


@pytest.mark.asyncio
async def test_no_probe_when_adjacent_same_as_base():
    executor = _ControllableExecutor()
    prober = ParallelProber()
    result = await prober.probe("test", 2, 2, executor)
    assert result.winning_tier == 2
    assert result.probe_used is False
    assert len(executor.calls) == 1


@pytest.mark.asyncio
async def test_base_tier_zero_cost_indicates_failure():
    executor = _ControllableExecutor()
    executor.results[0] = ModelInvocationResult(
        text="", model_name="base", estimated_cost=0.0,
        latency_ms=0.0, used_mock=True, fallback_used=True,
    )
    prober = ParallelProber()
    result = await prober.probe("test", 0, 1, executor)
    assert result.winning_tier == 1


@pytest.mark.asyncio
async def test_concurrent_probes_do_not_deadlock():
    executor = _ControllableExecutor()
    executor.delays = {0: 0.05, 1: 0.05}
    prober = ParallelProber()
    async def run():
        return await prober.probe("test", 0, 1, executor)
    results = await asyncio.gather(run(), run(), run())
    assert all(r.probe_used for r in results)
