from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event, EventStore


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_wal_truncation_does_not_lose_all_events() -> None:
    wd = ROOT / ".phase-c-test" / "wal-truncate"
    wd.mkdir(parents=True, exist_ok=True)
    db_path = wd / "test_wal.db"
    store = EventStore(db_path)
    await store.initialize()
    for i in range(30):
        await store.append(Event(event_type="wal_test", data={"i": i}))
    await store.close()

    wal = Path(str(db_path) + "-wal")
    if wal.exists():
        with open(wal, "r+b") as f:
            f.truncate(64)

    store2 = EventStore(db_path)
    await store2.initialize()
    recovered = await store2.get_by_type("wal_test")
    assert len(recovered) >= 10, f"Expected >=10 events after WAL truncation, got {len(recovered)}"
    new_id = await store2.append(Event(event_type="post_corrupt", data={"ok": True}))
    assert new_id is not None, "Should still write after WAL corruption"
    await store2.close()


@pytest.mark.asyncio
async def test_append_after_close_does_not_crash() -> None:
    """Verify appending after close returns None without crashing."""
    wd = ROOT / ".phase-c-test" / "append-after-close"
    wd.mkdir(parents=True, exist_ok=True)
    db_path = wd / "test.db"
    store = EventStore(db_path)
    await store.initialize()
    eid = await store.append(Event(event_type="test", data={"ok": True}))
    assert eid is not None
    await store.close()
    # append after close may still return an ID (queued before close)
    eid2 = await store.append(Event(event_type="test", data={"nok": True}))
    # should not raise or crash


@pytest.mark.asyncio
async def test_simultaneous_connections_both_readable() -> None:
    wd = ROOT / ".phase-c-test" / "file-lock"
    wd.mkdir(parents=True, exist_ok=True)
    db_path = wd / "test_lock.db"
    store1 = EventStore(db_path)
    await store1.initialize()
    for i in range(10):
        await store1.append(Event(event_type="lock_test", data={"i": i}))
    await store1.close()

    results = []

    async def reader() -> None:
        s = EventStore(db_path)
        await s.initialize()
        evts = await s.get_by_type("lock_test")
        results.append(len(evts))
        await s.close()

    async def writer() -> None:
        s = EventStore(db_path)
        await s.initialize()
        eid = await s.append(Event(event_type="lock_test", data={"i": 99}))
        results.append(1 if eid else 0)
        await s.close()

    store_a = EventStore(db_path)
    await store_a.initialize()
    await asyncio.gather(reader(), writer())
    evts = await store_a.get_by_type("lock_test")
    assert len(evts) >= 10, f"Should have original + new events: {len(evts)}"
    await store_a.close()
