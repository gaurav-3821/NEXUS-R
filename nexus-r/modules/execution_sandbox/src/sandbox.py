from __future__ import annotations

import asyncio
from fnmatch import fnmatch
from pathlib import Path
import shlex
from typing import Callable

from nexus_r.config import NEXUSConfig
from nexus_r.errors import SandboxExecutionError
from nexus_r.events import Event, ExecutionResult, TaskDefinition
from nexus_r.telemetry import RuntimeTelemetry


class ExecutionSandbox:
    _IGNORED_DIRS = {".git", ".nexus-r", "__pycache__", ".pytest_cache", ".ruff_cache"}

    def __init__(
        self,
        config: NEXUSConfig,
        event_store,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self.config = config
        self.event_store = event_store
        self.telemetry = telemetry

    async def execute(self, task: TaskDefinition) -> ExecutionResult:
        await self.event_store.append(
            Event(
                event_type="sandbox_invocation",
                data={"task_id": task.task_id, "action": task.action_type, "parameters": task.parameters},
            )
        )
        try:
            handler = self._handler_for(task.action_type)
            if self.telemetry is not None:
                self.telemetry.emit(
                    "sandbox_execution_started",
                    task_id=task.task_id,
                    action=task.action_type,
                )
            result = await handler(task)
            if self.telemetry is not None:
                self.telemetry.increment("sandbox.success_total", action=task.action_type)
                self.telemetry.emit(
                    "sandbox_execution_completed",
                    task_id=task.task_id,
                    action=task.action_type,
                    success=result.success,
                )
            await self.event_store.append(
                Event(
                    event_type="sandbox_result",
                    data={
                        "task_id": task.task_id,
                        "action": task.action_type,
                        "success": result.success,
                        "message": result.message,
                    },
                )
            )
            return result
        except Exception as exc:
            if self.telemetry is not None:
                self.telemetry.increment("sandbox.failures_total", action=task.action_type)
                self.telemetry.emit(
                    "sandbox_execution_failed",
                    task_id=task.task_id,
                    action=task.action_type,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            await self.event_store.append(
                Event(
                    event_type="sandbox_result",
                    data={
                        "task_id": task.task_id,
                        "action": task.action_type,
                        "success": False,
                        "message": str(exc),
                    },
                )
            )
            raise

    def _handler_for(self, action_type: str) -> Callable[[TaskDefinition], asyncio.Future]:
        handlers = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "append_file": self._append_file,
            "search_text": self._search_text,
            "run_terminal": self._run_terminal,
        }
        if action_type not in handlers:
            raise SandboxExecutionError(f"Unsupported action: {action_type}")
        return handlers[action_type]

    async def _list_files(self, task: TaskDefinition) -> ExecutionResult:
        return await asyncio.to_thread(self._list_files_sync, task)

    def _list_files_sync(self, task: TaskDefinition) -> ExecutionResult:
        base = self._resolve_path(task.parameters.get("path", "."))
        pattern = task.parameters.get("pattern", "*")
        files = sorted(
            str(path.relative_to(self.config.workspace_root))
            for path in self._iter_workspace_files(base)
            if fnmatch(path.name, pattern)
        )
        return ExecutionResult(success=True, message="Listed files.", output=files)

    async def _read_file(self, task: TaskDefinition) -> ExecutionResult:
        return await asyncio.to_thread(self._read_file_sync, task)

    def _read_file_sync(self, task: TaskDefinition) -> ExecutionResult:
        path = self._resolve_path(task.parameters.get("path", ""))
        if not path.exists() or not path.is_file():
            return ExecutionResult(success=False, message="File not found.", error=str(path))
        return ExecutionResult(success=True, message="Read file.", output=path.read_text(encoding="utf-8"))

    async def _write_file(self, task: TaskDefinition) -> ExecutionResult:
        return await asyncio.to_thread(self._write_file_sync, task)

    def _write_file_sync(self, task: TaskDefinition) -> ExecutionResult:
        path = self._resolve_path(task.parameters.get("path", "untitled.txt"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(task.parameters.get("content", "")), encoding="utf-8")
        return ExecutionResult(success=True, message="Wrote file.", output=str(path.relative_to(self.config.workspace_root)))

    async def _append_file(self, task: TaskDefinition) -> ExecutionResult:
        return await asyncio.to_thread(self._append_file_sync, task)

    def _append_file_sync(self, task: TaskDefinition) -> ExecutionResult:
        path = self._resolve_path(task.parameters.get("path", "untitled.txt"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(str(task.parameters.get("content", "")))
        return ExecutionResult(success=True, message="Appended file.", output=str(path.relative_to(self.config.workspace_root)))

    async def _search_text(self, task: TaskDefinition) -> ExecutionResult:
        return await asyncio.to_thread(self._search_text_sync, task)

    def _search_text_sync(self, task: TaskDefinition) -> ExecutionResult:
        base = self._resolve_path(task.parameters.get("path", "."))
        pattern = task.parameters.get("pattern", "*")
        query = str(task.parameters.get("query", ""))
        matches: list[dict[str, object]] = []
        if not query:
            return ExecutionResult(success=False, message="Search query is empty.", error="missing query")
        for file_path in self._iter_workspace_files(base):
            if not fnmatch(file_path.name, pattern):
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for index, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    matches.append(
                        {
                            "path": str(file_path.relative_to(self.config.workspace_root)),
                            "line": index,
                            "text": line.strip(),
                        }
                    )
        return ExecutionResult(success=True, message="Search complete.", output=matches)

    async def _run_terminal(self, task: TaskDefinition) -> ExecutionResult:
        command = str(task.parameters.get("command", "")).strip()
        if not command:
            return ExecutionResult(success=False, message="Terminal command missing.", error="missing command")
        if any(token in command for token in ("&&", "||", ";", "|", ">", "<")):
            raise SandboxExecutionError("Shell chaining and redirection are not allowed.")
        argv = shlex.split(command, posix=False)
        verb = argv[0].lower()
        if verb not in [item.lower() for item in self.config.sandbox.allowed_commands]:
            raise SandboxExecutionError(f"Command '{verb}' is not on the allowlist.")
        builtin = self._run_builtin(argv)
        if builtin is not None:
            return builtin
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(self.config.workspace_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.sandbox.command_timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise SandboxExecutionError("Terminal command timed out.") from exc
        return ExecutionResult(
            success=process.returncode == 0,
            message="Command executed.",
            output=stdout.decode("utf-8", errors="ignore").strip(),
            error=stderr.decode("utf-8", errors="ignore").strip() or None,
            command=command,
        )

    def _run_builtin(self, argv: list[str]) -> ExecutionResult | None:
        verb = argv[0].lower()
        if verb in {"dir", "ls"}:
            target = self._resolve_path(argv[1] if len(argv) > 1 else ".")
            entries = sorted(path.name for path in target.iterdir())
            return ExecutionResult(success=True, message="Command executed.", output=entries, command=" ".join(argv))
        if verb == "pwd":
            return ExecutionResult(success=True, message="Command executed.", output=str(self.config.workspace_root), command=" ".join(argv))
        if verb == "type":
            target = self._resolve_path(argv[1] if len(argv) > 1 else "")
            if not target.exists():
                return ExecutionResult(success=False, message="File not found.", error=str(target), command=" ".join(argv))
            return ExecutionResult(success=True, message="Command executed.", output=target.read_text(encoding="utf-8"), command=" ".join(argv))
        if verb == "echo":
            return ExecutionResult(success=True, message="Command executed.", output=" ".join(argv[1:]), command=" ".join(argv))
        return None

    def _resolve_path(self, value: str) -> Path:
        relative = Path(value or ".")
        candidate = (self.config.workspace_root / relative).resolve()
        workspace = self.config.workspace_root.resolve()
        if candidate != workspace and workspace not in candidate.parents:
            raise SandboxExecutionError("Path escapes workspace root.")
        return candidate

    def _iter_workspace_files(self, base: Path):
        for path in base.rglob("*"):
            if any(part in self._IGNORED_DIRS for part in path.parts):
                continue
            if path.is_file():
                yield path
