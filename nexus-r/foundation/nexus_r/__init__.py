"""Foundation package for NEXUS-R."""

from .config import NEXUSConfig
from .events import (
    Action,
    CausalEvent,
    Event,
    EventStore,
    ExecutionResult,
    IntentResult,
    PermissionDecision,
    PermissionTier,
    RoutingDecision,
    TaskDefinition,
)
from .telemetry import RuntimeTelemetry

__all__ = [
    "Action",
    "CausalEvent",
    "Event",
    "EventStore",
    "ExecutionResult",
    "IntentResult",
    "NEXUSConfig",
    "PermissionDecision",
    "PermissionTier",
    "RoutingDecision",
    "TaskDefinition",
    "RuntimeTelemetry",
]
