from __future__ import annotations

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.errors import SandboxExecutionError
from nexus_r.events import PermissionTier, TaskDefinition
from modules.execution_sandbox.src.sandbox import ExecutionSandbox
from modules.state_core.src.event_store import EventStore


@pytest.mark.asyncio
async def test_sandbox_write_read_and_search(workspace) -> None:
    config = NEXUSConfig.default(workspace)
    store = EventStore(config.database.path)
    sandbox = ExecutionSandbox(config, store)
    write_task = TaskDefinition(
        raw_input="create demo.txt",
        action_type="write_file",
        parameters={"path": "demo.txt", "content": "hello world"},
        tier=PermissionTier.T2,
    )
    await sandbox.execute(write_task)
    read_task = TaskDefinition(
        raw_input="read demo.txt",
        action_type="read_file",
        parameters={"path": "demo.txt"},
        tier=PermissionTier.T1,
    )
    search_task = TaskDefinition(
        raw_input='find "hello"',
        action_type="search_text",
        parameters={"path": ".", "pattern": "*.txt", "query": "hello"},
        tier=PermissionTier.T1,
    )
    read_result = await sandbox.execute(read_task)
    search_result = await sandbox.execute(search_task)
    assert read_result.output == "hello world"
    assert search_result.output
    await store.close()


@pytest.mark.asyncio
async def test_sandbox_blocks_traversal_and_shell_chaining(workspace) -> None:
    config = NEXUSConfig.default(workspace)
    store = EventStore(config.database.path)
    sandbox = ExecutionSandbox(config, store)
    with pytest.raises(SandboxExecutionError):
        await sandbox.execute(
            TaskDefinition(
                raw_input="read outside file",
                action_type="read_file",
                parameters={"path": "../secret.txt"},
                tier=PermissionTier.T1,
            )
        )
    with pytest.raises(SandboxExecutionError):
        await sandbox.execute(
            TaskDefinition(
                raw_input="run dangerous command",
                action_type="run_terminal",
                parameters={"command": "echo ok && dir"},
                tier=PermissionTier.T2,
            )
        )
    await store.close()
