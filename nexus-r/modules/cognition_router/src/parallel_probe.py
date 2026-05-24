from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from nexus_r.model_registry import ModelInvocationResult


@dataclass
class ParallelProbeResult:
    winning_tier: int
    result: ModelInvocationResult
    discarded_tier: int | None = None
    discarded_cost: float = 0.0
    total_cost: float = 0.0
    probe_used: bool = False


class ParallelProber:
    NULL_RESULT = ModelInvocationResult(
        text="",
        model_name="none",
        estimated_cost=0.0,
        latency_ms=0.0,
        used_mock=True,
        fallback_used=True,
    )

    def __init__(self) -> None:
        self._concurrent_limit = asyncio.Semaphore(4)

    async def probe(
        self,
        prompt: str,
        base_tier: int,
        adjacent_tier: int,
        tier_executor: Any,
    ) -> ParallelProbeResult:
        if adjacent_tier <= base_tier:
            single = await tier_executor.execute_tier(prompt, base_tier)
            return ParallelProbeResult(
                winning_tier=base_tier,
                result=single,
                total_cost=single.estimated_cost,
                probe_used=False,
            )

        async def _run(tier: int) -> tuple[int, ModelInvocationResult | Exception]:
            try:
                r = await tier_executor.execute_tier(prompt, tier)
                return tier, r
            except Exception as exc:
                return tier, exc

        results = await asyncio.gather(
            _run(base_tier),
            _run(adjacent_tier),
            return_exceptions=True,
        )

        base_exc: Exception | None = None
        adj_exc: Exception | None = None
        base_outcome: ModelInvocationResult | None = None
        adj_outcome: ModelInvocationResult | None = None

        base_raw, adj_raw = results[0], results[1]

        if not isinstance(base_raw, Exception):
            _, base_val = base_raw
            if isinstance(base_val, Exception):
                base_exc = base_val
            else:
                base_outcome = base_val
        else:
            base_exc = base_raw

        if not isinstance(adj_raw, Exception):
            _, adj_val = adj_raw
            if isinstance(adj_val, Exception):
                adj_exc = adj_val
            else:
                adj_outcome = adj_val
        else:
            adj_exc = adj_raw

        if base_outcome is not None and base_outcome.estimated_cost > 0:
            return ParallelProbeResult(
                winning_tier=base_tier,
                result=base_outcome,
                discarded_tier=adjacent_tier if adj_outcome is not None and adj_outcome.estimated_cost > 0 else None,
                discarded_cost=adj_outcome.estimated_cost if adj_outcome is not None and adj_outcome.estimated_cost > 0 else 0.0,
                total_cost=base_outcome.estimated_cost,
                probe_used=True,
            )

        if adj_outcome is not None and adj_outcome.estimated_cost > 0:
            return ParallelProbeResult(
                winning_tier=adjacent_tier,
                result=adj_outcome,
                discarded_tier=base_tier if base_outcome is not None and base_outcome.estimated_cost > 0 else None,
                discarded_cost=base_outcome.estimated_cost if base_outcome is not None and base_outcome.estimated_cost > 0 else 0.0,
                total_cost=adj_outcome.estimated_cost,
                probe_used=True,
            )

        raise RuntimeError(
            f"Parallel probe failed: base_tier={base_tier} err={base_exc}, "
            f"adjacent_tier={adjacent_tier} err={adj_exc}"
        )
