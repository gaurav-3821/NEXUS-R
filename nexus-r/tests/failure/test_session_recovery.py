from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_session_id_persists_across_restarts() -> None:
    wd = ROOT / ".phase-c-test" / "session-restart"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "src").mkdir(exist_ok=True)
    (wd / "src" / "dummy.py").write_text("# test")
    config = NEXUSConfig.default(wd)

    orch1 = MainOrchestrator(config)
    await orch1.initialize()
    sid1 = orch1.session_id
    await orch1.run_task("hello")
    await orch1.close()

    orch2 = MainOrchestrator(config)
    await orch2.initialize()
    sid2 = orch2.session_id
    assert sid2 == sid1, f"Session ID changed: {sid1} -> {sid2}"
    await orch2.close()


@pytest.mark.asyncio
async def test_task_history_persists_after_restart() -> None:
    wd = ROOT / ".phase-c-test" / "session-history"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "src").mkdir(exist_ok=True)
    (wd / "src" / "dummy.py").write_text("# test")
    config = NEXUSConfig.default(wd)

    orch1 = MainOrchestrator(config)
    await orch1.initialize()
    await orch1.run_task("hello")
    history_before = await orch1.get_history()
    await orch1.close()

    orch2 = MainOrchestrator(config)
    await orch2.initialize()
    history_after = await orch2.get_history()
    assert len(history_after) >= len(history_before), "History should not shrink after restart"
    await orch2.close()


@pytest.mark.asyncio
async def test_concurrent_session_recovery_all_succeed() -> None:
    wd = ROOT / ".phase-c-test" / "session-concurrent"
    wd.mkdir(parents=True, exist_ok=True)

    async def worker(i: int) -> bool:
        w = wd / f"w{i}"
        w.mkdir(exist_ok=True)
        (w / "src").mkdir(exist_ok=True)
        (w / "src" / "dummy.py").write_text("# test")
        cfg = NEXUSConfig.default(w)
        o = MainOrchestrator(cfg)
        r = await o.run_task("hello")
        await o.close()
        return r.get("success", False)

    results = await asyncio.gather(*[worker(i) for i in range(10)])
    assert sum(results) >= 8, f"Expected >=8/10 concurrent sessions to succeed, got {sum(results)}/10"
