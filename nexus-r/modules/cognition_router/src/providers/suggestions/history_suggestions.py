import logging
from ..suggestion_provider import SuggestionProvider, SuggestionResult

logger = logging.getLogger("nexus-r.history_suggestions")

class HistorySuggestionProvider(SuggestionProvider):
    def __init__(self, event_store):
        self._event_store = event_store

    async def suggest(self, prefix: str, limit: int = 5) -> SuggestionResult:
        if not prefix:
            return SuggestionResult(suggestions=[], source="history")

        prefix_lower = prefix.lower().strip()
        try:
            events = await self._event_store.get_recent_by_type("chat_message_sent", limit=100)
        except Exception as e:
            logger.exception(f"Failed to fetch history suggestions: {e}")
            return SuggestionResult(suggestions=[], source="history")

        seen_lower = set()
        matches = []
        for event in events:
            content = event.data.get("content", "")
            content_lower = content.lower()
            if not content or content_lower in seen_lower:
                continue
            seen_lower.add(content_lower)
            if content_lower.startswith(prefix_lower):
                matches.append(content)
                if len(matches) >= limit:
                    break

        return SuggestionResult(suggestions=matches, source="history")

    async def health(self) -> bool:
        return True
