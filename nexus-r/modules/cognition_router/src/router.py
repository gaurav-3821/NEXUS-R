from __future__ import annotations

from dataclasses import dataclass, field

from nexus_r.config import NEXUSConfig
from nexus_r.events import IntentResult, PermissionTier, RoutingDecision
from nexus_r.model_registry import ModelRegistry, ModelInvocationResult
from nexus_r.telemetry import RuntimeTelemetry

from modules.cognition_router.src.capability_profiler import (
    CapabilityProfiler,
    CAR_TIERS,
    CAR_TIER_NAMES,
    complexity_to_tier_index,
    tier_index_by_name,
)
from modules.cognition_router.src.parallel_probe import ParallelProber, ParallelProbeResult
from modules.cognition_router.src.de_escalation import DeEscalationLearner


MAX_CAR_TIER = len(CAR_TIERS) - 1


@dataclass
class CarRouteResult:
    tier_index: int
    tier_name: str
    model_name: str
    cost_estimate: float
    parallel_probe_used: bool = False
    probe_result: ParallelProbeResult | None = None
    de_escalated: bool = False
    requires_approval: bool = False
    rationale: str = ""


class _TierExecutor:
    def __init__(self, models: ModelRegistry) -> None:
        self.models = models

    async def execute_tier(self, prompt: str, tier_index: int) -> ModelInvocationResult:
        if tier_index < 0 or tier_index > MAX_CAR_TIER:
            raise ValueError(f"Invalid tier index: {tier_index}")
        tier = CAR_TIERS[tier_index]
        preferred = "byok" if tier["kind"] == "byok" else "local"
        return await self.models.complete(prompt=prompt, preferred=preferred)


