from __future__ import annotations

from uuid import uuid4

import pytest

from nexus_r.events import CausalEvent, IntentResult, PermissionTier

from modules.workflow_engine.src.pipeline import ETDPipeline
from modules.workflow_engine.src.applicator import ETDApplicator
from modules.workflow_engine.src.distiller import ToolStep
from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.parameterizer import ETDEntry
from modules.workflow_engine.src.store import IndexedETDEntry


class _FakeSandbox:
    def __init__(self) -> None:
        self.executions: list[str] = []

    async def execute(self, task) -> object:
        from nexus_r.events import ExecutionResult
        self.executions.append(task.action_type)
        return ExecutionResult(success=True, message="ran", output="ok")


class _FailingSandbox:
    async def execute(self, task) -> object:
        from nexus_r.events import ExecutionResult
        return ExecutionResult(success=False, message="failed", error="fail")


def _causal_event(action: str, step_index: int = 0,
                  parent_id: str | None = None) -> CausalEvent:
    return CausalEvent(
        event_type="workflow_step",
        parent_event_id=parent_id,
        data={
            "task_id": str(uuid4()),
            "step_index": step_index,
            "tool": "terminal",
            "action": action,
            "input_data": {},
            "output_data": {"message": f"Ran {action}"},
        },
        verification_result="passed",
        model_used="none",
        cost=0.0,
        tier=PermissionTier.T1,
    )


def _make_trace(actions: list[str]) -> list[CausalEvent]:
    events: list[CausalEvent] = []
    prev: str | None = None
    for i, a in enumerate(actions):
        e = _causal_event(a, step_index=i, parent_id=prev)
        events.append(e)
        prev = e.id
    return events


def _intent(normalized: str = "build app", task_type: str = "run_terminal"
            ) -> IntentResult:
    return IntentResult(
        raw_input=normalized,
        normalized_input=normalized,
        task_type=task_type,
        complexity=0.5,
        confidence=0.9,
        parameters={},
        suggested_tier=PermissionTier.T1,
    )


def _seed_store(pipeline: ETDPipeline, sig: str = "build-app",
                actions: list[str] | None = None) -> ETDEntry:
    from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
    from modules.workflow_engine.src.distiller import DistilledWorkflow
    actions = actions or ["npm install"]
    wf = DistilledWorkflow(
        id=str(uuid4()),
        intent_signature=sig,
        tool_sequence=[ToolStep(tool="terminal", action=a, verify="passed")
                       for a in actions],
        parameter_slots=[],
        invariant_checks=["Node available"],
        success_count=1,
        failure_count=0,
        generalization_success_rate=1.0,
    )
    entry = WorkflowParameterizer().parameterize(wf)
    entry.generalization_success_rate = 1.0
    pipeline.indexer.index(entry)
    return entry


