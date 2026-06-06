import asyncio
import logging
from typing import Any
from .widget_provider import WidgetResult

logger = logging.getLogger("nexus-r.widgets")

class WidgetRegistry:
    def __init__(self):
        self._providers: list = []

    def register(self, provider):
        self._providers.append(provider)

    async def execute_all(self, context: Any) -> list[WidgetResult]:
        if not self._providers:
            return []

        tasks = []
        for provider in self._providers:
            try:
                if not await provider.should_run(context):
                    continue
                tasks.append(provider.execute(context))
            except Exception as e:
                logger.warning(f"Widget {type(provider).__name__} should_run failed: {e}")

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        widgets = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Widget execution failed: {r}")
            elif r is not None:
                widgets.append(r)

        widgets.sort(key=lambda w: w.priority)
        return widgets
