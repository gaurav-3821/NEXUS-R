from __future__ import annotations

import asyncio

from nexus_r.config import NEXUSConfig
from nexus_r.events import Action, Event, ExecutionResult, IntentResult, TaskDefinition
from nexus_r.telemetry import RuntimeTelemetry

from modules.cognition_router.src.router import CognitionRouter
from modules.execution_sandbox.src.sandbox import ExecutionSandbox
from modules.input_gateway.src.intent_parser import IntentParser
from modules.session_manager.src.manager import SessionManager
from modules.state_core.src.event_store import EventStore
from modules.state_core.src.identity_store import IdentityStore
from modules.state_core.src.working_state import WorkingStateStore
from modules.trust_layer.src.cost_tracker import CostTracker
from modules.trust_layer.src.permission_enforcer import PermissionEnforcer
from modules.trust_layer.src.secret_registry import SecretRegistry
from modules.workflow_engine.src.trace_recorder import TraceRecorder
from modules.workflow_engine.src.pipeline import ETDPipeline
from modules.workflow_engine.src.applicator import ETDApplicator


class MainOrchestrator:
    def __init__(self, config: NEXUSConfig) -> None:
        self.config = config
        self.telemetry = RuntimeTelemetry(
            config.observability.log_path,
            enabled=config.observability.enabled,
        )
        self.event_store = EventStore(
            config.database.path,
            telemetry=self.telemetry,
            cache_size_mb=config.database.sqlite_cache_size_mb,
        )
        self.working_state = WorkingStateStore()
        self.identity_store = IdentityStore(config.database.path.parent)
        self.session_manager = SessionManager(config.workspace_root)
        self.session_id: str | None = None
        self.secret_registry = SecretRegistry(config.app_name)
        self.secret_registry.bootstrap_from_environment(
            config.models.byok_secret_name,
            config.models.byok_api_key_env,
        )
        self.parser = IntentParser()
        self.router = CognitionRouter(
            config,
            self.event_store,
            self.secret_registry,
            telemetry=self.telemetry,
        )
        self.permission_enforcer = PermissionEnforcer()
        self.cost_tracker = CostTracker(self.event_store)
        self.trace_recorder = TraceRecorder(self.event_store)
        self.sandbox = ExecutionSandbox(config, self.event_store, telemetry=self.telemetry)
        self.etd_pipeline = ETDPipeline()
        self.etd_applicator = ETDApplicator(self.sandbox, self.etd_pipeline.store)
        self._active_tasks = 0

    async def initialize(self) -> None:
        async with self.telemetry.span("orchestrator.initialize"):
            await self.event_store.initialize()
            asyncio.create_task(self.router.warm_up(), name="model-warm-up")
            self.session_manager.initialize()
            if self.session_id is None:
                self.session_id = self.session_manager.get_or_create_default_session()
                resume = self.session_manager.resume_session(self.session_id, self.config.workspace_root)
                working_state = resume.state.get("working_state")
                if isinstance(working_state, dict):
                    self.working_state.restore(working_state)

    async def close(self) -> None:
        await self.event_store.close()
        self.session_manager.close()
        self.telemetry.emit("orchestrator_closed")

    def _emit_task_failure_telemetry(self, task_id: str, error_type: str, message: str, provider_info: dict[str, object] | None = None) -> None:
        self.telemetry.increment("orchestrator.failures_total", error_type=error_type)
        self.telemetry.emit(
            "orchestrator_task_failed",
            task_id=task_id,
            error_type=error_type,
            error_message=message,
            provider_info=provider_info,
        )

    async def run_task(self, raw_input: str) -> dict[str, object]:
        self._active_tasks += 1
        self.telemetry.set_gauge("orchestrator.active_tasks", float(self._active_tasks))
        self.telemetry.increment("orchestrator.tasks_started_total")
        intent = self.parser.parse(raw_input)
        task = TaskDefinition(
            raw_input=intent.raw_input,
            action_type=intent.task_type,
            parameters=intent.parameters,
            tier=intent.suggested_tier,
        )
        permission = None
        routing = None
        trace_event_id: str | None = None
        provider_info: dict[str, object] | None = None
        try:
            async with self.telemetry.span("orchestrator.run_task", task_id=task.task_id):
                await self.initialize()
                self.working_state.begin_task(task.task_id)
                self._checkpoint_session("task_started", status="running")
                task_received = Event(
                    event_type="task_received",
                    data={"task_id": task.task_id, "raw_input": raw_input},
                )
                task_received_id = await self.event_store.append(task_received)
                intent_parsed = Event(
                    event_type="intent_parsed",
                    parent_event_id=task_received_id,
                    data={
                        "task_id": task.task_id,
                        "task_type": intent.task_type,
                        "complexity": intent.complexity,
                        "confidence": intent.confidence,
                        "parameters": intent.parameters,
                        "warnings": intent.warnings,
                    },
                )
                intent_parsed_id = await self.event_store.append(intent_parsed)
                if intent.task_type == "unknown":
                    result = ExecutionResult(
                        success=False,
                        message="Unsupported Phase 1 task.",
                        error="unknown task type",
                    )
                    return await self._finish(task, intent, None, result, None, intent_parsed_id)

                action = Action(
                    name=task.action_type,
                    tier=task.tier,
                    target=task.parameters.get("path"),
                    metadata=task.parameters,
                )
                trace_event_id = intent_parsed_id
                permission = await self.permission_enforcer.check(action, task.tier)
                audit_event_id = await self.event_store.append(
                    Event(
                        event_type="audit_log",
                        parent_event_id=intent_parsed_id,
                        data={
                            "task_id": task.task_id,
                            "action": action.name,
                            "allowed": permission.allowed,
                            "tier": permission.tier.value,
                            "reason": permission.reason,
                            "metadata": permission.redacted_metadata,
                        },
                    )
                )
                trace_event_id = audit_event_id
                if not permission.allowed:
                    result = ExecutionResult(success=False, message=permission.reason, error="permission denied")
                    return await self._finish(task, intent, None, result, permission, audit_event_id)

                etd_match = await self.etd_pipeline.find_match(intent)
                if etd_match is not None:
                    etd_result = await self.etd_applicator.apply(
                        etd_match, task.parameters, task.task_id,
                    )
                    if etd_result is not None and etd_result.success:
                        trace_event_id = await self.trace_recorder.record_step(
                            task_id=task.task_id,
                            step_index=1,
                            tool="etd_cache",
                            action=intent.task_type,
                            input_data=task.parameters,
                            output_data={"message": etd_result.message, "output": etd_result.output},
                            verification_result="passed",
                            model_used="etd_cache",
                            cost=0.0,
                            tier=task.tier,
                            parent_event_id=audit_event_id,
                        )
                        result = etd_result
                        result.cost_incurred = 0.0
                        if result.success:
                            await self.cost_tracker.record(task.task_id, 0.0, "etd_cache", task.tier)
                        return await self._finish(task, intent, None, result, permission, trace_event_id)
                    self.telemetry.emit("etd_fallback", task_id=task.task_id, sig=etd_match.intent_signature)

                routing = await self.router.route(intent)
                self.working_state.set_routing(task.task_id, routing.model_dump(mode="json"))
                self._checkpoint_session("routing_decided", status="running")
                routing_event_id = await self.event_store.append(
                    Event(
                        event_type="routing_decided",
                        parent_event_id=audit_event_id,
                        data={
                    "task_id": task.task_id,
                    "selected_model": routing.selected_model,
                    "selected_tier": routing.selected_tier.value,
                    "cost_estimate": routing.cost_estimate,
                    "rationale": routing.rationale,
                    "etd_match_found": routing.etd_match_found,
                    "car_tier": routing.car_tier,
                    "car_tier_name": routing.car_tier_name,
                    "parallel_probe_used": routing.parallel_probe_used,
                    "de_escalated": routing.de_escalated,
                    "requires_approval": routing.requires_approval,
                },
                    )
                )
                trace_event_id = routing_event_id
                if task.action_type == "general_llm":
                    provider_event_id = await self.event_store.append(
                        Event(
                            event_type="provider_invocation",
                            parent_event_id=routing_event_id,
                            data={
                                "task_id": task.task_id,
                                "preferred_model": routing.selected_model,
                            },
                        )
                    )
                    completion = await self.router.complete(
                        intent_result=intent,
                        preferred="byok" if routing.selected_model == self.config.models.byok_model else "local",
                    )
                    provider_result_id = await self.event_store.append(
                        Event(
                            event_type="provider_result",
                            parent_event_id=provider_event_id,
                            data={
                                "task_id": task.task_id,
                                "model_name": completion["model_name"],
                                "used_mock": completion["used_mock"],
                                "fallback_used": completion["fallback_used"],
                                "latency_ms": completion["latency_ms"],
                                "cost": completion["cost"],
                            },
                        )
                    )
                    result = ExecutionResult(
                        success=True,
                        message="Model completion generated.",
                        output=completion["text"],
                        cost_incurred=float(completion["cost"]),
                    )
                    trace_tool = "model_provider"
                    trace_model = str(completion["model_name"])
                    trace_cost = float(completion["cost"])
                    verification = "generated"
                    trace_parent_id = provider_result_id
                else:
                    result = await self.sandbox.execute(task)
                    trace_tool = "execution_sandbox"
                    trace_model = routing.selected_model
                    trace_cost = routing.cost_estimate if result.success else 0.0
                    verification = "passed" if result.success else "failed"
                    trace_parent_id = routing_event_id
                trace_event_id = await self.trace_recorder.record_step(
                    task_id=task.task_id,
                    step_index=1,
                    tool=trace_tool,
                    action=task.action_type,
                    input_data=task.parameters,
                    output_data={"message": result.message, "output": result.output},
                    verification_result=verification,
                    model_used=trace_model,
                    cost=trace_cost,
                    tier=task.tier,
                    parent_event_id=trace_parent_id,
                )
                if result.success:
                    await self.cost_tracker.record(task.task_id, trace_cost, trace_model, task.tier)
                    trace = await self.trace_recorder.get_trace(task.task_id)
                    etd_entry = await self.etd_pipeline.process_success(trace, normalized_input=intent.normalized_input)
                    if etd_entry is not None:
                        self.telemetry.emit("etd_learned", task_id=task.task_id, sig=etd_entry.intent_signature)
                self.router.record_outcome(
                    task_type=intent.task_type,
                    assigned_tier=routing.car_tier,
                    actual_tier=routing.car_tier,
                    success=result.success,
                    cost=trace_cost,
                    latency_ms=0.0,
                )
                return await self._finish(task, intent, routing, result, permission, trace_event_id)
        except Exception as exc:
            self._emit_task_failure_telemetry(
                task.task_id,
                type(exc).__name__,
                str(exc),
                provider_info,
            )
            provider_event_data: dict[str, object] = {
                "task_id": task.task_id,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
            if provider_info:
                provider_event_data["provider_info"] = provider_info
            try:
                error_event_id = await self.event_store.append(
                    Event(
                        event_type="task_error",
                        parent_event_id=trace_event_id,
                        data=provider_event_data,
                    )
                )
            except Exception:
                error_event_id = trace_event_id
            result = ExecutionResult(success=False, message="Task failed during execution.", error=str(exc))
            return await self._finish(task, intent, routing, result, permission, error_event_id)
        finally:
            self._active_tasks -= 1
            self.telemetry.set_gauge("orchestrator.active_tasks", float(self._active_tasks))

    async def get_history(self) -> list[dict[str, object]]:
        await self.initialize()
        history = []
        for event in await self.event_store.get_by_type("task_completed"):
            history.append(event.data)
        return history

    async def get_cost_summary(self) -> dict[str, object]:
        await self.initialize()
        return await self.cost_tracker.summary()

    def get_telemetry_snapshot(self) -> dict[str, dict[str, float]]:
        return self.telemetry.snapshot()

    def get_config(self) -> dict[str, object]:
        return self.config.redacted_dict()

    async def _finish(
        self,
        task: TaskDefinition,
        intent,
        routing,
        result: ExecutionResult,
        permission,
        trace_event_id: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "task_id": task.task_id,
            "normalized_input": intent.normalized_input,
            "task_type": task.action_type,
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "routing_model": routing.selected_model if routing else None,
            "tier": task.tier.value,
            "trace_event_id": trace_event_id,
            "permission_allowed": permission.allowed if permission else False,
        }
        try:
            await self.event_store.append(
                Event(
                    event_type="task_completed",
                    parent_event_id=trace_event_id,
                    data=payload,
                )
            )
        except Exception:
            payload["persistence_warning"] = "task_completed event could not be persisted"
        self.working_state.complete_task(
            task.task_id,
            payload,
            status="completed" if result.success else "failed",
        )
        self._checkpoint_session(
            "task_finished",
            status="idle" if result.success else "degraded",
            last_error=result.error,
        )
        self.telemetry.increment("orchestrator.tasks_completed_total", 1.0, success=result.success)
        self.telemetry.emit(
            "orchestrator_task_finished",
            task_id=task.task_id,
            success=result.success,
            routing_model=payload["routing_model"],
            persistence_warning=payload.get("persistence_warning"),
        )
        return payload

    def _checkpoint_session(
        self,
        reason: str,
        *,
        status: str,
        last_error: str | None = None,
    ) -> None:
        if self.session_id is None:
            return
        self.session_manager.checkpoint(
            self.session_id,
            {
                "working_state": self.working_state.snapshot(),
                "workspace_root": str(self.config.workspace_root),
            },
            checkpoint_reason=reason,
            status=status,
            last_error=last_error,
        )
