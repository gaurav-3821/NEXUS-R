import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.router_decision_widget")

class RouterDecisionWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        decision = getattr(context, "router_decision", None)
        return decision is not None and bool(decision.get("model"))

    async def execute(self, context) -> WidgetResult | None:
        decision = getattr(context, "router_decision", {})
        if not decision:
            return None

        return WidgetResult(
            widget_type="router_decision",
            data={
                "model": decision.get("model", "unknown"),
                "tier": decision.get("tier", "auto"),
                "estimated_cost": decision.get("cost_estimate", 0),
            },
            title="Router Decision",
            priority=9,
        )
