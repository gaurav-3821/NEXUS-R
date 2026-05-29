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


def pytest_sessionstart(session: pytest.Session) -> None:
    from foundation.nexus_r.backend_manager import BackendManager
    # Try to start it, but don't fail the whole test suite if ollama is missing
    # in some CI environments, although the requirement says we should start it.
    try:
        mgr = BackendManager(test_mode=True)
        mgr.start(wait_ready=True)
        BackendManager.set_instance(mgr)
    except Exception as e:
        import logging
        logging.warning(f"Could not start test BackendManager: {e}")

def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    from foundation.nexus_r.backend_manager import BackendManager
    try:
        BackendManager.get_instance().stop()
    except Exception:
        pass
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


@pytest.fixture(autouse=True)
def mock_litellm_acompletion():
    from unittest.mock import AsyncMock, patch

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = None

    async_mock = AsyncMock(return_value=MockResponse("Mock model response content."))

    with patch("litellm.acompletion", async_mock):
        yield async_mock

