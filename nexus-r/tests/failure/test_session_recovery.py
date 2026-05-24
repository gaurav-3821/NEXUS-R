from __future__ import annotations

"""
Session Recovery — Phase C session resilience validation.
Tests session ID persistence, stale pointer recovery, and event consistency.
See: RUNTIME STABILITY — T2 Session Recovery
"""

import asyncio

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator
from pathlib import Path


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("print('hello')\n")
    (tmp_path / "notes.txt").write_text("test\n")
    return tmp_path


async def test_session_id_persists_across_restarts() -> None:
    import tempfile
    wd = Path(tempfile.mkdtemp())
    _workspace(wd)
    config = NEXUSConfig.default(wd)
    orch = MainOrchestrator(config)
    await orch.initialize()
    sid = orch.session_id
    await orch.run_task("hello session")
    await orch.close()

    orch2 = MainOrchestrator(config)
    await orch2.initialize()
    assert orch2.session_id == sid, "Session ID should persist across restarts"
    await orch2.close()
