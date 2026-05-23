from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
import shutil
from time import perf_counter
from typing import AsyncIterator, Protocol

import httpx

from .config import NEXUSConfig
from .telemetry import RuntimeTelemetry


class ModelProvider(Protocol):
    name: str

    def available(self) -> bool:
        ...

    def cost_estimate(self) -> float:
        ...


@dataclass(slots=True)
class StaticModelProvider:
    name: str
    is_available: bool
    estimated_cost: float
    provider_kind: str
    uses_mock: bool = False

    def available(self) -> bool:
        return self.is_available

    def cost_estimate(self) -> float:
        return self.estimated_cost


@dataclass(slots=True)
class ModelInvocationResult:
    text: str
    model_name: str
    estimated_cost: float
    latency_ms: float
    used_mock: bool
    fallback_used: bool


@dataclass(slots=True)
class ModelStreamChunk:
    text: str
    model_name: str
    used_mock: bool
    fallback_used: bool
    done: bool = False


class ModelRegistry:
    def __init__(
        self,
        config: NEXUSConfig,
        secret_registry,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self.config = config
        self.secret_registry = secret_registry
        self.telemetry = telemetry
        self._provider_semaphore = asyncio.Semaphore(max(1, config.models.provider_max_concurrency))
        self._queued_requests = 0
        self._active_requests = 0
        local_ready = self._local_model_ready(config.models.local_model)
        self.local = StaticModelProvider(
            name=config.models.local_model,
            is_available=local_ready,
            estimated_cost=config.models.local_cost_per_call,
            provider_kind="local",
        )
        self.local_mock = StaticModelProvider(
            name=config.models.local_fallback_model,
            is_available=config.models.enable_mock_fallbacks,
            estimated_cost=config.models.local_cost_per_call,
            provider_kind="local",
            uses_mock=True,
        )
        self.byok = StaticModelProvider(
            name=config.models.byok_model,
            is_available=bool(secret_registry.get_secret(config.models.byok_secret_name)),
            estimated_cost=config.models.byok_cost_per_call,
            provider_kind="byok",
        )
        self.byok_mock = StaticModelProvider(
            name=config.models.byok_fallback_model,
            is_available=config.models.enable_mock_fallbacks,
            estimated_cost=config.models.byok_cost_per_call,
            provider_kind="byok",
            uses_mock=True,
        )

    def refresh(self) -> None:
        self.local.is_available = self._local_model_ready(self.config.models.local_model)
        self.byok.is_available = bool(
            self.secret_registry.get_secret(self.config.models.byok_secret_name)
        )

    def get(self, tier_name: str) -> StaticModelProvider:
        self.refresh()
        if tier_name == "byok":
            return self.byok if self.byok.available() else self.byok_mock
        return self.local if self.local.available() else self.local_mock

    def provider_chain(self, preferred: str) -> list[StaticModelProvider]:
        self.refresh()
        if preferred == "byok":
            chain = [self.byok, self.local, self.byok_mock, self.local_mock]
        else:
            chain = [self.local, self.byok, self.byok_mock, self.local_mock]
        deduped: list[StaticModelProvider] = []
        seen: set[str] = set()
        for provider in chain:
            key = f"{provider.provider_kind}:{provider.name}:{provider.uses_mock}"
            if provider.available() and key not in seen:
                deduped.append(provider)
                seen.add(key)
        return deduped

    async def complete(self, prompt: str, preferred: str) -> ModelInvocationResult:
        chain = self.provider_chain(preferred)
        if not chain:
            raise RuntimeError("No providers or mock fallbacks are available.")
        last_error: Exception | None = None
        for index, provider in enumerate(chain):
            attempt = index + 1
            if attempt > 1 and self.telemetry is not None:
                self.telemetry.increment("provider.retries_total")
            try:
                return await self._invoke_with_limit(
                    provider=provider,
                    prompt=prompt,
                    fallback_used=index > 0,
                )
            except asyncio.CancelledError:
                if self.telemetry is not None:
                    self.telemetry.increment("provider.cancellations_total")
                raise
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if self.telemetry is not None:
                    self.telemetry.increment("provider.failures_total", provider=provider.name)
                    self.telemetry.emit(
                        "provider_attempt_failed",
                        provider=provider.name,
                        provider_kind=provider.provider_kind,
                        fallback_used=index > 0,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                continue
        raise RuntimeError(str(last_error) if last_error else "Provider invocation failed.")

    async def stream(self, prompt: str, preferred: str) -> AsyncIterator[ModelStreamChunk]:
        chain = self.provider_chain(preferred)
        if not chain:
            raise RuntimeError("No providers or mock fallbacks are available.")
        last_error: Exception | None = None
        for index, provider in enumerate(chain):
            attempt = index + 1
            if attempt > 1 and self.telemetry is not None:
                self.telemetry.increment("provider.retries_total")
            try:
                async for chunk in self._stream_with_limit(
                    provider=provider,
                    prompt=prompt,
                    fallback_used=index > 0,
                ):
                    yield chunk
                return
            except asyncio.CancelledError:
                if self.telemetry is not None:
                    self.telemetry.increment("provider.cancellations_total")
                raise
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if self.telemetry is not None:
                    self.telemetry.increment("provider.failures_total", provider=provider.name)
                    self.telemetry.emit(
                        "provider_stream_failed",
                        provider=provider.name,
                        provider_kind=provider.provider_kind,
                        fallback_used=index > 0,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                continue
        raise RuntimeError(str(last_error) if last_error else "Provider stream failed.")

    async def _invoke_with_limit(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
    ) -> ModelInvocationResult:
        started = perf_counter()
        self._queued_requests += 1
        self._emit_queue_metrics()
        try:
            async with self._provider_semaphore:
                self._queued_requests -= 1
                self._active_requests += 1
                self._emit_queue_metrics()
                try:
                    if self.telemetry is not None:
                        self.telemetry.emit(
                            "provider_request_started",
                            provider=provider.name,
                            provider_kind=provider.provider_kind,
                            uses_mock=provider.uses_mock,
                            fallback_used=fallback_used,
                        )
                    result = await self._invoke(provider, prompt, fallback_used)
                    if self.telemetry is not None:
                        self.telemetry.increment("provider.success_total", provider=provider.name)
                        self.telemetry.emit(
                            "provider_request_completed",
                            provider=provider.name,
                            provider_kind=provider.provider_kind,
                            uses_mock=provider.uses_mock,
                            fallback_used=fallback_used,
                            latency_ms=round((perf_counter() - started) * 1000, 3),
                            cost=result.estimated_cost,
                        )
                    return result
                finally:
                    self._active_requests -= 1
                    self._emit_queue_metrics()
        except Exception:
            if self._queued_requests > 0:
                self._queued_requests -= 1
                self._emit_queue_metrics()
            raise

    async def _stream_with_limit(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
    ) -> AsyncIterator[ModelStreamChunk]:
        self._queued_requests += 1
        self._emit_queue_metrics()
        try:
            async with self._provider_semaphore:
                self._queued_requests -= 1
                self._active_requests += 1
                self._emit_queue_metrics()
                try:
                    if self.telemetry is not None:
                        self.telemetry.emit(
                            "provider_stream_started",
                            provider=provider.name,
                            provider_kind=provider.provider_kind,
                            uses_mock=provider.uses_mock,
                            fallback_used=fallback_used,
                        )
                    async for chunk in self._invoke_stream(provider, prompt, fallback_used):
                        if self.telemetry is not None and chunk.text:
                            self.telemetry.increment(
                                "provider.stream_chunks_total",
                                provider=provider.name,
                            )
                        yield chunk
                finally:
                    self._active_requests -= 1
                    self._emit_queue_metrics()
        except Exception:
            if self._queued_requests > 0:
                self._queued_requests -= 1
                self._emit_queue_metrics()
            raise

    async def _invoke(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
    ) -> ModelInvocationResult:
        if provider.uses_mock:
            return await self._mock_completion(provider, prompt, fallback_used)
        if provider.provider_kind == "local":
            return await self._litellm_completion(
                provider=provider,
                prompt=prompt,
                fallback_used=fallback_used,
                api_base=self.config.models.local_api_base,
                api_key="ollama",
            )
        api_key = self.secret_registry.get_secret(self.config.models.byok_secret_name)
        if not api_key:
            raise RuntimeError("BYOK secret is unavailable.")
        return await self._litellm_completion(
            provider=provider,
            prompt=prompt,
            fallback_used=fallback_used,
            api_key=api_key,
        )

    async def _invoke_stream(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
    ) -> AsyncIterator[ModelStreamChunk]:
        if provider.uses_mock:
            parts = await self._mock_stream_parts(provider, prompt)
            for index, part in enumerate(parts):
                yield ModelStreamChunk(
                    text=part,
                    model_name=provider.name,
                    used_mock=True,
                    fallback_used=fallback_used,
                    done=index == len(parts) - 1,
                )
            return
        if provider.provider_kind != "local":
            result = await self._invoke(provider, prompt, fallback_used)
            yield ModelStreamChunk(
                text=result.text,
                model_name=result.model_name,
                used_mock=result.used_mock,
                fallback_used=result.fallback_used,
                done=True,
            )
            return
        model_name = self._provider_model_name(provider.name)
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {"temperature": 0},
        }
        timeout = httpx.Timeout(self.config.models.stream_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.config.models.local_api_base}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                saw_done = False
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    text = data.get("message", {}).get("content", "")
                    saw_done = saw_done or bool(data.get("done"))
                    yield ModelStreamChunk(
                        text=text,
                        model_name=provider.name,
                        used_mock=False,
                        fallback_used=fallback_used,
                        done=bool(data.get("done")),
                    )
                if not saw_done:
                    raise RuntimeError("Provider stream ended before a done marker was received.")

    async def _litellm_completion(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
        api_key: str,
        api_base: str | None = None,
    ) -> ModelInvocationResult:
        from litellm import acompletion

        started = perf_counter()
        response = await acompletion(
            model=provider.name,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            api_base=api_base,
            timeout=self.config.models.provider_timeout_seconds,
            temperature=0,
        )
        latency_ms = (perf_counter() - started) * 1000
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("Provider returned no choices.")
        message = getattr(choices[0], "message", None)
        content = self._coerce_message_content(getattr(message, "content", ""))
        if not content.strip():
            raise RuntimeError("Provider returned empty content.")
        estimated_cost = self._estimate_cost(provider, response)
        return ModelInvocationResult(
            text=content,
            model_name=provider.name,
            estimated_cost=max(estimated_cost, provider.estimated_cost),
            latency_ms=latency_ms,
            used_mock=False,
            fallback_used=fallback_used,
        )

    async def _mock_completion(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
    ) -> ModelInvocationResult:
        await asyncio.sleep(self.config.models.mock_latency_ms / 1000.0)
        shortened = " ".join(prompt.split())[:160]
        return ModelInvocationResult(
            text=f"{self.config.models.mock_response_prefix} {shortened}".strip(),
            model_name=provider.name,
            estimated_cost=max(provider.estimated_cost, 0.001),
            latency_ms=float(self.config.models.mock_latency_ms),
            used_mock=True,
            fallback_used=fallback_used,
        )

    async def _mock_stream_parts(
        self,
        provider: StaticModelProvider,
        prompt: str,
    ) -> list[str]:
        result = await self._mock_completion(provider, prompt, fallback_used=False)
        text = result.text
        words = text.split()
        if len(words) < 3:
            return [text]
        midpoint = max(1, len(words) // 2)
        return [" ".join(words[:midpoint]) + " ", " ".join(words[midpoint:])]

    def _coerce_message_content(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content or "")

    def _estimate_cost(self, provider: StaticModelProvider, response) -> float:
        usage = getattr(response, "usage", None)
        if usage is None:
            return provider.estimated_cost
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens <= 0:
            return provider.estimated_cost
        return max(provider.estimated_cost, total_tokens * (provider.estimated_cost / 1000.0))

    def _local_model_ready(self, model_name: str) -> bool:
        target = self._provider_model_name(model_name)
        try:
            response = httpx.get(f"{self.config.models.local_api_base}/api/tags", timeout=1.5)
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models", [])
            return any(model.get("name") == target for model in models)
        except Exception:
            return shutil.which("ollama") is not None or self._ollama_install_exists()

    def _provider_model_name(self, model_name: str) -> str:
        return model_name.split("/", 1)[-1]

    def _emit_queue_metrics(self) -> None:
        if self.telemetry is None:
            return
        self.telemetry.set_gauge("provider.queue_depth", float(self._queued_requests))
        self.telemetry.set_gauge("provider.active_requests", float(self._active_requests))

    def _ollama_install_exists(self) -> bool:
        return shutil.which("ollama") is not None or os.path.exists(
            r"C:\Users\Gaurav\AppData\Local\Programs\Ollama\ollama.exe"
        )
