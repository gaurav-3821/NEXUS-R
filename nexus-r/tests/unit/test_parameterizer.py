from __future__ import annotations

import re

from uuid import uuid4

import pytest

from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep
from modules.workflow_engine.src.parameterizer import (
    ETDEntry,
    WorkflowParameterizer,
)


def _make_wf(actions: list[str], slots: list[str] | None = None,
             invariants: list[str] | None = None, sig: str = "test") -> DistilledWorkflow:
    return DistilledWorkflow(
        id=str(uuid4()),
        intent_signature=sig,
        tool_sequence=[ToolStep(tool="terminal", action=a, verify="passed") for a in actions],
        parameter_slots=slots or [],
        invariant_checks=invariants or [],
        success_count=1,
        failure_count=0,
        generalization_success_rate=1.0,
    )


def _actions(entry: ETDEntry) -> list[str]:
    return [s.action for s in entry.tool_sequence]


class TestWorkflowParameterizer:
    def test_simple_path_parameterization(self) -> None:
        wf = _make_wf(["cd /home/user/project-a", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{project_dir}" in actions[0], f"got {actions[0]}"
        assert actions[1] == "npm run build"
        assert "project_dir" in entry.input_schema, f"got {entry.input_schema}"
        assert entry.input_schema["project_dir"] == "string"
        assert entry.parameter_slots

    def test_url_parameterization(self) -> None:
        wf = _make_wf(["curl https://myapp.vercel.app"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{deploy_url}" in actions[0], f"got {actions[0]}"
        assert "deploy_url" in entry.input_schema
        assert "deploy_url" in entry.output_schema

    def test_multiple_parameters(self) -> None:
        wf = _make_wf(["cd /home/user/project-a", "export MY_KEY=secret123", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{project_dir}" in actions[0], f"got {actions[0]}"
        assert "{env_vars}" in actions[1], f"got {actions[1]}"
        assert "project_dir" in entry.input_schema
        assert "env_vars" in entry.input_schema

    def test_no_parameters_fixed_workflow(self) -> None:
        wf = _make_wf(["npm run build", "vercel deploy"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert actions[0] == "npm run build"
        assert actions[1] == "vercel deploy"
        assert not entry.parameter_slots

    def test_output_schema_from_url(self) -> None:
        wf = _make_wf(["curl https://myapp.vercel.app"])
        entry = WorkflowParameterizer().parameterize(wf)
        assert entry.output_schema.get("deploy_url") == "string", f"got {entry.output_schema}"
        assert entry.output_schema.get("status") == "enum", f"got {entry.output_schema}"

    def test_intent_signature_kebab_case(self) -> None:
        wf = _make_wf(["npm run build"], sig="Deploy my Next.js app to Vercel")
        entry = WorkflowParameterizer().parameterize(wf)
        assert entry.intent_signature == "deploy-my-next-js-app-to-vercel", \
            f"got {entry.intent_signature}"

    def test_repo_url_detected(self) -> None:
        wf = _make_wf(["git clone https://github.com/user/my-repo.git"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{repo_url}" in actions[0], f"got {actions[0]}"
        assert "repo_url" in entry.input_schema

    def test_version_numbers_left_untouched(self) -> None:
        wf = _make_wf(["node --version", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert actions[0] == "node --version"
        assert actions[1] == "npm run build"

    def test_etd_entry_has_all_fields(self) -> None:
        wf = _make_wf(["cd /home/user/proj", "npm run build"],
                       invariants=["Node available"])
        entry = WorkflowParameterizer().parameterize(wf)
        assert entry.id.startswith("etd_")
        assert len(entry.intent_embedding) == 128
        assert all(isinstance(v, float) for v in entry.intent_embedding)
        assert entry.invariant_checks == ["Node available"]
        assert entry.success_count == 1
        assert entry.failure_count == 0
        assert entry.generalization_success_rate == 1.0
        assert isinstance(entry.last_validated, str)

    def test_embedding_deterministic(self) -> None:
        wf = _make_wf(["npm run build"], sig="same-signature")
        e1 = WorkflowParameterizer().parameterize(wf)
        e2 = WorkflowParameterizer().parameterize(wf)
        assert e1.intent_embedding == e2.intent_embedding

    def test_file_path_extension_detected(self) -> None:
        wf = _make_wf(["cat /home/user/data.json", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{file_path}" in actions[0], f"got {actions[0]}"

    def test_github_url_parameterized(self) -> None:
        wf = _make_wf(["git clone https://github.com/owner/project.git"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{repo_url}" in actions[0], f"got {actions[0]}"

    def test_env_var_replaced_with_map_type(self) -> None:
        wf = _make_wf(["export DATABASE_URL=postgres://localhost:5432/db"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{env_vars}" in actions[0], f"got {actions[0]}"
        assert entry.input_schema.get("env_vars") == "map"

    def test_api_url_detected(self) -> None:
        wf = _make_wf(["curl https://api.example.com/v1/users"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{api_url}" in actions[0], f"got {actions[0]}"

    def test_system_path_not_parameterized(self) -> None:
        wf = _make_wf(["ls /usr/bin/", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{project_dir}" not in actions[0]

    def test_empty_signature_falls_back(self) -> None:
        wf = _make_wf(["npm run build"], sig="")
        entry = WorkflowParameterizer().parameterize(wf)
        assert entry.intent_signature == "untitled-workflow", f"got {entry.intent_signature}"

    def test_output_schema_includes_status_with_deploy_url(self) -> None:
        wf = _make_wf(["curl https://myapp.vercel.app/api/health"])
        entry = WorkflowParameterizer().parameterize(wf)
        assert "deploy_url" in entry.output_schema
        assert "status" in entry.output_schema

    def test_file_extension_path_detected(self) -> None:
        wf = _make_wf(["python /home/user/script.py", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{file_path}" in actions[0], f"got {actions[0]}"

    def test_config_json_path(self) -> None:
        wf = _make_wf(["cat /home/user/config.json", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{file_path}" in actions[0], f"got {actions[0]}"

    def test_md_file_path(self) -> None:
        wf = _make_wf(["cat /home/user/README.md"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{file_path}" in actions[0], f"got {actions[0]}"

    def test_generic_url_default_to_url_slot(self) -> None:
        wf = _make_wf(["curl https://example.com/data"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{url}" in actions[0], f"got {actions[0]}"

    def test_unknown_file_extension_path(self) -> None:
        wf = _make_wf(["cat /home/user/data.bin"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert "{file_path}" in actions[0], f"got {actions[0]}"

    def test_version_check_function(self) -> None:
        wf = _make_wf(["python --version", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert actions[0] == "python --version"

    def test_dedup_param_counters_init(self) -> None:
        p = WorkflowParameterizer()
        counters: dict[str, int] = {}
        name = p._dedup_name("project_dir", counters)
        assert name == "project_dir"
        assert counters["project_dir"] == 0

    def test_duplicate_bare_path_single_slash(self) -> None:
        wf = _make_wf(["ls /", "npm run build"])
        entry = WorkflowParameterizer().parameterize(wf)
        actions = _actions(entry)
        assert actions[0] == "ls /"
