from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkingStateStore:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_task_id: str | None = None

    def begin_task(self, task_id: str) -> None:
        self.latest_task_id = task_id
        self.tasks[task_id] = {"status": "running", "routing": {}, "result": {}}

    def set_routing(self, task_id: str, routing: dict[str, Any]) -> None:
        self.tasks.setdefault(task_id, {"status": "running", "routing": {}, "result": {}})
        self.tasks[task_id]["routing"] = dict(routing)

    def complete_task(self, task_id: str, result: dict[str, Any], status: str = "completed") -> None:
        self.tasks.setdefault(task_id, {"status": "running", "routing": {}, "result": {}})
        self.tasks[task_id]["result"] = dict(result)
        self.tasks[task_id]["status"] = status

    def restore(self, snapshot: dict[str, Any]) -> None:
        tasks = snapshot.get("completed_tasks") or snapshot.get("tasks") or {}
        latest_task_id = snapshot.get("latest_task_id")
        restored: dict[str, dict[str, Any]] = {}
        for task_id, payload in tasks.items():
            if not isinstance(task_id, str) or not isinstance(payload, dict):
                continue
            restored[task_id] = {
                "status": payload.get("status", "running"),
                "routing": dict(payload.get("routing", {})),
                "result": dict(payload.get("result", {})),
            }
        self.tasks = restored
        self.latest_task_id = latest_task_id if isinstance(latest_task_id, str) else None

    def snapshot(self) -> dict[str, Any]:
        active = {
            task_id: data
            for task_id, data in self.tasks.items()
            if data.get("status") == "running"
        }
        return {
            "latest_task_id": self.latest_task_id,
            "active_task_count": len(active),
            "active_tasks": active,
            "completed_tasks": self.tasks,
        }
