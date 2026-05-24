from __future__ import annotations

from datetime import datetime, timezone

from nexus_r.events import Event, PermissionTier


class CostTracker:
    def __init__(self, event_store, ws_handler=None) -> None:
        self.event_store = event_store
        self._ws_handler = ws_handler

    async def record(self, task_id: str, amount: float, model: str, tier: PermissionTier) -> None:
        event = Event(
            event_type="cost_recorded",
            data={
                "task_id": task_id,
                "amount": amount,
                "model": model,
                "tier": tier.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.event_store.append(event)
        if self._ws_handler is not None:
            await self._ws_handler.notify_cost_update(
                task_id=task_id,
                amount=amount,
                model=model,
                tier=tier.value,
            )

    async def summary(self) -> dict[str, object]:
        totals: dict[str, float] = {"total_cost": 0.0}
        per_task: dict[str, float] = {}
        for event in await self.event_store.get_by_type("cost_recorded"):
            amount = float(event.data["amount"])
            totals["total_cost"] += amount
            totals[f"tier_{event.data['tier']}"] = totals.get(f"tier_{event.data['tier']}", 0.0) + amount
            totals[f"model_{event.data['model']}"] = totals.get(f"model_{event.data['model']}", 0.0) + amount
            task_id = event.data["task_id"]
            per_task[task_id] = per_task.get(task_id, 0.0) + amount
        return {
            "totals": dict(totals),
            "per_task": dict(per_task),
        }
