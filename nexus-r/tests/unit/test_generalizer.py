from __future__ import annotations

from uuid import uuid4

import pytest

from modules.workflow_engine.src.distiller import (
    DistilledWorkflow,
    ToolStep,
)
from modules.workflow_engine.src.generalizer import (
    GeneralizationVerifier,
    GeneralizationResult,
    TaskVariant,
)


def _make_workflow(
    tool_actions: list[str],
    param_slots: list[str] | None = None,
    invariants: list[str] | None = None,
) -> DistilledWorkflow:
    return DistilledWorkflow(
        id=str(uuid4()),
        intent_signature="-".join(tool_actions),
        tool_sequence=[
            ToolStep(tool="terminal", action=a, verify="passed")
            for a in tool_actions
        ],
        parameter_slots=param_slots or [],
        invariant_checks=invariants or [],
        success_count=1,
        failure_count=0,
        generalization_success_rate=0.0,
    )


class TestGeneralizationVerifier:
    def test_high_success_rate_admitted(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build", "vercel deploy"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="v1",
                parameters={},
                environment={"node_version": "18.17.0", "vercel_version": "34.0.0"},
                expected_success=True,
            ),
            TaskVariant(
                name="v2",
                parameters={},
                environment={"node_version": "20.0.0", "vercel_version": "34.0.0"},
                expected_success=True,
            ),
            TaskVariant(
                name="v3",
                parameters={},
                environment={"node_version": "18.17.0", "vercel_version": "35.0.0"},
                expected_success=True,
            ),
            TaskVariant(
                name="v4",
                parameters={},
                environment={"node_version": "22.0.0", "vercel_version": "33.0.0"},
                expected_success=True,
            ),
            TaskVariant(
                name="v5",
                parameters={},
                environment={"node_version": "18.17.0", "vercel_version": "34.0.0"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.success_rate == 1.0, f"got {result.success_rate}"
        assert result.passed_variants == 5
        assert result.tested_variants == 5
        assert result.admitted is True
        assert result.failure_cases == []

    def test_borderline_not_admitted(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="pass1", parameters={}, environment={"node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="pass2", parameters={}, environment={"node_version": "20"},
                expected_success=True,
            ),
            TaskVariant(
                name="pass3", parameters={}, environment={"node_version": "22"},
                expected_success=True,
            ),
            TaskVariant(
                name="pass4", parameters={}, environment={"node_version": "19"},
                expected_success=True,
            ),
            TaskVariant(
                name="fail1", parameters={}, environment={},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.success_rate == 0.8, f"got {result.success_rate}"
        assert result.passed_variants == 4
        assert result.tested_variants == 5
        assert result.admitted is False
        assert len(result.failure_cases) == 1

    def test_exact_threshold_nine_of_ten_admitted(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name=f"pass{i}", parameters={}, environment={"node_version": "20"},
                expected_success=True,
            )
            for i in range(9)
        ] + [
            TaskVariant(
                name="fail1", parameters={}, environment={},
                expected_success=False,
            )
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.success_rate == 0.9, f"got {result.success_rate}"
        assert result.passed_variants == 9
        assert result.tested_variants == 10
        assert result.admitted is True
        assert len(result.failure_cases) == 1

    def test_invariant_violation_version_too_low(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build"],
            invariants=["node >= 18"],
        )
        variants = [
            TaskVariant(
                name="low_node",
                parameters={},
                environment={"node_version": "14.0.0"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 0
        assert result.tested_variants == 1
        assert result.admitted is False
        assert len(result.failure_cases) >= 1
        fail_msg = result.failure_cases[0]
        assert "14" in fail_msg, f"missing version in: {fail_msg}"
        assert "node" in fail_msg.lower(), f"missing tool in: {fail_msg}"

    def test_parameter_substitution_failure(self) -> None:
        wf = _make_workflow(
            ["cd {project_dir}", "npm run build"],
            param_slots=["project_dir"],
        )
        variants = [
            TaskVariant(
                name="missing_param",
                parameters={},
                environment={"node_version": "18"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 0
        assert result.tested_variants == 1
        assert result.admitted is False
        assert len(result.failure_cases) >= 1
        assert "project_dir" in result.failure_cases[0]

    def test_all_variants_identical_admitted(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="same1",
                parameters={},
                environment={"node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="same2",
                parameters={},
                environment={"node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="same3",
                parameters={},
                environment={"node_version": "18"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.success_rate == 1.0
        assert result.passed_variants == 3
        assert result.admitted is True
        assert result.failure_cases == []

    def test_empty_variants(self) -> None:
        wf = _make_workflow(["npm run build"])
        result = GeneralizationVerifier().verify(wf, [])
        assert result.success_rate == 0.0
        assert result.tested_variants == 0
        assert result.passed_variants == 0
        assert result.admitted is False

    def test_invariant_version_comparison_operators(self) -> None:
        wf = _make_workflow(
            ["npm install"],
            invariants=["node <= 20"],
        )
        variants = [
            TaskVariant(
                name="high_ver",
                parameters={},
                environment={"node_version": "22"},
                expected_success=False,
            ),
            TaskVariant(
                name="low_ver",
                parameters={},
                environment={"node_version": "18"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert result.admitted is False
        assert "high_ver" in result.failure_cases[0]

    def test_invariant_strict_greater_and_less(self) -> None:
        wf = _make_workflow(
            ["npm install"],
            invariants=["node > 18"],
        )
        variants = [
            TaskVariant(
                name="exact_18",
                parameters={},
                environment={"node_version": "18"},
                expected_success=False,
            ),
            TaskVariant(
                name="above_18",
                parameters={},
                environment={"node_version": "19"},
                expected_success=True,
            ),
            TaskVariant(
                name="below_18",
                parameters={},
                environment={"node_version": "17"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert result.tested_variants == 3

    def test_invariant_equal_operator(self) -> None:
        wf = _make_workflow(
            ["npm install"],
            invariants=["node = 18"],
        )
        variants = [
            TaskVariant(
                name="match",
                parameters={},
                environment={"node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="mismatch",
                parameters={},
                environment={"node_version": "20"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1

    def test_empty_parameter_value_rejected(self) -> None:
        wf = _make_workflow(
            ["cd {project_dir}"],
            param_slots=["project_dir"],
        )
        variants = [
            TaskVariant(
                name="empty_val",
                parameters={"project_dir": ""},
                environment={"node_version": "18"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 0
        assert "empty" in result.failure_cases[0].lower()

    def test_python_step_simulated(self) -> None:
        wf = _make_workflow(
            ["pip install -r requirements.txt", "python run.py"],
            invariants=["Python available"],
        )
        variants = [
            TaskVariant(
                name="has_python",
                parameters={},
                environment={"python_version": "3.10"},
                expected_success=True,
            ),
            TaskVariant(
                name="no_python",
                parameters={},
                environment={},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert "no_python" in result.failure_cases[0]

    def test_git_and_directory_steps(self) -> None:
        wf = _make_workflow(
            ["git clone {repo_url}", "cd project", "npm install"],
            param_slots=["repo_url"],
            invariants=["Git available", "Node available"],
        )
        variants = [
            TaskVariant(
                name="full_env",
                parameters={"repo_url": "https://github.com/user/repo.git"},
                environment={"git_version": "2.40", "node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="no_git",
                parameters={"repo_url": "https://github.com/user/repo.git"},
                environment={"node_version": "18"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert "no_git" in result.failure_cases[0]

    def test_verify_90_percent_exact_boundary(self) -> None:
        wf = _make_workflow(
            ["npm run build"],
            invariants=["Node available"],
        )
        nine_pass = [
            TaskVariant(
                name=f"p{i}", parameters={}, environment={"node_version": "18"},
                expected_success=True,
            )
            for i in range(9)
        ]
        one_fail = [
            TaskVariant(
                name="f1", parameters={}, environment={},
                expected_success=False,
            )
        ]
        result = GeneralizationVerifier().verify(wf, nine_pass + one_fail)
        assert result.success_rate == 0.9
        assert result.admitted is True

        nine_fail = [
            TaskVariant(
                name=f"f{i}", parameters={}, environment={},
                expected_success=False,
            )
            for i in range(2)
        ]
        result2 = GeneralizationVerifier().verify(wf, nine_pass + nine_fail)
        assert result2.success_rate == pytest.approx(0.818, abs=0.001)
        assert result2.admitted is False

    def test_step_simulation_reached_when_invariant_passes(self) -> None:
        wf = _make_workflow(
            ["npm install", "vercel deploy"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="no_vercel_in_env",
                parameters={},
                environment={"node_version": "20"},
                expected_success=False,
            ),
            TaskVariant(
                name="vercel_and_node",
                parameters={},
                environment={"node_version": "20", "vercel_version": "34"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert result.tested_variants == 2
        assert "no_vercel_in_env" in result.failure_cases[0]
        assert "vercel" in result.failure_cases[0].lower()

    def test_step_simulation_git_missing(self) -> None:
        wf = _make_workflow(
            ["git clone repo", "npm install"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="no_git",
                parameters={},
                environment={"node_version": "20"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 0
        assert "git" in result.failure_cases[0].lower()

    def test_invariant_less_than_operator(self) -> None:
        wf = _make_workflow(["npm install"], invariants=["node < 20"])
        variants = [
            TaskVariant(
                name="too_high", parameters={}, environment={"node_version": "22"},
                expected_success=False,
            ),
            TaskVariant(
                name="ok", parameters={}, environment={"node_version": "18"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert "too_high" in result.failure_cases[0]

    def test_invariant_less_equal_operator(self) -> None:
        wf = _make_workflow(["npm install"], invariants=["node <= 18"])
        variants = [
            TaskVariant(
                name="exact", parameters={}, environment={"node_version": "18"},
                expected_success=True,
            ),
            TaskVariant(
                name="above", parameters={}, environment={"node_version": "20"},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert "above" in result.failure_cases[0]

    def test_cd_mkdir_steps_succeed_with_params(self) -> None:
        wf = _make_workflow(
            ["cd {project_dir}", "mkdir build", "npm run build"],
            param_slots=["project_dir"],
            invariants=["Node available"],
        )
        variants = [
            TaskVariant(
                name="with_path",
                parameters={"project_dir": "/tmp/test-project"},
                environment={"node_version": "20"},
                expected_success=True,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1

    def test_mixed_success_and_failure_reasons_specific(self) -> None:
        wf = _make_workflow(
            ["npm install", "npm run build", "vercel deploy"],
            invariants=["Node available", "Vercel available"],
        )
        variants = [
            TaskVariant(
                name="good",
                parameters={},
                environment={"node_version": "20", "vercel_version": "34"},
                expected_success=True,
            ),
            TaskVariant(
                name="no_vercel",
                parameters={},
                environment={"node_version": "20"},
                expected_success=False,
            ),
            TaskVariant(
                name="no_node",
                parameters={},
                environment={},
                expected_success=False,
            ),
        ]
        result = GeneralizationVerifier().verify(wf, variants)
        assert result.passed_variants == 1
        assert result.tested_variants == 3
        assert result.admitted is False
        assert len(result.failure_cases) == 2
        for msg in result.failure_cases:
            assert msg.startswith("no_vercel:") or msg.startswith("no_node:"), f"unexpected msg: {msg}"
