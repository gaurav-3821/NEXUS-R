from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class SuggestionResult:
    suggestions: list[str] = field(default_factory=list)
    source: str = ""

class SuggestionProvider(ABC):
    @abstractmethod
    async def suggest(self, prefix: str, limit: int = 5) -> SuggestionResult:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...
