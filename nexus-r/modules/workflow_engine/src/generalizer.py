from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep


@dataclass
class TaskVariant:
    name: str
    parameters: dict[str, str]
    environment: dict[str, str]
    expected_success: bool = True


@dataclass
class GeneralizationResult:
    success_rate: float
    tested_variants: int
    passed_variants: int
    failure_cases: list[str]
    admitted: bool


TOOL_ENV_MAP: dict[str, str] = {
    "node": "node_version",
    "npm": "node_version",
    "vercel": "vercel_version",
    "python": "python_version",
    "git": "git_version",
    "docker": "docker_version",
    "java": "java_version",
}


class GeneralizationVerifier:
    def verify(
        self,
        workflow: DistilledWorkflow,
        test_variants: Sequence[TaskVariant],
    ) -> GeneralizationResult:
        passed = 0
        failures: list[str] = []
        for variant in test_variants:
            inv_fails = self._check_invariants(workflow.invariant_checks, variant.environment)
            if inv_fails:
                failures.append(f"{variant.name}: {inv_fails[0]}")
                continue
            param_fails = self._check_parameters(workflow.parameter_slots, variant.parameters)
            if param_fails:
                failures.append(f"{variant.name}: {param_fails[0]}")
                continue
            step_fails = self._simulate_steps(workflow.tool_sequence, variant.parameters, variant.environment)
            if step_fails:
                failures.append(f"{variant.name}: {step_fails[0]}")
                continue
            passed += 1
        total = len(test_variants)
        rate = passed / total if total > 0 else 0.0
        admitted = rate >= 0.90
        return GeneralizationResult(
            success_rate=rate,
            tested_variants=total,
            passed_variants=passed,
            failure_cases=failures,
            admitted=admitted,
        )

    def _check_invariants(
        self, invariants: list[str], env: dict[str, str]
    ) -> list[str]:
        failures: list[str] = []
        for inv in invariants:
            m = re.match(r"(\w+)\s+available", inv, re.IGNORECASE)
            if m:
                tool = m.group(1).lower()
                env_key = TOOL_ENV_MAP.get(tool, f"{tool}_version")
                raw = env.get(env_key) or env.get(tool)
                if raw is None:
                    failures.append(
                        f"Invariant '{inv}' violated: {tool} not available "
                        f"(env keys: {list(env.keys())})"
                    )
                else:
                    version = self._extract_version(raw)
                    expected_min = self._extract_version(inv)
                    if expected_min is not None and version is not None and version < expected_min:
                        failures.append(
                            f"Invariant '{inv}' violated: {tool} version {version} < "
                            f"required {expected_min}"
                        )
            m_ver = re.match(r"(\w+)\s*(>=|<=|>|<|=)\s*([\d.]+)", inv, re.IGNORECASE)
            if m_ver:
                tool = m_ver.group(1).lower()
                op = m_ver.group(2)
                required = float(m_ver.group(3))
                env_key = TOOL_ENV_MAP.get(tool, f"{tool}_version")
                raw = env.get(env_key) or env.get(tool)
                if raw is None:
                    failures.append(
                        f"Invariant '{inv}' violated: {tool} not available"
                    )
                else:
                    version = self._extract_version(raw)
                    if version is None:
                        failures.append(
                            f"Invariant '{inv}' violated: could not parse version "
                            f"'{raw}' for {tool}"
                        )
                    elif not self._compare_versions(version, op, required):
                        failures.append(
                            f"Invariant '{inv}' violated: {tool} version {version} "
                            f"does not satisfy {op} {required}"
                        )
        return failures

    def _check_parameters(
        self, slots: list[str], params: dict[str, str]
    ) -> list[str]:
        for slot in slots:
            if slot not in params:
                return [f"Missing required parameter '{slot}' (slots={slots}, provided={list(params.keys())})"]
            if not params[slot]:
                return [f"Parameter '{slot}' is empty"]
        return []

    def _simulate_steps(
        self,
        steps: Sequence[ToolStep],
        params: dict[str, str],
        env: dict[str, str],
    ) -> list[str]:
        for step in steps:
            action = step.action.lower()
            if action.startswith("npm") or action.startswith("node"):
                if "node_version" not in env and "node" not in env:
                    return [f"Step '{step.action}' requires Node.js (not in env)"]
            elif action.startswith("pip") or action.startswith("python"):
                if "python_version" not in env and "python" not in env:
                    return [f"Step '{step.action}' requires Python (not in env)"]
            elif action.startswith("vercel"):
                if "vercel_version" not in env and "vercel" not in env:
                    return [f"Step '{step.action}' requires Vercel CLI (not in env)"]
            elif action.startswith("git"):
                if "git_version" not in env and "git" not in env:
                    return [f"Step '{step.action}' requires Git (not in env)"]
            elif action.startswith("cd") or action.startswith("mkdir"):
                for slot_name, slot_val in params.items():
                    if slot_val and slot_name not in action:
                        continue
            elif action.startswith("curl"):
                continue
        return []

    def _extract_version(self, text: str) -> float | None:
        m = re.search(r"(\d+)(?:\.(\d+))?", text)
        if m:
            major = int(m.group(1))
            minor = int(m.group(2)) if m.group(2) else 0
            return float(f"{major}.{minor}")
        return None

    def _compare_versions(self, version: float, op: str, required: float) -> bool:
        if op == ">=":
            return version >= required
        if op == "<=":
            return version <= required
        if op == ">":
            return version > required
        if op == "<":
            return version < required
        if op == "=":
            return abs(version - required) < 0.01
        return False
