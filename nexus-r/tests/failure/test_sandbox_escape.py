from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import EventStore, PermissionTier, TaskDefinition
from nexus_r.errors import SandboxExecutionError
from modules.execution_sandbox.src.sandbox import ExecutionSandbox


ROOT = Path(__file__).resolve().parents[2]


async def _make_sandbox(wd: Path):
    (wd / "src").mkdir(parents=True, exist_ok=True)
    (wd / "src" / "safe.py").write_text("print('ok')")
    config = NEXUSConfig.default(wd)
    store = EventStore(config.database.path)
    await store.initialize()
    sandbox = ExecutionSandbox(config, store)
    return sandbox, store


@pytest.mark.asyncio
async def test_path_traversal_etc_passwd_blocked() -> None:
    wd = Path(tempfile.mkdtemp()) / "sandbox-traversal"
    sandbox, store = await _make_sandbox(wd)
    task = TaskDefinition(
        raw_input="../etc/passwd", action_type="read_file",
        parameters={"path": "../etc/passwd"}, tier=PermissionTier.T1,
    )
    with pytest.raises(SandboxExecutionError):
        await sandbox.execute(task)
    await store.close()


@pytest.mark.asyncio
async def test_shell_injection_rm_rf_blocked() -> None:
    wd = Path(tempfile.mkdtemp()) / "sandbox-injection"
    sandbox, store = await _make_sandbox(wd)
    task = TaskDefinition(
        raw_input="rm -rf /", action_type="run_terminal",
        parameters={"command": "echo ok; rm -rf /"}, tier=PermissionTier.T1,
    )
    with pytest.raises(SandboxExecutionError):
        await sandbox.execute(task)
    await store.close()


@pytest.mark.asyncio
async def test_shell_injection_and_chaining_blocked() -> None:
    wd = Path(tempfile.mkdtemp()) / "sandbox-chaining"
    sandbox, store = await _make_sandbox(wd)
    for cmd, label in [
        ("echo ok && dir", "&& chaining"),
        ("ls | cat /etc/passwd", "pipe"),
        ("dir > output.txt", "redir_out"),
        ("sort < input.txt", "redir_in"),
    ]:
        task = TaskDefinition(
            raw_input=label, action_type="run_terminal",
            parameters={"command": cmd}, tier=PermissionTier.T1,
        )
        with pytest.raises(SandboxExecutionError):
            await sandbox.execute(task)
    await store.close()
