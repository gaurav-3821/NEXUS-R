from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from nexus_r.events import Event, PermissionTier


class CostTracker:
    def __init__(self, event_store) -> None:
        self.event_store = event_store

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

    async def summary(self) -> dict[str, object]:
        totals = defaultdict(float)
        per_task = defaultdict(float)
        for event in await self.event_store.get_by_type("cost_recorded"):
            amount = float(event.data["amount"])
            totals["total"] += amount
            totals[f"tier_{event.data['tier']}"] += amount
            totals[f"model_{event.data['model']}"] += amount
            per_task[event.data["task_id"]] += amount
        return {
            "totals": dict(totals),
            "per_task": dict(per_task),
        }
