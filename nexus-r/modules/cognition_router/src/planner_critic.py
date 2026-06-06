from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("nexus-r.planner_critic")

PLANNER_SYSTEM_PROMPT = """You are a Task Planner. Output ONLY valid JSON. No other text.

Available tools: browser.goto(url), browser.click(selector), browser.type_text(selector,text), browser.wait_for_element(selector), browser.extract_text(), browser.evaluate(js_code), browser.screenshot(), search_web(query), calculator.evaluate(expression)

JSON format:
{"plan":{"goal":"...","steps":[{"step":1,"action":"...","tool":"...","reasoning":"...","expected_outcome":"..."}],"fallback_strategy":"...","estimated_complexity":"low|medium|high"},"requires_browser":true|false,"security_notes":"..."}

Examples:
- "amazon iPhone price" -> {"plan":{"goal":"Find iPhone 15 price on Amazon","steps":[{"step":1,"action":"Navigate to amazon.com","tool":"browser.goto","reasoning":"Start at the homepage","expected_outcome":"Amazon homepage loaded"},{"step":2,"action":"Search for iPhone 15","tool":"browser.type_text","reasoning":"Find product","expected_outcome":"Search results shown"},{"step":3,"action":"Extract price from results","tool":"browser.extract_text","reasoning":"Read the price","expected_outcome":"Price displayed"}],"fallback_strategy":"Retry search with different query","estimated_complexity":"low"},"requires_browser":true,"security_notes":"Public product lookup, no credentials needed"}
- "weather Tokyo" -> {"plan":{"goal":"Get current weather in Tokyo","steps":[{"step":1,"action":"Search web for Tokyo weather","tool":"search_web","reasoning":"Get real-time weather data","expected_outcome":"Weather forecast displayed"}],"fallback_strategy":"Try alternative search terms","estimated_complexity":"low"},"requires_browser":false,"security_notes":"none"}
"""

CRITIC_SYSTEM_PROMPT = """You are a Plan Reviewer (Critic) for an AI agent system.

Your job is to review execution plans for logical flaws, missing edge cases, security risks, and efficiency.

Review the plan against these criteria:
1. **Completeness**: Does the plan cover all necessary steps to achieve the goal?
2. **Logical Flow**: Are the steps in the correct order? Are there gaps?
3. **Edge Cases**: Does the plan handle common failure scenarios?
4. **Security**: Does the plan expose credentials, PII, or perform unsafe actions?
5. **Efficiency**: Is there a simpler way to achieve the same result?
6. **Tool Selection**: Are the right tools chosen for each step?

Output a strict JSON response:
{
    "approved": true or false,
    "issues": [
        {"severity": "critical|major|minor", "description": "what's wrong", "step": 1}
    ],
    "revised_plan": { ... } or null if approved,
    "critic_notes": "Summary of the review"
}

If approved, set "approved": true and "revised_plan": null.
If rejected or needs revision, set "approved": false and provide the revised_plan.
"""


@dataclass
class ExecutionPlan:
    goal: str = ""
    steps: list[dict] = field(default_factory=list)
    fallback_strategy: str = ""
    estimated_complexity: str = "medium"
    requires_browser: bool = False
    security_notes: str = ""


@dataclass
class PlanReview:
    approved: bool = False
    issues: list[dict] = field(default_factory=list)
    revised_plan: ExecutionPlan | None = None
    critic_notes: str = ""


