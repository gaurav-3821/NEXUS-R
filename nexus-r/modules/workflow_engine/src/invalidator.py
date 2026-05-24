from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from modules.workflow_engine.src.store import ETDStore, IndexedETDEntry


@dataclass
class ETDInvalidationRule:
    rule_id: str
    trigger: str
    entry_ids: list[str] = field(default_factory=list)
    invalidated_at: str = ""
    reason: str = ""


STALE_ZERO_HIT_DAYS = 60
STALE_DEPRIORITIZE_DAYS = 30
FAILURE_CASCADE_LIMIT = 3


class ETDInvalidator:
    def __init__(self, store: ETDStore) -> None:
        self._store = store

    def run_all(self) -> list[ETDInvalidationRule]:
        rules: list[ETDInvalidationRule] = []
        ttl = self.check_ttl()
        if ttl:
            rules.append(ttl)
        cascade = self.check_failure_cascade()
        if cascade:
            rules.append(cascade)
        stale = self.check_stale()
        if stale:
            rules.append(stale)
        return rules

    def check_ttl(self) -> ETDInvalidationRule | None:
        now = datetime.now(timezone.utc)
        expired: list[str] = []
        for entry in self._store.list_active():
            try:
                created = datetime.fromisoformat(entry.created_at)
            except (ValueError, TypeError):
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days = (now - created).days
            if days >= entry.ttl_days:
                expired.append(entry.entry.id)
        if not expired:
            return None
        rule = ETDInvalidationRule(
            rule_id=str(uuid4()),
            trigger="ttl_exceeded",
            entry_ids=expired,
            invalidated_at=now.isoformat(),
            reason=f"TTL exceeded for {len(expired)} entries",
        )
        for eid in expired:
            entry = self._store.get(eid)
            if entry:
                entry.invalidated = True
                entry.invalidation_reason = "ttl_exceeded"
                self._store.update(entry)
        return rule

    def check_failure_cascade(self) -> ETDInvalidationRule | None:
        now = datetime.now(timezone.utc)
        cascaded: list[str] = []
        for entry in self._store.list_active():
            if entry.consecutive_failures >= FAILURE_CASCADE_LIMIT:
                cascaded.append(entry.entry.id)
        if not cascaded:
            return None
        rule = ETDInvalidationRule(
            rule_id=str(uuid4()),
            trigger="failure_cascade",
            entry_ids=cascaded,
            invalidated_at=now.isoformat(),
            reason=f"{len(cascaded)} entries exceeded {FAILURE_CASCADE_LIMIT} consecutive failures",
        )
        for eid in cascaded:
            entry = self._store.get(eid)
            if entry:
                entry.invalidated = True
                entry.invalidation_reason = "failure_cascade"
                self._store.update(entry)
        return rule

    def manual_invalidate(self, entry_id: str, reason: str) -> ETDInvalidationRule:
        now = datetime.now(timezone.utc)
        entry = self._store.get(entry_id)
        if entry and not entry.invalidated:
            entry.invalidated = True
            entry.invalidation_reason = reason
            self._store.update(entry)
        return ETDInvalidationRule(
            rule_id=str(uuid4()),
            trigger="manual",
            entry_ids=[entry_id],
            invalidated_at=now.isoformat(),
            reason=reason,
        )

    def check_stale(self) -> ETDInvalidationRule | None:
        now = datetime.now(timezone.utc)
        stale: list[str] = []
        for entry in self._store.list_active():
            if entry.hit_count > 0:
                continue
            try:
                created = datetime.fromisoformat(entry.created_at)
            except (ValueError, TypeError):
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days = (now - created).days
            if days >= STALE_ZERO_HIT_DAYS:
                stale.append(entry.entry.id)
        if not stale:
            return None
        rule = ETDInvalidationRule(
            rule_id=str(uuid4()),
            trigger="stale_zero_hit",
            entry_ids=stale,
            invalidated_at=now.isoformat(),
            reason=f"{len(stale)} entries with zero hits for {STALE_ZERO_HIT_DAYS}+ days",
        )
        for eid in stale:
            entry = self._store.get(eid)
            if entry:
                entry.invalidated = True
                entry.invalidation_reason = "stale_zero_hit"
                self._store.update(entry)
        return rule

    def record_failure(self, entry_id: str) -> None:
        entry = self._store.get(entry_id)
        if entry:
            entry.consecutive_failures += 1
            self._store.update(entry)

    def record_success(self, entry_id: str) -> None:
        entry = self._store.get(entry_id)
        if entry:
            entry.consecutive_failures = 0
            entry.hit_count += 1
            entry.last_hit_at = datetime.now(timezone.utc).isoformat()
            self._store.update(entry)
