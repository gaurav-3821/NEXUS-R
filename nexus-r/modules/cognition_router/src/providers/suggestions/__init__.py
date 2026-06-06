import logging
from ..suggestion_provider import SuggestionResult

logger = logging.getLogger("nexus-r.suggestions")

class SuggestionProviderRegistry:
    def __init__(self):
        self._providers: list = []

    def register(self, provider):
        self._providers.append(provider)

    async def suggest(self, prefix: str, limit: int = 5) -> list[str]:
        all_suggestions: list[str] = []
        seen_lower = set()
        for provider in self._providers:
            try:
                result = await provider.suggest(prefix, limit)
                for s in result.suggestions:
                    sl = s.lower()
                    if sl not in seen_lower:
                        seen_lower.add(sl)
                        all_suggestions.append(s)
            except Exception as e:
                logger.warning(f"Suggestion provider {type(provider).__name__} failed: {e}")
        return all_suggestions[:limit]
