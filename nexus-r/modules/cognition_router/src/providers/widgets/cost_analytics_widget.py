import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.cost_analytics_widget")

COST_KEYWORDS = ["cost", "price", "spending", "tokens", "usage", "analytics"]

class CostAnalyticsWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        return any(kw in query.lower() for kw in COST_KEYWORDS)

    async def execute(self, context) -> WidgetResult | None:
        decision = getattr(context, "router_decision", {})
        cost = decision.get("cost_estimate", 0)
        model = decision.get("model", "unknown")
        tier = decision.get("tier", "auto")

        return WidgetResult(
            widget_type="cost_analytics",
            data={
                "estimated_cost": cost,
                "model": model,
                "tier": tier,
                "currency": "USD",
            },
            title="Cost Analytics",
            priority=10,
        )
