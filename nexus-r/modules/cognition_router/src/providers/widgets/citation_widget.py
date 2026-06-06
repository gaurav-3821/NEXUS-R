import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.citation_widget")

class CitationWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        research = getattr(context, "research_result", None)
        return research is not None and bool(getattr(research, "sources", []))

    async def execute(self, context) -> WidgetResult | None:
        research = getattr(context, "research_result", None)
        if not research:
            return None
        sources = getattr(research, "sources", [])
        if not sources:
            return None

        return WidgetResult(
            widget_type="citation",
            data={
                "sources": [
                    {"title": s[0], "url": s[1], "snippet": s[2][:300]}
                    for s in sources[:8]
                ]
            },
            title="Research Sources",
            priority=1,
        )
