import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.memory_widget")

MEMORY_KEYWORDS = ["remember", "memory", "remembered", "what do you know", "what do i know",
                   "preferences", "what have i said", "recall"]

class MemoryWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        memory_facts = getattr(context, "memory_facts", [])
        return bool(memory_facts) or any(kw in query.lower() for kw in MEMORY_KEYWORDS)

    async def execute(self, context) -> WidgetResult | None:
        memory_facts = getattr(context, "memory_facts", [])
        return WidgetResult(
            widget_type="memory",
            data={
                "facts": memory_facts[:10],
                "fact_count": len(memory_facts),
            },
            title="Memory Context",
            priority=6,
        )
