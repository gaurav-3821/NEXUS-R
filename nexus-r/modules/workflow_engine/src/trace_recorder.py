from __future__ import annotations

from nexus_r.events import CausalEvent, PermissionTier


class TraceRecorder:
    def __init__(self, event_store) -> None:
        self.event_store = event_store

    async def record_step(
        self,
        task_id: str,
        step_index: int,
        tool: str,
        action: str,
        input_data: dict,
        output_data: dict,
        verification_result: str,
        model_used: str,
        cost: float,
        tier: PermissionTier,
        parent_event_id: str | None = None,
    ) -> str:
        event = CausalEvent(
            event_type="workflow_step",
            parent_event_id=parent_event_id,
            data={
                "task_id": task_id,
                "step_index": step_index,
                "tool": tool,
                "action": action,
                "input_data": input_data,
                "output_data": output_data,
            },
            verification_result=verification_result,
            model_used=model_used,
            cost=cost,
            tier=tier,
        )
        return await self.event_store.append(event)

    async def get_trace(self, task_id: str):
        trace = await self.event_store.get_by_type("workflow_step")
        return [
            event
            for event in trace
            if event.data.get("task_id") == task_id
        ]