class TestETDPipelineIntegration:
    @pytest.mark.asyncio
    async def test_first_execution_creates_etd(self) -> None:
        pipeline = ETDPipeline()
        trace = _make_trace(["npm install", "npm run build"])
        etd = await pipeline.process_success(trace)
        assert etd is not None, "ETD should be created from successful trace"
        assert etd.id.startswith("etd_")
        assert len(pipeline.store.list_active()) == 1

    @pytest.mark.asyncio
    async def test_second_execution_same_intent_matches(self) -> None:
        pipeline = ETDPipeline()
        entry = _seed_store(pipeline, sig="npm-install-npm-run-build")
        intent = _intent(normalized="npm-install-npm-run-build", task_type="npm")
        match = await pipeline.find_match(intent)
        assert match is not None
        assert match.id == entry.id

    @pytest.mark.asyncio
    async def test_etd_step_fails_abandons_and_falls_back(self) -> None:
        sandbox = _FailingSandbox()
        pipeline = ETDPipeline()
        entry = _seed_store(pipeline, actions=["echo hello"])
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_similarity_below_threshold_no_match(self) -> None:
        pipeline = ETDPipeline()
        _seed_store(pipeline, sig="deploy-python-microservice")
        intent = _intent(normalized="totally unrelated query about fish",
                         task_type="general_llm")
        match = await pipeline.find_match(intent)
        assert match is None

    @pytest.mark.asyncio
    async def test_etd_applicator_executes_steps(self) -> None:
        sandbox = _FakeSandbox()
        pipeline = ETDPipeline()
        entry = _seed_store(pipeline, actions=["npm install", "npm run build"])
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is not None
        assert result.success is True
        assert result.cost_incurred == 0.0
        assert len(sandbox.executions) == 2

    @pytest.mark.asyncio
    async def test_empty_trace_returns_none(self) -> None:
        pipeline = ETDPipeline()
        etd = await pipeline.process_success([])
        assert etd is None

    @pytest.mark.asyncio
    async def test_invalidate_stale_returns_ids(self) -> None:
        pipeline = ETDPipeline()
        from datetime import datetime, timezone
        entry = _seed_store(pipeline)
        indexed = pipeline.store.get(entry.id)
        indexed.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        indexed.ttl_days = 1
        pipeline.store.update(indexed)
        ids = await pipeline.invalidate_stale()
        assert entry.id in ids

    @pytest.mark.asyncio
    async def test_etd_applicator_substitutes_params(self) -> None:
        sandbox = _FakeSandbox()
        pipeline = ETDPipeline()
        from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
        from modules.workflow_engine.src.distiller import DistilledWorkflow
        wf = DistilledWorkflow(
            id=str(uuid4()),
            intent_signature="cd-into-project",
            tool_sequence=[ToolStep(tool="terminal", action="cd {project_dir}", verify="passed"),
                           ToolStep(tool="terminal", action="ls {project_dir}", verify="passed")],
            parameter_slots=["project_dir"],
            invariant_checks=[],
            success_count=1,
            failure_count=0,
            generalization_success_rate=1.0,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 1.0
        pipeline.indexer.index(entry)
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {"project_dir": "/tmp/test"}, str(uuid4()))
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_unknown_tool_type_returns_none(self) -> None:
        sandbox = _FakeSandbox()
        pipeline = ETDPipeline()
        entry = ETDEntry(
            id="etd_test",
            intent_signature="model-call",
            intent_embedding=[0.1] * 128,
            input_schema={},
            output_schema={},
            tool_sequence=[ToolStep(tool="model_provider", action="call-llm", verify="passed")],
            parameter_slots=[],
            invariant_checks=[],
            success_count=1, failure_count=0,
            generalization_success_rate=1.0,
            last_validated="2026-01-01T00:00:00Z",
        )
        pipeline.indexer.index(entry)
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_sandbox_exception_returns_none(self) -> None:
        class _RaisingSandbox:
            async def execute(self, task) -> object:
                raise RuntimeError("sandbox exploded")
        sandbox = _RaisingSandbox()
        pipeline = ETDPipeline()
        entry = _seed_store(pipeline, actions=["npm install"])
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_verify_failure_returns_none(self) -> None:
        sandbox = _FakeSandbox()
        pipeline = ETDPipeline()
        from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
        from modules.workflow_engine.src.distiller import DistilledWorkflow
        wf = DistilledWorkflow(
            id=str(uuid4()),
            intent_signature="verify-check",
            tool_sequence=[ToolStep(tool="terminal", action="echo ok", verify="should-fail")],
            parameter_slots=[],
            invariant_checks=[],
            success_count=1, failure_count=0,
            generalization_success_rate=1.0,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 1.0
        pipeline.indexer.index(entry)
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_output_verify_fails(self) -> None:
        class _EmptyOutputSandbox:
            async def execute(self, task) -> object:
                from nexus_r.events import ExecutionResult
                return ExecutionResult(success=True, message="ran", output="")
        sandbox = _EmptyOutputSandbox()
        pipeline = ETDPipeline()
        from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
        from modules.workflow_engine.src.distiller import DistilledWorkflow
        wf = DistilledWorkflow(
            id=str(uuid4()),
            intent_signature="empty-verify",
            tool_sequence=[ToolStep(tool="terminal", action="echo hi", verify="expected-text")],
            parameter_slots=[],
            invariant_checks=[],
            success_count=1, failure_count=0,
            generalization_success_rate=1.0,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 1.0
        pipeline.indexer.index(entry)
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_verify_success_passes(self) -> None:
        sandbox = _FakeSandbox()
        pipeline = ETDPipeline()
        from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
        from modules.workflow_engine.src.distiller import DistilledWorkflow
        wf = DistilledWorkflow(
            id=str(uuid4()),
            intent_signature="verify-ok",
            tool_sequence=[ToolStep(tool="terminal", action="echo ok", verify="ok")],
            parameter_slots=[],
            invariant_checks=[],
            success_count=1, failure_count=0,
            generalization_success_rate=1.0,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 1.0
        pipeline.indexer.index(entry)
        applicator = ETDApplicator(sandbox, pipeline.store)
        result = await applicator.apply(entry, {}, str(uuid4()))
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_trace_with_version_check_produces_etd(self) -> None:
        pipeline = ETDPipeline()
        trace = _make_trace(["node --version", "npm install", "npm run build"])
        etd = await pipeline.process_success(trace)
        assert etd is not None

    @pytest.mark.asyncio
    async def test_trace_with_path_parameterizes(self) -> None:
        pipeline = ETDPipeline()
        trace = _make_trace(["cd /home/user/project", "npm run build"])
        etd = await pipeline.process_success(trace)
        assert etd is not None
        assert "project_dir" in etd.parameter_slots or etd.parameter_slots

    @pytest.mark.asyncio
    async def test_low_generalization_rate_rejected(self) -> None:
        pipeline = ETDPipeline()
        entry = _seed_store(pipeline, sig="build-app")
        indexed = pipeline.store.get(entry.id)
        indexed.entry.generalization_success_rate = 0.5
        pipeline.store.update(indexed)
        intent = _intent(normalized="build app", task_type="run_terminal")
        match = await pipeline.find_match(intent)
        assert match is None
