from __future__ import annotations

from dataclasses import dataclass, field

from modules.workflow_engine.src.parameterizer import ETDEntry


@dataclass
class IndexedETDEntry:
    entry: ETDEntry
    verification_status: str = "passed"
    verified_at: str = ""
    latency_ms: float = 0.0
    created_at: str = ""
    ttl_days: int = 30
    hit_count: int = 0
    last_hit_at: str = ""
    tags: list[str] = field(default_factory=list)
    invalidated: bool = False
    invalidation_reason: str = ""
    consecutive_failures: int = 0
    normalized_input: str = ""


class ETDStore:
    def __init__(self) -> None:
        self._entries: dict[str, IndexedETDEntry] = {}

    def add(self, entry: IndexedETDEntry) -> None:
        self._entries[entry.entry.id] = entry

    def get(self, entry_id: str) -> IndexedETDEntry | None:
        return self._entries.get(entry_id)

    def list_active(self) -> list[IndexedETDEntry]:
        return [e for e in self._entries.values() if not e.invalidated]

    def list_all(self) -> list[IndexedETDEntry]:
        return list(self._entries.values())

    def update(self, entry: IndexedETDEntry) -> None:
        self._entries[entry.entry.id] = entry

    def remove(self, entry_id: str) -> None:
        self._entries.pop(entry_id, None)
