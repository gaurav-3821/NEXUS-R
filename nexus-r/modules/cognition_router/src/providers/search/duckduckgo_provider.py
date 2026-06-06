"""DuckDuckGo search provider — works out of the box without API keys or setup.

Falls back gracefully if the ddgs/duckduckgo_search package isn't installed.
"""
import os
import logging
import asyncio
import httpx
import re
from typing import Any
from ..search_provider import SearchProvider, SearchResult, SearchResponse

logger = logging.getLogger("nexus-r.duckduckgo_provider")


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self._ddgs = None
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            self._DDGS = DDGS
        except ImportError:
            self._DDGS = None
            logger.warning("ddgs/duckduckgo_search not installed; DuckDuckGo provider will use HTTP fallback")

    async def search(self, query, categories=None, site=None, limit=10) -> SearchResponse:
        if self._DDGS is not None:
            return await self._search_library(query, categories, site, limit)
        return await self._search_http(query, categories, site, limit)

    async def _search_library(self, query, categories, site, limit) -> SearchResponse:
        try:
            ddgs = self._DDGS()
            loop = asyncio.get_running_loop()
            cat_filter = self._category_to_ddg(categories)
            kwargs: dict[str, Any] = {"max_results": max(limit, 10)}
            if cat_filter:
                kwargs["category"] = cat_filter
            if site:
                kwargs["site"] = site
            results = await loop.run_in_executor(
                None,
                lambda: list(ddgs.text(query, **kwargs)),
            )
            search_results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href") or r.get("url", ""),
                    content=str(r.get("body") or r.get("content") or "")[:500],
                    score=1.0 - (i * 0.01),
                    engine="duckduckgo",
                )
                for i, r in enumerate(results[:limit])
            ]
            return SearchResponse(
                results=search_results,
                suggestions=[],
                total=len(search_results),
            )
        except Exception as e:
            logger.warning(f"DDG library search failed: {e}")
            return await self._search_http(query, categories, site, limit)

    async def _search_http(self, query, categories, site, limit) -> SearchResponse:
        client = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            params = {"q": query, "kl": "us-en"}
            if site:
                params["q"] = f"site:{site} {query}"
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            resp.raise_for_status()
            html = resp.text
            results = self._parse_html(html)[:limit]
            return SearchResponse(results=results, suggestions=[], total=len(results))
        except Exception as e:
            logger.warning(f"DDG HTTP search failed: {e}")
            return SearchResponse(results=[], suggestions=[], total=0)
        finally:
            if self._client is None:
                await client.aclose()

    @staticmethod
    def _parse_html(html: str) -> list[SearchResult]:
        results: list[SearchResult] = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )
        snippet_pattern = re.compile(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for i, match in enumerate(pattern.finditer(html)):
            url, title = match.group(1), match.group(2).strip()
            snippet_match = snippet_pattern.search(html, match.end())
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""
            if not url or not title:
                continue
            if "duckduckgo.com" in url and "/l/?uddg=" in url:
                m = re.search(r"uddg=([^&]+)", url)
                if m:
                    from urllib.parse import unquote
                    url = unquote(m.group(1))
            results.append(SearchResult(
                title=title,
                url=url,
                content=snippet[:500],
                score=1.0 - (i * 0.01),
                engine="duckduckgo",
            ))
        return results

    @staticmethod
    def _category_to_ddg(categories):
        if not categories:
            return None
        cat = categories[0].lower() if isinstance(categories, list) else str(categories).lower()
        mapping = {
            "news": "news",
            "academic": None,
            "social": None,
            "web": None,
            "images": "images",
            "videos": "videos",
        }
        return mapping.get(cat)

    async def health(self) -> bool:
        return True

    async def extract(self, url: str) -> str:
        return ""
