from __future__ import annotations


class TraceAnalyzer:
    def __init__(self, trace_recorder) -> None:
        self.trace_recorder = trace_recorder

    async def summarize(self, task_id: str) -> dict[str, object]:
        trace = await self.trace_recorder.get_trace(task_id)
        tools = [event.data.get("tool") for event in trace]
        total_cost = sum(float(getattr(event, "cost", 0.0)) for event in trace)
        return {
            "task_id": task_id,
            "steps": len(trace),
            "tools": tools,
            "total_cost": total_cost,
        }
