from __future__ import annotations

import re
from typing import Any

from nexus_r.events import ExecutionResult, TaskDefinition, PermissionTier

from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.store import ETDStore


class ETDApplicator:
    def __init__(self, sandbox, store: ETDStore) -> None:
        self._sandbox = sandbox
        self._store = store

    async def apply(self, etd: ETDEntry, parameters: dict[str, Any],
                    task_id: str) -> ExecutionResult | None:
        outputs: list[str] = []
        for step in etd.tool_sequence:
            action = self._substitute(step.action, parameters)
            tool_result = await self._execute_step(step.tool, action, parameters, task_id)
            if tool_result is None:
                return None
            if not tool_result.success:
                self._record_failure(etd)
                return None
            outputs.append(str(tool_result.output or ""))
            if step.verify and not self._check_verify(action, tool_result.output, step.verify):
                self._record_failure(etd)
                return None
        self._record_success(etd)
        combined = "\n".join(outputs)
        return ExecutionResult(
            success=True,
            message="ETD applied successfully.",
            output=combined,
            cost_incurred=0.0,
        )

    def _substitute(self, action: str, parameters: dict[str, Any]) -> str:
        def _replace(m: re.Match) -> str:
            key = m.group(1)
            return str(parameters.get(key, m.group(0)))
        return re.sub(r"\{(\w+)\}", _replace, action)

    async def _execute_step(self, tool: str, action: str,
                            parameters: dict[str, Any],
                            task_id: str) -> ExecutionResult | None:
        action_type = self._tool_to_action_type(tool)
        if action_type is None:
            if tool.lower() == "execution_sandbox":
                action_type = action
            else:
                return ExecutionResult(success=False, message=f"Unknown tool: {tool}")
        task_params = dict(parameters) if action_type == "run_terminal" else dict(parameters)
        task = TaskDefinition(
            raw_input=action,
            action_type=action_type,
            parameters=task_params,
            tier=PermissionTier.T1,
            task_id=task_id,
        )
        try:
            return await self._sandbox.execute(task)
        except Exception:
            return None

    def _tool_to_action_type(self, tool: str) -> str | None:
        mapping = {
            "terminal": "run_terminal",
            "execution_sandbox": None,
            "model_provider": None,
        }
        return mapping.get(tool)

    def _check_verify(self, action: str, output: Any, verify: str) -> bool:
        if verify in ("passed", "generated", "unknown"):
            return True
        if not output:
            return False
        output_str = str(output) if output else ""
        return verify in output_str

    def _record_failure(self, etd: ETDEntry) -> None:
        indexed = self._store.get(etd.id)
        if indexed:
            from modules.workflow_engine.src.invalidator import ETDInvalidator
            ETDInvalidator(self._store).record_failure(etd.id)

    def _record_success(self, etd: ETDEntry) -> None:
        indexed = self._store.get(etd.id)
        if indexed:
            from modules.workflow_engine.src.invalidator import ETDInvalidator
            ETDInvalidator(self._store).record_success(etd.id)
