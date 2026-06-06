from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Literal

import httpx

logger = logging.getLogger("nexus-r.query_router")

ROUTER_SYSTEM_PROMPT = """You are a Query Routing Evaluator for a hybrid AI system.

Your job is to analyze a user query and decide whether it should be handled by a **local lightweight model** or escalated to a **powerful cloud model**.

## Self-Assessment: What the local model CAN do well:
- Short factual Q&A (e.g., "What is the capital of France?")
- Casual conversation, greetings, chitchat
- Simple creative writing (poems, short stories, emails)
- Basic math and logic
- Summarization of provided text
- Translation between languages
- Simple code snippets (less than 50 lines)
- Explaining concepts that don't require real-time data

## What REQUIRES cloud escalation:
- Complex multi-step reasoning or math problem solving
- Tasks requiring browsing the web, real-time data, or current events
- Tasks requiring code execution or file system access
- Long document processing or analysis (>2000 words of output)
- Tasks requiring integration with external APIs
- Queries requiring deep domain expertise (medical, legal, financial analysis)
- Tasks involving browser automation (form filling, navigation)
- Multi-turn tool use or agentic workflows
- Generating structured data in large volumes
- Tasks requiring high factual accuracy where hallucination is unacceptable
- Questions about recent events (last 6 months)

## Output Format
Respond with ONLY a valid JSON object. No other text.

If LOCAL:
{"route": "local", "reason": "Brief explanation of why local can handle this"}

If CLOUD:
{"route": "cloud", "reason": "Brief explanation of why cloud is needed", "required_capabilities": ["list", "of", "needed", "capabilities"]}

Examples:
- Query: "What is 2+2?" -> {"route": "local", "reason": "Simple arithmetic"}
- Query: "Write a poem about AI" -> {"route": "local", "reason": "Creative writing, no external data needed"}
- Query: "Analyze this CSV file and create a forecast" -> {"route": "cloud", "reason": "Requires data analysis and file access", "required_capabilities": ["data_analysis", "file_io", "forecasting"]}
- Query: "Go to amazon.com and find the price of iPhone" -> {"route": "cloud", "reason": "Requires web browsing and multi-step reasoning", "required_capabilities": ["browser_automation", "web_navigation"]}
- Query: "HELLO" -> {"route": "local", "reason": "Simple greeting"}
"""

FALLBACK_ROUTER_PROMPT = """Analyze this query and respond with JSON only:
{"route": "local" or "cloud", "reason": "..."}"""


@dataclass
class RouterResult:
    route: Literal["local", "cloud"]
    reason: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    confidence: float = 1.0
    model_used: str = ""
    raw_response: str = ""


