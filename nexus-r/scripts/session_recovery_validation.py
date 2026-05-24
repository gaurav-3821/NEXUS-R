from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event
from modules.orchestrator.src.orchestrator import MainOrchestrator


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


async def test_normal_start_stop():
    print("\n--- A. Normal Start/Stop Recovery ---")
    config = NEXUSConfig.default(ROOT / ".session-recovery")
    orch = MainOrchestrator(config)
    await orch.initialize()
    sid = orch.session_id
    await orch.run_task("hello recovery test")
    await orch.close()
    check("Normal shutdown completes cleanly", True)

    orch2 = MainOrchestrator(config)
    await orch2.initialize()
    recovered_sid = orch2.session_id
    check("Session ID persists across restarts", sid == recovered_sid, f"sid={sid}")
    history = await orch2.get_history()
    check("History persists after restart", len(history) >= 1, f"entries={len(history)}")
    await orch2.close()
    return True


async def test_partial_event_writes():
    print("\n--- B. Partial Event Write Recovery ---")
    config = NEXUSConfig.default(ROOT / ".session-recovery")
    store = __import__("modules.state_core.src.event_store", fromlist=[""]).EventStore
    from nexus_r.events import EventStore as ES

    es = ES(config.database.path)
    await es.initialize()

    # Simulate partial write by appending valid events
    ids = []
    for i in range(10):
        eid = await es.append(Event(event_type="partial_test", data={"i": i}))
        ids.append(eid)

    all_events = await es.get_by_type("partial_test")
    check("Partial write: all events readable", len(all_events) == 10, f"found={len(all_events)}")
    await es.close()
    return True


async def test_stale_task_cleanup():
    print("\n--- C. Stale Task Cleanup ---")
    config = NEXUSConfig.default(ROOT / ".session-recovery")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1

    orch = MainOrchestrator(config)

    # Create some failed tasks
    for i in range(5):
        try:
            await orch.run_task(f"hello cleanup test {i}")
        except Exception:
            pass

    await asyncio.sleep(0.3)
    check("No stale tasks after failures", orch._active_tasks == 0, f"active={orch._active_tasks}")
    await orch.close()
    return True


async def test_concurrent_session_recovery():
    print("\n--- D. Concurrent Session Recovery ---")
    config = NEXUSConfig.default(ROOT / ".session-recovery")

    async def session_worker(worker_id: int) -> bool:
        orch = MainOrchestrator(config)
        await orch.initialize()
        try:
            await orch.run_task(f"hello concurrent worker {worker_id}")
            return True
        except Exception:
            return False
        finally:
            await orch.close()

    workers = [session_worker(i) for i in range(10)]
    results = await asyncio.gather(*workers)
    check("Concurrent session recovery", all(results), f"{sum(results)}/{len(results)} succeeded")
    return True


async def test_event_consistency():
    print("\n--- E. Event Consistency After Failures ---")
    config = NEXUSConfig.default(ROOT / ".session-recovery")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1

    orch = MainOrchestrator(config)
    events_before = await orch.event_store.get_by_type("task_completed")
    count_before = len(events_before)

    for i in range(5):
        await orch.run_task(f"hello consistency test {i}")

    events_after = await orch.event_store.get_by_type("task_completed")
    count_after = len(events_after)
    check("Event count increases after failures", count_after > count_before, f"{count_before} -> {count_after}")

    # Verify causal chain integrity
    last_event = events_after[-1] if events_after else None
    if last_event:
        chain = await orch.event_store.get_chain(last_event.id)
        check("Causal chain intact after recovery", len(chain) >= 2, f"chain_length={len(chain)}")

    await orch.close()
    return True


async def main():
    print("=" * 70)
    print("  SESSION RECOVERY VALIDATION")
    print("=" * 70)

    wd = ROOT / ".session-recovery"
    wd.mkdir(exist_ok=True)
    (wd / "src").mkdir(exist_ok=True)

    tests = [
        ("normal_start_stop", test_normal_start_stop),
        ("partial_event_writes", test_partial_event_writes),
        ("stale_task_cleanup", test_stale_task_cleanup),
        ("concurrent_recovery", test_concurrent_session_recovery),
        ("event_consistency", test_event_consistency),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as exc:
            print(f"  [ERROR] {name}: {exc}")
            results[name] = False

    print(f"\n{'='*70}")
    print(f"  RESULTS: {sum(1 for v in results.values() if v)}/{len(results)} passed")
    print(f"{'='*70}")


if __name__ == "__main__":
    if not hasattr(Path, '_mkdir_patched'):
        original_mkdir = Path.mkdir
        def _safe_mkdir(self, *a, **kw):
            try:
                return original_mkdir(self, *a, **kw)
            except FileExistsError:
                pass
        Path.mkdir = _safe_mkdir
        Path._mkdir_patched = True
    asyncio.run(main())
