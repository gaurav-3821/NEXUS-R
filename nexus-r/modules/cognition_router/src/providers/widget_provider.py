from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class WidgetResult:
    widget_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    title: str = ""
    priority: int = 5

class WidgetProvider(ABC):
    @abstractmethod
    async def execute(self, context: Any) -> WidgetResult | None:
        ...

    @abstractmethod
    async def should_run(self, context: Any) -> bool:
        ...
