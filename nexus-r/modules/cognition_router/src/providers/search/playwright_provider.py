from ..search_provider import SearchProvider, SearchResult, SearchResponse
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # We assume AgenticBrowser exists or will exist; for now we use dynamic typing or duck typing
    from modules.execution_sandbox.src.browser_sandbox import AgenticBrowser

class PlaywrightProvider(SearchProvider):
    def __init__(self, browser: 'AgenticBrowser'):
        self.browser = browser

    async def search(self, query, categories=None, site=None, limit=10) -> SearchResponse:
        full_query = f"{query} site:{site}" if site else query
        raw = await self.browser.search_web(full_query)
        results = raw.get("results", [])
        return SearchResponse(
            results=[
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=str(r.get("snippet") or r.get("content") or ""),
                    score=1.0 - (i * 0.01),
                    engine="playwright",
                )
                for i, r in enumerate(results[:limit])
            ],
            total=len(results),
        )

    async def extract(self, url: str) -> str:
        """Fetch full page content from a URL. Used by ResearchEngine for deep extraction."""
        nav = await self.browser.goto(url)
        if nav.get("success"):
            return await self.browser.extract_text(max_chars=4000)
        return ""

    async def health(self) -> bool:
        return True
