import os
import httpx
import logging
from ..search_provider import SearchProvider, SearchResult, SearchResponse

logger = logging.getLogger("nexus-r.searxng_provider")

class SearxngProvider(SearchProvider):
    def __init__(self, base_url: str | None = None, client: httpx.AsyncClient | None = None):
        self.base_url = base_url or os.environ.get("SEARXNG_API_URL", "http://127.0.0.1:8080")
        self._client = client or httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=100))

    async def search(self, query, categories=None, site=None, limit=10) -> SearchResponse:
        params = {"format": "json", "q": query}
        if categories:
            params["categories"] = ",".join(categories)
        try:
            resp = await self._client.get(f"{self.base_url}/search", params=params)
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
        except httpx.TimeoutException:
            logger.error("SearxNG timeout")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"SearxNG HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"SearxNG unexpected error: {e}")
            raise

    async def health(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/search", params={"format": "json", "q": "ping"}, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def extract(self, url: str) -> str:
        return ''
