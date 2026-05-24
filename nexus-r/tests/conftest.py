from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_TMP = Path.cwd() / ".test-tmp"


def _force_remove(path: Path) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
    except PermissionError:
        for p in sorted(path.rglob("*"), key=lambda p: len(str(p)), reverse=True):
            try:
                if p.is_file():
                    p.chmod(0o777)
                    p.unlink()
            except PermissionError:
                pass
        try:
            shutil.rmtree(path, ignore_errors=True)
        except PermissionError:
            pass


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("TEMP", str(TEST_TMP))
    os.environ.setdefault("TMP", str(TEST_TMP))
    os.environ.setdefault("TMPDIR", str(TEST_TMP))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _force_remove(TEST_TMP)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("alpha\nbeta\nhello world\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
async def warmup_orchestrator(workspace) -> None:
    from nexus_r.config import NEXUSConfig
    from modules.orchestrator.src.orchestrator import MainOrchestrator

    config = NEXUSConfig.default(workspace)
    orch = MainOrchestrator(config)
    await orch.initialize()
    await orch.run_task("list files")
    await orch.close()
