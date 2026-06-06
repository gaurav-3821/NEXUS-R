import time
import asyncio
from ..search_provider import SearchResponse

class SearchProviderRegistry:
    def __init__(self):
        self._search_providers: list = []
        self._extract_providers: list = []
        self._health_cache: dict[str, tuple[bool, float, asyncio.Lock]] = {}
        self._health_ttl: float = 30.0

    def register(self, provider, role: str = "search", provider_id: str | None = None):
        pid = provider_id or getattr(provider, 'name', str(id(provider)))
        if pid not in self._health_cache:
            import asyncio
            self._health_cache[pid] = (False, 0.0, asyncio.Lock())
            
        if role == "search": self._search_providers.append((pid, provider))
        elif role == "extract": self._extract_providers.append((pid, provider))

    async def _is_healthy(self, pid: str, provider) -> bool:
        is_healthy, last_check, lock = self._health_cache[pid]
        now = time.monotonic()
        
        if (now - last_check) < self._health_ttl:
            return is_healthy
            
        async with lock:
            if (time.monotonic() - self._health_cache[pid][1]) < self._health_ttl:
                return self._health_cache[pid][0]
                
            try:
                import asyncio
                ok = await asyncio.wait_for(provider.health(), timeout=5.0)
            except Exception:
                ok = False
                
            self._health_cache[pid] = (ok, time.monotonic(), lock)
            return ok

    async def search(self, query, **kwargs) -> SearchResponse:
        import logging
        logger = logging.getLogger("nexus-r.search")
        for pid, p in self._search_providers:
            if await self._is_healthy(pid, p):
                try:
                    resp = await p.search(query, **kwargs)
                    if resp.results: return resp
                except Exception as e:
                    logger.error(f"Provider {pid} failed during search: {e}")
                    continue
        return SearchResponse(results=[], suggestions=[], total=0)

    async def extract(self, url: str) -> str:
        for pid, p in self._extract_providers:
            if await self._is_healthy(pid, p):
                return await p.extract(url)
        return ""
