from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float
    engine: str = ""

@dataclass
class SearchResponse:
    results: list[SearchResult] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    total: int = 0

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, categories: list[str] | None = None,
                     site: str | None = None, limit: int = 10) -> SearchResponse:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...
