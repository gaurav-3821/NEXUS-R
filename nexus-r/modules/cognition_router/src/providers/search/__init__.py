import time
from ..search_provider import SearchResponse

class SearchProviderRegistry:
    def __init__(self):
        self._search_providers: list = []
        self._extract_providers: list = []
        self._health_cache: dict[int, tuple[bool, float]] = {}
        self._health_ttl: float = 30.0

    def register(self, provider, role: str = "search"):
        if role == "search":
            self._search_providers.append(provider)
        elif role == "extract":
            self._extract_providers.append(provider)

    async def _is_healthy(self, provider) -> bool:
        pid = id(provider)
        now = time.time()
        if pid in self._health_cache and (now - self._health_cache[pid][1]) < self._health_ttl:
            return self._health_cache[pid][0]
        ok = await provider.health()
        self._health_cache[pid] = (ok, now)
        return ok

    async def search(self, query, **kwargs) -> SearchResponse:
        for p in self._search_providers:
            if await self._is_healthy(p):
                return await p.search(query, **kwargs)
        return SearchResponse(results=[], suggestions=[], total=0)

    async def extract(self, url: str) -> str:
        for p in self._extract_providers:
            if await self._is_healthy(p):
                return await p.extract(url)
        return ""
