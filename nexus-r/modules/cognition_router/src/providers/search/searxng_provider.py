import os
import httpx
import logging
from ..search_provider import SearchProvider, SearchResult, SearchResponse

logger = logging.getLogger("nexus-r.searxng_provider")

class SearxngProvider(SearchProvider):
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get("SEARXNG_API_URL", "http://127.0.0.1:8080")

    async def search(self, query, categories=None, site=None, limit=10) -> SearchResponse:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                params = {"format": "json", "q": query, "limit": limit}
                if categories:
                    params["categories"] = ",".join(categories)
                resp = await client.get(f"{self.base_url}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
                results = [
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        content=str(r.get("content") or ""),
                        score=1.0 - (i * 0.01),
                        engine="searxng",
                    )
                    for i, r in enumerate(data.get("results", []))
                ]
                return SearchResponse(
                    results=results[:limit],
                    suggestions=data.get("suggestions", []),
                    total=len(results),
                )
        except Exception as e:
            logger.warning(f"SearxNG search failed: {e}")
            return SearchResponse(results=[], suggestions=[], total=0)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/search", params={"format": "json", "q": "ping"})
                return resp.status_code == 200
        except Exception:
            return False