class CognitionRouter:
    def __init__(
        self,
        config: NEXUSConfig,
        event_store,
        secret_registry,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self.config = config
        self.event_store = event_store
        self.telemetry = telemetry
        self.models = ModelRegistry(config, secret_registry, telemetry=telemetry)
        self.profiler = CapabilityProfiler()
        self.prober = ParallelProber()
        self.learner = DeEscalationLearner()
        self._tier_executor = _TierExecutor(self.models)

    async def warm_up(self) -> None:
        await self.models.warm_up()

    async def route(self, intent_result: IntentResult) -> RoutingDecision:
        base_tier = self._assign_base_tier(intent_result)
        base_tier = self._apply_de_escalation(intent_result, base_tier)
        base_tier = self._apply_cost_cap(base_tier, intent_result)
        route = await self._resolve_tier(intent_result, base_tier)

        return RoutingDecision(
            selected_model=route.model_name,
            selected_tier=list(PermissionTier)[route.tier_index],
            cost_estimate=route.cost_estimate,
            rationale=route.rationale,
            etd_match_found=False,
            fallback_chain=CAR_TIER_NAMES,
            car_tier=route.tier_index,
            car_tier_name=route.tier_name,
            parallel_probe_used=route.parallel_probe_used,
            de_escalated=route.de_escalated,
            requires_approval=route.requires_approval,
        )

    def record_outcome(self, task_type: str, assigned_tier: int, actual_tier: int, success: bool, cost: float = 0.0, latency_ms: float = 0.0) -> None:
        self.profiler.record_outcome(task_type, assigned_tier, success, cost, latency_ms)
        task_sig = f"task_type:{task_type}"
        self.learner.learn(task_sig, assigned_tier, actual_tier, success)

    async def complete(self, intent_result: IntentResult, preferred: str) -> dict[str, object]:
        invocation = await self.models.complete(
            prompt=intent_result.normalized_input,
            preferred=preferred,
            messages=intent_result.messages,
        )
        return {
            "text": invocation.text,
            "model_name": invocation.model_name,
            "cost": invocation.estimated_cost,
            "latency_ms": invocation.latency_ms,
            "used_mock": invocation.used_mock,
            "fallback_used": invocation.fallback_used,
        }

    async def stream(self, intent_result: IntentResult, preferred: str):
        async for chunk in self.models.stream(
            prompt=intent_result.normalized_input,
            preferred=preferred,
            messages=intent_result.messages,
        ):
            yield {
                "text": chunk.text,
                "model_name": chunk.model_name,
                "used_mock": chunk.used_mock,
                "fallback_used": chunk.fallback_used,
                "done": chunk.done,
                "reasoning_tokens": chunk.reasoning_tokens,
            }

    def _assign_base_tier(self, intent: IntentResult) -> int:
        return complexity_to_tier_index(intent.complexity)

    def _apply_de_escalation(self, intent: IntentResult, base_tier: int) -> int:
        task_sig = f"task_type:{intent.task_type}"
        de_tier = self.learner.get_suggested_tier_by_index(task_sig, base_tier)
        return min(base_tier, de_tier)

    def _apply_cost_cap(self, base_tier: int, intent: IntentResult) -> int:
        cumulative = 0.0
        cap = self._cost_cap_for_task(intent)
        for i in range(base_tier + 1):
            cumulative += CAR_TIERS[i]["cost"]
            if cumulative > cap:
                return max(0, i - 1)
        return base_tier

    def _cost_cap_for_task(self, intent: IntentResult) -> float:
        if intent.task_type == "general_llm":
            return 0.15
        return 0.05

    async def _resolve_tier(self, intent: IntentResult, base_tier: int) -> CarRouteResult:
        tier_info = CAR_TIERS[base_tier]

        if tier_info["kind"] == "managed":
            return CarRouteResult(
                tier_index=base_tier,
                tier_name=tier_info["name"],
                model_name=tier_info["model"],
                cost_estimate=tier_info["cost"],
                requires_approval=True,
                rationale=f"Task requires {tier_info['name']} — explicit approval needed.",
            )

        if base_tier == MAX_CAR_TIER:
            return CarRouteResult(
                tier_index=base_tier,
                tier_name=tier_info["name"],
                model_name=tier_info["model"],
                cost_estimate=tier_info["cost"],
                rationale=f"Routed to highest tier {tier_info['name']}.",
            )

        for attempt_tier in range(base_tier, min(base_tier + 2, MAX_CAR_TIER + 1)):
            adj_tier = attempt_tier + 1 if attempt_tier < MAX_CAR_TIER else attempt_tier
            if adj_tier > attempt_tier:
                probe_allowed = self._probe_allowed(intent, attempt_tier, adj_tier)
                if probe_allowed:
                    probe_result = await self.prober.probe(
                        prompt=intent.normalized_input,
                        base_tier=attempt_tier,
                        adjacent_tier=adj_tier,
                        tier_executor=self._tier_executor,
                    )
                    win_tier_info = CAR_TIERS[probe_result.winning_tier]
                    return CarRouteResult(
                        tier_index=probe_result.winning_tier,
                        tier_name=win_tier_info["name"],
                        model_name=win_tier_info["model"],
                        cost_estimate=probe_result.total_cost,
                        parallel_probe_used=True,
                        probe_result=probe_result,
                        rationale=f"Parallel probe: tier {attempt_tier} vs {adj_tier}, "
                                  f"winner={probe_result.winning_tier}@{probe_result.total_cost}",
                    )
            tier_info = CAR_TIERS[attempt_tier]
            return CarRouteResult(
                tier_index=attempt_tier,
                tier_name=tier_info["name"],
                model_name=tier_info["model"],
                cost_estimate=tier_info["cost"],
                rationale=f"Sequential route to {tier_info['name']}.",
            )

        tier_info = CAR_TIERS[base_tier]
        return CarRouteResult(
            tier_index=base_tier,
            tier_name=tier_info["name"],
            model_name=tier_info["model"],
            cost_estimate=tier_info["cost"],
            rationale=f"Fallback to base tier {tier_info['name']}.",
        )

    def _probe_allowed(self, intent: IntentResult, base_tier: int, adj_tier: int) -> bool:
        # Parallel probe is disabled for latency optimization.
        # The probe makes 2 full LLM inference calls just to decide routing,
        # adding 2-8 seconds of overhead. Direct tier assignment is sufficient.
        return False