class QueryRouter:
    def __init__(
        self,
        router_model: str = "llama3.2:3b",
        ollama_base: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: float = 300.0,
    ):
        self.router_model = router_model
        self.ollama_base = ollama_base.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, tuple[RouterResult, float]] = {}
        self._cache_ttl = cache_ttl_seconds

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def evaluate(self, query: str) -> RouterResult:
        query_norm = query.strip().lower()
        cache_key = query_norm
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        available_models = await self._get_available_models()
        router_model = self._resolve_router_model(available_models)
        if not router_model:
            logger.warning("No router model available, using heuristic fallback")
            result = self._heuristic_fallback(query)
            self._set_cache(cache_key, result)
            return result

        result = await self._query_router_model(query, router_model, available_models)
        if result is None:
            logger.warning("Router model response parsing failed, using heuristic fallback")
            result = self._heuristic_fallback(query)

        self._set_cache(cache_key, result)
        return result

    def _check_cache(self, key: str) -> RouterResult | None:
        import time
        if key in self._cache:
            result, ts = self._cache[key]
            if time.monotonic() - ts < self._cache_ttl:
                return result
            del self._cache[key]
        return None

    def _set_cache(self, key: str, result: RouterResult):
        import time
        self._cache[key] = (result, time.monotonic())
        if len(self._cache) > 100:
            purge_keys = [k for k, (_, ts) in self._cache.items()
                          if time.monotonic() - ts > self._cache_ttl]
            for k in purge_keys:
                del self._cache[k]

    async def _get_available_models(self) -> list[str]:
        try:
            resp = await self.client.get(f"{self.ollama_base}/api/tags", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.debug("Failed to list Ollama models: %s", exc)
            return []

    def _resolve_router_model(self, available: list[str]) -> str | None:
        if self.router_model in available:
            return self.router_model
        for candidate in (self.router_model, "llama3.2:3b", "llama3.2:1b", "gemma2:2b", "deepseek-r1:8b"):
            if candidate in available or any(candidate in m for m in available):
                return candidate
        return None

    async def _query_router_model(self, query: str, model: str, available: list[str]) -> RouterResult | None:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this query for routing: {query}"},
            ],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 256},
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
            return self._parse_response(raw, model)
        except Exception as exc:
            logger.warning("Router model query failed: %s", exc)

        return None

    def _parse_response(self, raw: str, model_used: str) -> RouterResult | None:
        json_match = None
        for bracket_depth in range(0, raw.count("{") + 1):
            start = raw.find("{")
            if start == -1:
                continue
            end = raw.rfind("}")
            if end == -1 or end < start:
                continue
            candidate = raw[start:end+1]
            try:
                json_match = json.loads(candidate)
                break
            except json.JSONDecodeError:
                for i in range(start + 1, len(raw)):
                    if raw[i] == "{":
                        candidate = raw[i:end+1]
                        try:
                            json_match = json.loads(candidate)
                            break
                        except json.JSONDecodeError:
                            continue
                    break
                break

        if json_match is None:
            return None

        route = json_match.get("route", "")
        if route not in ("local", "cloud"):
            return None

        return RouterResult(
            route=route,
            reason=json_match.get("reason", ""),
            required_capabilities=json_match.get("required_capabilities", []),
            model_used=model_used,
            raw_response=raw,
        )

    def _heuristic_fallback(self, query: str) -> RouterResult:
        q = query.strip().lower()
        word_count = len(q.split())

        cloud_keywords = [
            "browse", "search the web", "go to ", "http", "www.", ".com",
            "forecast", "predict", "analyze", "research", "multi-step",
            "browser", "navigate", "click on", "type in", "fill in",
            "captcha", "login", "authenticate", "scrape", "extract data",
            "current", "latest", "recent", "news", "today",
            "code execution", "run this", "execute", "file system",
            "download", "upload", "attach", "csv", "json file",
        ]

        cloud_count = sum(1 for kw in cloud_keywords if kw in q)
        if cloud_count >= 2:
            return RouterResult(
                route="cloud",
                reason=f"Heuristic: {cloud_count} cloud-trigger keywords matched",
                confidence=0.6 + min(cloud_count * 0.1, 0.3),
            )

        single_kw = ["browse", "forecast", "predict", "scrape", "analyze csv",
                      "current events", "web search", "browser automation"]
        if any(kw in q for kw in single_kw):
            return RouterResult(
                route="cloud",
                reason=f"Heuristic: cloud-trigger keyword matched",
                confidence=0.5,
            )

        if word_count <= 8:
            return RouterResult(
                route="local",
                reason="Heuristic: short query, likely simple",
                confidence=0.7,
            )

        return RouterResult(
            route="local",
            reason="Heuristic: no cloud triggers detected, routing to local by default",
            confidence=0.5,
        )

    async def route(
        self,
        query: str,
        has_local_model: bool = True,
        has_cloud_provider: bool = False,
    ) -> RouterResult:
        result = await self.evaluate(query)

        if result.route == "cloud" and not has_cloud_provider:
            logger.info("Cloud route requested but no cloud provider configured, forcing local")
            return RouterResult(
                route="local",
                reason="Cloud provider not configured",
                confidence=0.8,
            )

        if result.route == "local" and not has_local_model:
            logger.info("Local route requested but no local model available, forcing cloud")
            return RouterResult(
                route="cloud",
                reason="No local model available",
                confidence=0.8,
            )

        return result
