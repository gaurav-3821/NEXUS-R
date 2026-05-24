from __future__ import annotations

from datetime import datetime, timezone

from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry


STOP_WORDS = {"a", "an", "the", "to", "of", "in", "for", "on", "with",
              "and", "or", "is", "it", "at", "by", "from", "as", "into",
              "through", "during", "before", "after", "above", "below"}


class ETDIndexer:
    def __init__(self, store: ETDStore) -> None:
        self._store = store

    def index(self, entry: ETDEntry, latency_ms: float = 0.0) -> IndexedETDEntry:
        now = datetime.now(timezone.utc).isoformat()
        status = "passed" if entry.failure_count == 0 else "failed"
        tags = self._generate_tags(entry)
        indexed = IndexedETDEntry(
            entry=entry,
            verification_status=status,
            verified_at=now,
            latency_ms=latency_ms,
            created_at=now,
            ttl_days=30,
            hit_count=0,
            last_hit_at="",
            tags=tags,
            invalidated=False,
            invalidation_reason="",
            consecutive_failures=0,
        )
        self._store.add(indexed)
        return indexed

    def _generate_tags(self, entry: ETDEntry) -> list[str]:
        tags: list[str] = []
        for seg in entry.intent_signature.split("-"):
            seg = seg.strip()
            if seg and seg not in STOP_WORDS:
                tags.append(seg.lower())
        tool_names: set[str] = set()
        for step in entry.tool_sequence:
            t = step.tool.lower().strip()
            if t:
                tool_names.add(t)
        tags.extend(sorted(tool_names))
        if entry.parameter_slots:
            tags.append("has-params")
        tags.append("etd")
        seen: set[str] = set()
        deduped: list[str] = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped
