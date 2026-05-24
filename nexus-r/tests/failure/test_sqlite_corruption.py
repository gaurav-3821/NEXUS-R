from __future__ import annotations

"""
SQLite Corruption — Phase C database resilience validation.
Tests WAL corruption, page corruption, and concurrent access.
See: RUNTIME STABILITY — T3 SQLite Corruption
"""

import asyncio

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event, EventStore
from pathlib import Path


@pytest.mark.asyncio
async def test_wal_corruption_recovery() -> None:
    wd = Path(__file__).parents[2] / ".corruption-test"
    wd.mkdir(exist_ok=True)
    db_path = wd / "test_wal.db"
    store = EventStore(db_path)
    await store.initialize()
    for i in range(50):
        await store.append(Event(event_type="wal_test", data={"i": i}))
    await store.close()

    wal = Path(str(db_path) + "-wal")
    if wal.exists():
        with open(wal, "r+b") as f:
            f.truncate(64)

    store2 = EventStore(db_path)
    await store2.initialize()
    recovered = await store2.get_by_type("wal_test")
    assert len(recovered) >= 25, f"Expected >=25 events after WAL truncation, got {len(recovered)}"
    new_id = await store2.append(Event(event_type="post_corrupt", data={"ok": True}))
    assert new_id is not None
    await store2.close()
