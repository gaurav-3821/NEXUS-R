from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Sequence

from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep


@dataclass
class ETDEntry:
    id: str
    intent_signature: str
    intent_embedding: list[float]
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    tool_sequence: list[ToolStep]
    parameter_slots: list[str]
    invariant_checks: list[str]
    success_count: int
    failure_count: int
    generalization_success_rate: float
    last_validated: str
    avg_cost: float = 0.0
    avg_latency_ms: float = 0.0


URL_PATTERN = re.compile(r"https?://[^\s'\"]+")
PATH_PATTERN = re.compile(r"(?:/[a-zA-Z0-9._\-\~]+)+(?:/[a-zA-Z0-9._\-\~]+)*")
ENV_VAR_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)=(?:[^\s'\"]+)")
VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+|\b\d+\.\d+\b")
REPO_URL_PATTERN = re.compile(r"github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+")

COMMON_SYSTEM_DIRS = {"bin", "lib", "usr", "etc", "var", "opt", "tmp",
                      "dev", "proc", "sys", "mnt", "media", "sbin",
                      "root", "home", "Users", "Documents", "Desktop",
                      "Downloads", "AppData", "Local", "Roaming",
                      "Program Files", "ProgramData", "System32",
                      "Windows", "System", "config", "cache", "log",
                      "run", "share", "local", "src", "node_modules"}


class WorkflowParameterizer:
    def parameterize(self, workflow: DistilledWorkflow, cost: float = 0.0, latency_ms: float = 0.0) -> ETDEntry:
        new_steps: list[ToolStep] = []
        input_schema: dict[str, str] = {}
        output_schema: dict[str, str] = {}
        seen_params: set[str] = set()
        input_counters: dict[str, int] = {}
        output_counters: dict[str, int] = {}

        for step in workflow.tool_sequence:
            action = step.action
            updated = action
            step_inputs: dict[str, str] = {}
            step_outputs: dict[str, str] = {}

            urls = URL_PATTERN.findall(action)
            for url in urls:
                slot = self._url_to_slot(url)
                param_name = self._dedup_name(slot, input_counters)
                updated = updated.replace(url, f"{{{param_name}}}", 1)
                if param_name not in seen_params:
                    step_inputs[param_name] = "string"

            env_vars = ENV_VAR_PATTERN.findall(action)
            for env_match in env_vars:
                env_name = env_match
                param_name = "env_vars"
                updated = updated.replace(f"{env_name}=...", f"{{{param_name}}}", 1)
                updated = re.sub(re.escape(f"{env_name}=") + r"[^\s'\"]+",
                                 f"{{{param_name}}}", updated, count=1)
                if param_name not in seen_params:
                    step_inputs[param_name] = "map"

            updated = self._parameterize_paths(updated, step_inputs, seen_params)

            param_slots_in_action = re.findall(r"\{(\w+)\}", updated)
            new_steps.append(ToolStep(
                tool=step.tool,
                action=updated,
                verify=step.verify,
                is_essential=step.is_essential,
            ))
            for p in param_slots_in_action:
                seen_params.add(p)

            for k, v in step_inputs.items():
                if k not in input_schema:
                    input_schema[k] = v

        url_params_in_output = [s for s in seen_params if s in {"deploy_url", "url", "api_url"}]
        if url_params_in_output:
            for p in url_params_in_output:
                output_schema.setdefault(p, "string")
            output_schema.setdefault("status", "enum")

        all_slots = sorted(seen_params)
        sig = self._derive_intent_signature(workflow.intent_signature)
        entry_id = "etd_" + hashlib.sha256(sig.encode()).hexdigest()[:12]
        embedding = self._compute_embedding(sig)

        return ETDEntry(
            id=entry_id,
            intent_signature=sig,
            intent_embedding=embedding,
            input_schema=input_schema,
            output_schema=output_schema,
            tool_sequence=new_steps,
            parameter_slots=all_slots,
            invariant_checks=workflow.invariant_checks,
            success_count=workflow.success_count,
            failure_count=workflow.failure_count,
            generalization_success_rate=workflow.generalization_success_rate,
            last_validated=datetime.now(timezone.utc).isoformat(),
            avg_cost=cost,
            avg_latency_ms=latency_ms,
        )

    def _parameterize_paths(self, action: str, step_inputs: dict[str, str],
                            seen_params: set[str]) -> str:
        matches = list(PATH_PATTERN.finditer(action))
        for m in reversed(matches):
            path = m.group(0)
            if self._is_system_path(path):
                continue
            if not path.startswith("/"):
                continue
            slot = self._path_to_slot(path)
            if slot is None:
                continue
            if slot not in seen_params:
                step_inputs.setdefault(slot, "string")
            action = action[:m.start()] + f"{{{slot}}}" + action[m.end():]
        return action

    def _path_to_slot(self, path: str) -> str | None:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return None
        non_system = [p for p in parts if p not in COMMON_SYSTEM_DIRS]
        if not non_system:
            return None
        last = non_system[-1]
        if "." in last:
            ext = last.rsplit(".", 1)[-1].lower()
            if ext in {"py", "js", "ts", "json", "md", "txt", "html", "css"}:
                return "file_path"
            return "file_path"
        if re.match(r"^[a-z]+-\d+$", last, re.IGNORECASE) or \
           re.match(r"^[a-z]+[-_][a-z0-9]+$", last, re.IGNORECASE):
            return "project_dir"
        return "project_dir"

    def _is_system_path(self, path: str) -> bool:
        parts = [p for p in path.strip("/").split("/") if p]
        return all(p in COMMON_SYSTEM_DIRS for p in parts)

    def _url_to_slot(self, url: str) -> str:
        if "github.com" in url:
            return "repo_url"
        if "vercel.app" in url or "netlify.app" in url:
            return "deploy_url"
        if "api" in url.lower():
            return "api_url"
        return "url"

    def _is_version_check(self, action: str) -> bool:
        return bool(re.search(r"(node|npm|vercel|python|git|docker|java)\s+(--version|-v\b)",
                              action, re.IGNORECASE))

    def _dedup_name(self, name: str, counters: dict[str, int]) -> str:
        if name not in counters:
            counters[name] = 0
            return name
        counters[name] += 1
        return f"{name}_{counters[name]}"

    def _derive_intent_signature(self, existing_sig: str) -> str:
        sig = existing_sig.strip().lower()
        sig = re.sub(r"[^a-z0-9]+", "-", sig)
        sig = sig.strip("-")
        return sig if sig else "untitled-workflow"

    def _compute_embedding(self, sig: str) -> list[float]:
        h = hashlib.sha256(sig.encode()).hexdigest()
        seed = int(h[:8], 16)
        rng = _SimpleRNG(seed)
        return [rng.next() for _ in range(128)]


class _SimpleRNG:
    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next(self) -> float:
        self._state = (self._state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._state >> 16) / 65536.0 * 2.0 - 1.0
