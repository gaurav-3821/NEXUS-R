from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
import json
from pathlib import Path
import threading
from time import perf_counter, time
from typing import Any


def _normalize_metric_key(name: str, tags: dict[str, Any]) -> str:
    if not tags:
        return name
    suffix = ",".join(f"{key}={tags[key]}" for key in sorted(tags))
    return f"{name}[{suffix}]"


class RuntimeTelemetry:
    def __init__(self, log_path: Path, enabled: bool = True) -> None:
        self.log_path = Path(log_path)
        self.enabled = enabled
        self._log_lock = threading.Lock()
        self._metric_lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields: Any) -> None:
        if not self.enabled:
            return
        payload = {
            "timestamp_unix": round(time(), 6),
            "event": event,
            **fields,
        }
        line = json.dumps(payload, default=str, sort_keys=True)
        with self._log_lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def increment(self, name: str, amount: float = 1.0, **tags: Any) -> None:
        key = _normalize_metric_key(name, tags)
        with self._metric_lock:
            self._counters[key] += amount

    def set_gauge(self, name: str, value: float, **tags: Any) -> None:
        key = _normalize_metric_key(name, tags)
        with self._metric_lock:
            self._gauges[key] = value

    def snapshot(self) -> dict[str, dict[str, float]]:
        with self._metric_lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }

    @asynccontextmanager
    async def span(self, name: str, **fields: Any):
        started = perf_counter()
        self.emit("span_start", span=name, **fields)
        try:
            yield
        except asyncio.CancelledError:
            duration_ms = (perf_counter() - started) * 1000
            self.increment("runtime.cancellations_total")
            self.emit(
                "span_end",
                span=name,
                status="cancelled",
                duration_ms=round(duration_ms, 3),
                **fields,
            )
            raise
        except Exception as exc:
            duration_ms = (perf_counter() - started) * 1000
            self.increment("runtime.failures_total", span=name)
            self.emit(
                "span_end",
                span=name,
                status="error",
                duration_ms=round(duration_ms, 3),
                error_type=type(exc).__name__,
                error=str(exc),
                **fields,
            )
            raise
        else:
            duration_ms = (perf_counter() - started) * 1000
            self.emit(
                "span_end",
                span=name,
                status="ok",
                duration_ms=round(duration_ms, 3),
                **fields,
            )
