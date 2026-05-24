from __future__ import annotations

"""
Sandbox Escape — Phase C security boundary validation.
Runs sandbox path traversal + injection tests.
See: RUNTIME STABILITY — T4 Sandbox Security
"""


def test_sandbox_boundary_enforcement() -> None:
    from nexus_r.config import NEXUSConfig
    from nexus_r.events import PermissionTier, TaskDefinition
    from nexus_r.errors import SandboxExecutionError
    from nexus_r.events import EventStore
    from modules.execution_sandbox.src.sandbox import ExecutionSandbox
    from pathlib import Path
    import pytest
    import tempfile

    wd = Path(tempfile.mkdtemp())
    (wd / "src").mkdir()
    (wd / "src" / "safe.py").write_text("print('ok')")
    config = NEXUSConfig.default(wd)

    import asyncio

    async def test():
        store = EventStore(config.database.path)
        await store.initialize()
        sandbox = ExecutionSandbox(config, store)
        attacks = [
            ("../etc/passwd", "read_file", {"path": "../etc/passwd"}),
            ("; rm -rf /", "run_terminal", {"command": "echo ok; rm -rf /"}),
            ("&& dir", "run_terminal", {"command": "echo ok && dir"}),
            ("| cat", "run_terminal", {"command": "ls | cat /etc/passwd"}),
        ]
        for label, action, params in attacks:
            task = TaskDefinition(raw_input=label, action_type=action,
                                  parameters=params, tier=PermissionTier.T1)
            with pytest.raises(SandboxExecutionError):
                await sandbox.execute(task)
        await store.close()

    asyncio.run(test())
