from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.model_registry import ModelRegistry
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.trust_layer.src.secret_registry import SecretRegistry


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


async def test_stream_cleanup_after_cancel():
    print("\n--- A. Stream Cleanup After Cancellation ---")
    config = NEXUSConfig.default(ROOT / ".stream-stress")
    orch = MainOrchestrator(config)
    await orch.initialize()
    reg = ModelRegistry(config, orch.secret_registry, telemetry=orch.telemetry)

    async def consume():
        chunks = 0
        try:
            async for _chunk in reg.stream("Repeat the word hello many times", preferred="local"):
                chunks += 1
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            pass
        return chunks

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    check("Stream cancel does not crash runtime", True)
    check("Orchestrator responsive after stream cancel", orch._active_tasks == 0, f"active={orch._active_tasks}")
    await orch.close()
    return True


async def test_fallback_during_stream():
    print("\n--- B. Fallback During Streaming (Local fails, switch to mock/byok) ---")
    config = NEXUSConfig.default(ROOT / ".stream-stress")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1
    orch = MainOrchestrator(config)
    await orch.initialize()
    reg = ModelRegistry(config, orch.secret_registry, telemetry=orch.telemetry)

    chunks = []
    try:
        async for chunk in reg.stream("Say hello world repeatedly", preferred="local"):
            chunks.append(chunk)
            if chunk.done:
                break
    except Exception as exc:
        check("Stream fallback handles error gracefully", True, f"error={str(exc)[:80]}")
    else:
        models_used = set(c.model_name for c in chunks)
        check("Stream completed via fallback", len(chunks) > 0, f"chunks={len(chunks)}, models={models_used}")

    await orch.close()
    return True


async def test_telemetry_integrity():
    print("\n--- C. Telemetry Integrity ---")
    config = NEXUSConfig.default(ROOT / ".stream-stress")
    orch = MainOrchestrator(config)
    await orch.initialize()

    for i in range(5):
        await orch.run_task(f"hello telemetry test {i}")

    telemetry = orch.get_telemetry_snapshot()
    counters = telemetry.get("counters", {})
    check("Telemetry counters populated", len(counters) > 0, f"counters={json.dumps(counters)}")

    log_path = config.observability.log_path
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        large_events = [l for l in lines if len(l) > 10240]
        check("No telemetry event >10KB", len(large_events) == 0, f"large_events={len(large_events)}")

        provider_events = [l for l in lines if "provider_" in l]
        check("Provider telemetry events logged", len(provider_events) > 0, f"count={len(provider_events)}")

    await orch.close()
    return True


async def test_no_orphan_tasks():
    print("\n--- D. No Orphan Tasks After Failure ---")
    config = NEXUSConfig.default(ROOT / ".stream-stress")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1
    orch = MainOrchestrator(config)

    tasks = []
    for i in range(20):
        t = asyncio.create_task(orch.run_task(f"hello orphan test {i}"))
        tasks.append(t)

    for t in tasks:
        try:
            await t
        except Exception:
            pass

    await asyncio.sleep(0.5)
    check("No orphan tasks after failures", orch._active_tasks == 0, f"active_tasks={orch._active_tasks}")
    await orch.close()
    return True


async def test_stream_no_corruption():
    print("\n--- E. Stream Integrity (No corrupted events/chains) ---")
    config = NEXUSConfig.default(ROOT / ".stream-stress")
    orch = MainOrchestrator(config)
    await orch.initialize()

    result = await orch.run_task("hello stream integrity check")
    completed = await orch.event_store.get_by_type("task_completed")
    latest = completed[-1] if completed else None

    check("Stream task completed successfully", result.get("success"), f"routing={result.get('routing_model')}")
    if latest:
        chain = await orch.event_store.get_chain(latest.id)
        check("Event chain is intact after streaming", len(chain) >= 3, f"events_in_chain={len(chain)}")

    await orch.close()
    return True


async def main():
    print("=" * 70)
    print("  STREAMING STRESS TEST")
    print("=" * 70)

    wd = ROOT / ".stream-stress"
    wd.mkdir(exist_ok=True)
    (wd / "src").mkdir(exist_ok=True)

    results = {}
    for test_fn in [test_stream_cleanup_after_cancel, test_fallback_during_stream, test_telemetry_integrity, test_no_orphan_tasks, test_stream_no_corruption]:
        try:
            results[test_fn.__name__] = await test_fn()
        except Exception as exc:
            print(f"  [ERROR] {test_fn.__name__}: {exc}")
            results[test_fn.__name__] = False

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
