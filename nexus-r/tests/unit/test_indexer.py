from __future__ import annotations

from uuid import uuid4
import pytest

from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep
from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
from modules.workflow_engine.src.store import ETDStore
from modules.workflow_engine.src.indexer import ETDIndexer


def _wf(actions: list[str], sig: str = "test") -> DistilledWorkflow:
    return DistilledWorkflow(
        id=str(uuid4()),
        intent_signature=sig,
        tool_sequence=[ToolStep(tool="terminal", action=a, verify="passed") for a in actions],
        parameter_slots=[],
        invariant_checks=[],
        success_count=1,
        failure_count=0,
        generalization_success_rate=1.0,
    )


class TestETDIndexer:
    def test_index_creates_indexed_entry(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        indexed = idx.index(entry)
        assert indexed.entry.id == entry.id
        assert indexed.verification_status == "passed"
        assert indexed.latency_ms == 0.0
        assert indexed.ttl_days == 30
        assert indexed.hit_count == 0
        assert indexed.invalidated is False
        assert indexed.created_at

    def test_index_latency_stored(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        indexed = idx.index(entry, latency_ms=42.5)
        assert indexed.latency_ms == 42.5

    def test_index_adds_to_store(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        idx.index(entry)
        assert store.get(entry.id) is not None

    def test_verification_failed_when_failure_count_positive(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        wf = _wf(["npm run build"])
        wf.failure_count = 2
        entry = WorkflowParameterizer().parameterize(wf)
        indexed = idx.index(entry)
        assert indexed.verification_status == "failed"

    def test_tags_from_intent_signature(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"], sig="deploy the app to production"))
        indexed = idx.index(entry)
        assert "deploy" in indexed.tags
        assert "the" not in indexed.tags
        assert "to" not in indexed.tags
        assert "app" in indexed.tags
        assert "production" in indexed.tags

    def test_tags_include_tool_names(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        indexed = idx.index(entry)
        assert "terminal" in indexed.tags

    def test_tags_include_has_params(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["cd /home/user/project"]))
        indexed = idx.index(entry)
        assert "has-params" in indexed.tags

    def test_tags_deduplicate(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build", "npm run test"], sig="build test test"))
        indexed = idx.index(entry)
        assert indexed.tags == indexed.tags
        assert len(indexed.tags) == len(set(indexed.tags))

    def test_tags_always_include_etd(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        indexed = idx.index(entry)
        assert "etd" in indexed.tags

    def test_no_params_no_has_params_tag(self) -> None:
        store = ETDStore()
        idx = ETDIndexer(store)
        entry = WorkflowParameterizer().parameterize(_wf(["npm run build"]))
        indexed = idx.index(entry)
        assert "has-params" not in indexed.tags
