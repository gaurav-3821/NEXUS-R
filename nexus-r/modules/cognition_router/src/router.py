from __future__ import annotations

from nexus_r.config import NEXUSConfig
from nexus_r.events import IntentResult, RoutingDecision
from nexus_r.model_registry import ModelRegistry
from nexus_r.telemetry import RuntimeTelemetry


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

    async def route(self, intent_result: IntentResult) -> RoutingDecision:
        etd_match = await self.event_store.similar_success_exists(intent_result.normalized_input)
        use_byok = (
            intent_result.complexity >= self.config.models.complexity_threshold
            and self.models.byok.available()
        )
        provider = self.models.get("byok" if use_byok else "local")
        rationale = "Escalated to BYOK due to complexity." if use_byok else "Handled locally."
        if etd_match:
            rationale += " Similar successful history exists."
        fallback_chain = [self.models.local.name]
        if self.models.byok.available():
            fallback_chain.append(self.models.byok.name)
        return RoutingDecision(
            selected_model=provider.name,
            selected_tier=intent_result.suggested_tier,
            cost_estimate=provider.cost_estimate(),
            rationale=rationale,
            etd_match_found=etd_match,
            fallback_chain=fallback_chain,
        )

    async def complete(self, intent_result: IntentResult, preferred: str) -> dict[str, object]:
        invocation = await self.models.complete(
            prompt=intent_result.parameters.get("prompt", intent_result.normalized_input),
            preferred=preferred,
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
            prompt=intent_result.parameters.get("prompt", intent_result.normalized_input),
            preferred=preferred,
        ):
            yield {
                "text": chunk.text,
                "model_name": chunk.model_name,
                "used_mock": chunk.used_mock,
                "fallback_used": chunk.fallback_used,
                "done": chunk.done,
            }