class PlannerSkill:
    """Generates step-by-step execution plans for complex tasks."""

    def __init__(
        self,
        model: str = "deepseek-r1:8b",
        ollama_base: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
    ):
        self.model = model
        self.ollama_base = ollama_base.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def plan(self, query: str, context: str = "") -> ExecutionPlan | None:
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a step-by-step execution plan for this request.\n\nUser Request: {query}\n\nAdditional Context:\n{context}" if context else f"Create a step-by-step execution plan for this request.\n\nUser Request: {query}"},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 4096},
        }

        try:
            resp = await self.client.post(
                f"{self.ollama_base}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message") or {}
            raw = msg.get("content", "") or ""
            if not raw.strip():
                raw = msg.get("thinking", "") or ""
            return self._parse_plan(raw)
        except Exception as exc:
            logger.warning("Planner model query failed: %s", exc)
            return None

    def _parse_plan(self, raw: str) -> ExecutionPlan | None:
        json_data = self._extract_json(raw)
        if not json_data:
            return None

        plan_data = json_data.get("plan", json_data)
        steps = plan_data.get("steps", [])
        if not steps:
            return None

        return ExecutionPlan(
            goal=plan_data.get("goal", ""),
            steps=steps,
            fallback_strategy=plan_data.get("fallback_strategy", ""),
            estimated_complexity=plan_data.get("estimated_complexity", "medium"),
            requires_browser=json_data.get("requires_browser", False),
            security_notes=json_data.get("security_notes", ""),
        )

    def format_for_prompt(self, plan: ExecutionPlan) -> str:
        lines = [
            "<EXECUTION_PLAN>",
            f"Goal: {plan.goal}",
            f"Complexity: {plan.estimated_complexity}",
            f"Requires Browser: {plan.requires_browser}",
            "",
            "Steps:",
        ]
        for step in plan.steps:
            lines.append(f"  Step {step.get('step', '?')}: {step.get('action', step.get('description', ''))}")
            if step.get("tool"):
                lines.append(f"    Tool: {step['tool']}")
            if step.get("reasoning"):
                lines.append(f"    Why: {step['reasoning']}")
            if step.get("expected_outcome"):
                lines.append(f"    Expected: {step['expected_outcome']}")
        if plan.fallback_strategy:
            lines.append(f"Fallback: {plan.fallback_strategy}")
        if plan.security_notes:
            lines.append(f"Security: {plan.security_notes}")
        lines.append("</EXECUTION_PLAN>")
        return "\n".join(lines)

    def _extract_json(self, raw: str) -> dict | None:
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        for end in range(start, len(raw)):
            if raw[end] == "{":
                depth += 1
            elif raw[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:end+1])
                    except json.JSONDecodeError:
                        return None
        return None


class CriticSkill:
    """Reviews execution plans for flaws, edge cases, and security risks."""

    def __init__(
        self,
        model: str = "deepseek-r1:8b",
        ollama_base: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
    ):
        self.model = model
        self.ollama_base = ollama_base.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def review(self, plan: ExecutionPlan, query: str) -> PlanReview:
        plan_str = json.dumps({
            "goal": plan.goal,
            "steps": plan.steps,
            "fallback_strategy": plan.fallback_strategy,
            "estimated_complexity": plan.estimated_complexity,
            "requires_browser": plan.requires_browser,
            "security_notes": plan.security_notes,
        }, indent=2)

        messages = [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this execution plan for the query: '{query}'\n\nPlan:\n{plan_str}"},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 1024},
        }

        try:
            resp = await self.client.post(
                f"{self.ollama_base}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message") or {}
            raw = msg.get("content", "") or ""
            if not raw.strip():
                raw = msg.get("thinking", "") or ""
            return self._parse_review(raw, plan)
        except Exception as exc:
            logger.warning("Critic model query failed: %s", exc)
            return PlanReview(
                approved=True,
                critic_notes=f"Critic unavailable ({exc}), plan approved by default",
            )

    def _parse_review(self, raw: str, original_plan: ExecutionPlan) -> PlanReview:
        json_data = self._extract_json(raw)
        if not json_data:
            return PlanReview(
                approved=True,
                critic_notes="Could not parse critic response, approved by default",
            )

        approved = json_data.get("approved", True)
        issues = json_data.get("issues", [])

        revised_plan = None
        if not approved and json_data.get("revised_plan"):
            rp = json_data["revised_plan"].get("plan", json_data["revised_plan"])
            steps = rp.get("steps", [])
            if steps:
                revised_plan = ExecutionPlan(
                    goal=rp.get("goal", original_plan.goal),
                    steps=steps,
                    fallback_strategy=rp.get("fallback_strategy", original_plan.fallback_strategy),
                    estimated_complexity=rp.get("estimated_complexity", original_plan.estimated_complexity),
                    requires_browser=json_data["revised_plan"].get("requires_browser", original_plan.requires_browser),
                    security_notes=json_data["revised_plan"].get("security_notes", original_plan.security_notes),
                )

        return PlanReview(
            approved=approved,
            issues=issues,
            revised_plan=revised_plan,
            critic_notes=json_data.get("critic_notes", ""),
        )

    def _extract_json(self, raw: str) -> dict | None:
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        for end in range(start, len(raw)):
            if raw[end] == "{":
                depth += 1
            elif raw[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:end+1])
                    except json.JSONDecodeError:
                        return None
        return None
