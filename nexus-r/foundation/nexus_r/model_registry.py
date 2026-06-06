from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
import os
import shutil
import time
from time import perf_counter
from typing import Any, AsyncIterator, Protocol

import httpx

logger = logging.getLogger("nexus-r.registry")

from .config import NEXUSConfig
from .errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderEmptyResponseError,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderModelUnavailableError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from .telemetry import RuntimeTelemetry
from .backend_manager import BackendManager


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
    reasoning_tokens: int | None = None


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
        self._last_model_reason = ''
        self._sentence_transformer_model = None
        self._sentence_transformer_loaded = False
        self._anchor_embeddings = {}
        # --- Latency optimization caches ---
        self._local_ready_cache: bool | None = None
        self._local_ready_cache_time: float = 0.0
        self._tags_cache: list[str] = []
        self._tags_cache_time: float = 0.0
        self._persistent_client: httpx.AsyncClient | None = None
        self._semantic_categories = {
            "coding": {
                "model_keyword": "coder",
                "default_model": "antigravity-coder:latest",
                "reason_name": "Coding",
                "anchors": [
                    "write a python script to parse json",
                    "how to implement a database query in sql",
                    "debug this syntax error in javascript",
                    "create an API endpoint with FastAPI",
                    "implement a binary search algorithm in rust",
                    "how to resolve git merge conflicts",
                    "explain class inheritance in python"
                ]
            },
            "math_reasoning": {
                "model_keyword": "deepseek-r1",
                "default_model": "deepseek-r1:8b",
                "reason_name": "Math & Reasoning",
                "anchors": [
                    "solve the quadratic equation and explain steps",
                    "calculate the integral of x times cosine x",
                    "what are the confidence intervals for this distribution",
                    "run a forecast regression analysis",
                    "prove the pythagorean theorem",
                    "compute the derivative of log x",
                    "calculate standard deviation and variance"
                ]
            },
            "creative": {
                "model_keyword": "gemma2",
                "default_model": "gemma2:9b",
                "reason_name": "Creative & Writing",
                "anchors": [
                    "write a short story about an astronaut on mars",
                    "compose a lyrical poem about the changing seasons",
                    "draft an essay comparing Keynesian vs Classical economics",
                    "write an engaging blog post introduction",
                    "create a screenplay scene between two detectives",
                    "write an email to ask for a deadline extension",
                    "draft a recipe blog article"
                ]
            },
            "conversational": {
                "model_keyword": "gemma2",
                "default_model": "gemma2:9b",
                "reason_name": "Conversational & Lightweight",
                "anchors": [
                    "hi",
                    "hello there, how are you",
                    "thanks so much",
                    "ok sounds good",
                    "bye",
                    "yes",
                    "no",
                    "sure that works"
                ]
            }
        }
        local_ready = self._local_model_ready(config.models.local_model)
        self.local = StaticModelProvider(
            name=config.models.local_model,
            is_available=local_ready,
            estimated_cost=config.models.local_cost_per_call,
            provider_kind="local",
        )
        self.byok = StaticModelProvider(
            name=config.models.byok_model,
            is_available=bool(secret_registry.get_secret(config.models.byok_secret_name)),
            estimated_cost=config.models.byok_cost_per_call,
            provider_kind="byok",
        )

    def refresh(self) -> None:
        self.local.is_available = self._local_model_ready(self.config.models.local_model)
        self.byok.is_available = bool(
            self.secret_registry.get_secret(self.config.models.byok_secret_name)
        )

    def get(self, tier_name: str) -> StaticModelProvider:
        self.refresh()
        if tier_name == "byok":
            if not self.byok.available():
                raise RuntimeError("BYOK provider is not available. Please configure an API key.")
            return self.byok
        if not self.local.available():
            raise RuntimeError("Local provider is not available. Please start Ollama or configure a model.")
        return self.local

    def is_vision_model(self, model_name: str, modality: str | None = None) -> bool:
        """Check if a model name indicates vision capabilities.

        Args:
            model_name: The model identifier string.
            modality: Optional OpenRouter modality string (e.g. "text+image->text").
                      Takes priority over keyword matching when provided.
        """
        if modality == "text+image->text":
            return True
        if not model_name:
            return False
        name = model_name.lower()
        vision_keywords = ["vl", "vision", "llava", "gpt-4o", "claude-3.5-sonnet", "gemini-1.5", "pixtral", "llama3.2-vision"]
        return any(kw in name for kw in vision_keywords)

    def provider_chain(self, preferred: str) -> list[StaticModelProvider]:
        self.refresh()
        
        # If the user explicitly provided a model name, let's honor it by creating an ephemeral provider!
        if preferred and preferred not in ("byok", "local", "System Default", "auto"):
            is_cloud = "/" in preferred and not preferred.startswith("ollama/")
            ephemeral_provider = StaticModelProvider(
                name=preferred,
                is_available=True,
                estimated_cost=0.01,
                provider_kind="byok" if is_cloud else "local",
            )
            # Create a chain starting with the explicit request, then falling back
            if is_cloud:
                chain = [ephemeral_provider, self.local, self.byok]
            else:
                chain = [ephemeral_provider, self.byok, self.local]
        else:
            if preferred == "byok":
                chain = [self.byok, self.local]
            else:
                chain = [self.local, self.byok]
                
        deduped: list[StaticModelProvider] = []
        seen: set[str] = set()
        for provider in chain:
            if not provider.name or not str(provider.name).strip():
                continue
            key = f"{provider.provider_kind}:{provider.name}:{provider.uses_mock}"
            if provider.available() and key not in seen:
                deduped.append(provider)
                seen.add(key)
        return deduped

    async def complete(self, prompt: str, preferred: str, images: list[str] | None = None, messages: list[dict[str, Any]] | None = None) -> ModelInvocationResult:
        chain = self.provider_chain(preferred)
        if not chain:
            raise RuntimeError("No models are available to serve the request. Please configure a cloud API key or start local Ollama.")
        last_error: Exception | None = None
        failures = []
        for index, provider in enumerate(chain):
            attempt = index + 1
            is_fallback = index > 0
            if is_fallback and self.telemetry is not None:
                self.telemetry.increment("provider.retries_total")
                self.telemetry.emit(
                    "provider_fallback_activated",
                    provider=provider.name,
                    provider_kind=provider.provider_kind,
                    chain_position=attempt,
                    total_in_chain=len(chain),
                )
            try:
                result = await self._invoke_with_limit(
                    provider=provider,
                    prompt=prompt,
                    fallback_used=is_fallback,
                    images=images,
                    messages=messages,
                )
                for f in failures:
                    self._log_provider_failure(*f)
                return result
            except asyncio.CancelledError:
                if self.telemetry is not None:
                    self.telemetry.increment("provider.cancellations_total")
                raise
            except ProviderError as exc:
                last_error = exc
                failures.append((exc, attempt, is_fallback))
                continue
            except Exception as exc:
                last_error = exc
                mapped = self._classify_unexpected_error(exc, provider)
                failures.append((mapped, attempt, is_fallback))
                continue
                
        for f in failures:
            self._log_provider_failure(*f)
        raise self._build_chain_exhausted_error(last_error, preferred)

    async def stream(self, prompt: str, preferred: str, images: list[str] | None = None, messages: list[dict[str, Any]] | None = None) -> AsyncIterator[ModelStreamChunk]:
        chain = self.provider_chain(preferred)
        if not chain:
            raise RuntimeError("No models are available to serve the request. Please configure a cloud API key or start local Ollama.")
        last_error: Exception | None = None
        failures = []
        for index, provider in enumerate(chain):
            attempt = index + 1
            is_fallback = index > 0
            if is_fallback and self.telemetry is not None:
                self.telemetry.increment("provider.retries_total")
                self.telemetry.emit(
                    "provider_fallback_activated",
                    provider=provider.name,
                    provider_kind=provider.provider_kind,
                    chain_position=attempt,
                    total_in_chain=len(chain),
                )
            try:
                for f in failures:
                    self._log_provider_failure(*f)
                failures.clear()
                
                async for chunk in self._stream_with_limit(
                    provider=provider,
                    prompt=prompt,
                    fallback_used=is_fallback,
                    images=images,
                    messages=messages,
                ):
                    yield chunk
                return
            except asyncio.CancelledError:
                if self.telemetry is not None:
                    self.telemetry.increment("provider.cancellations_total")
                raise
            except ProviderError as exc:
                last_error = exc
                failures.append((exc, attempt, is_fallback))
                continue
            except Exception as exc:
                last_error = exc
                mapped = self._classify_unexpected_error(exc, provider)
                failures.append((mapped, attempt, is_fallback))
                continue
                
        for f in failures:
            self._log_provider_failure(*f)
        raise self._build_chain_exhausted_error(last_error, preferred)

    def _classify_provider_error(
        self,
        exc: Exception,
        provider: StaticModelProvider,
        *,
        stream_context: bool = False,
    ) -> ProviderError:
        tier = provider.provider_kind
        provider_name = provider.name
        if isinstance(exc, asyncio.TimeoutError):
            msg = (
                f"{'Ollama' if tier == 'local' else 'Groq'} timeout after "
                f"{self.config.models.provider_timeout_seconds}s: "
                f"{'verify Ollama server is running on localhost:11434' if tier == 'local' else 'provider overloaded or network unreachable'}"
            )
            return ProviderTimeoutError(
                msg, provider=provider_name, tier=tier,
                failure_class="timeout", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        if isinstance(exc, httpx.ConnectError):
            host = self.config.models.local_api_base if tier == "local" else "api.groq.com"
            msg = (
                f"{'Ollama' if tier == 'local' else 'Groq'} connection refused: "
                f"verify {'Ollama server is running on ' + host if tier == 'local' else 'network connectivity to ' + host}"
            )
            return ProviderConnectionError(
                msg, provider=provider_name, tier=tier,
                failure_class="connection_refused", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        if isinstance(exc, httpx.TimeoutException):
            msg = (
                f"{'Ollama' if tier == 'local' else 'Groq'} HTTP timeout after "
                f"{self.config.models.provider_timeout_seconds}s"
            )
            return ProviderTimeoutError(
                msg, provider=provider_name, tier=tier,
                failure_class="http_timeout", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 401 or status == 403:
                key_source = "NEXUS_BYOK_API_KEY" if tier == "byok" else "default"
                msg = (
                    f"{'Groq' if tier == 'byok' else 'Provider'} authentication failed "
                    f"(HTTP {status}): verify API key in {key_source} is valid and not expired"
                )
                return ProviderAuthError(
                    msg, provider=provider_name, tier=tier,
                    failure_class="authentication", retryable=False,
                    fallback_decision="skip_chain_if_exhausted",
                )
            if status == 429:
                msg = (
                    f"{'Groq' if tier == 'byok' else 'Provider'} rate-limited "
                    f"(HTTP 429): retry after cooldown or fallback to lower-cost tier"
                )
                return ProviderRateLimitError(
                    msg, provider=provider_name, tier=tier,
                    failure_class="rate_limit", retryable=True,
                    fallback_decision="attempt_next_in_chain",
                )
            if status == 404:
                msg = (
                    f"Model '{provider_name}' not found: verify model name is correct "
                    f"{'and run `ollama pull ' + self._provider_model_name(provider_name) + '`' if tier == 'local' else 'for the provider'}"
                )
                return ProviderModelUnavailableError(
                    msg, provider=provider_name, tier=tier,
                    failure_class="model_not_found", retryable=False,
                    fallback_decision="skip_chain_if_exhausted",
                )
            msg = f"{'Ollama' if tier == 'local' else 'Groq'} HTTP error {status}"
            return ProviderError(
                msg, provider=provider_name, tier=tier,
                failure_class=f"http_{status}", retryable=status >= 500,
                fallback_decision="attempt_next_in_chain" if status >= 500 else "skip_chain_if_exhausted",
            )
        if isinstance(exc, (json.JSONDecodeError, RuntimeError)):
            exc_str = str(exc)
            msg = (
                f"{'Ollama' if tier == 'local' else 'Groq'} returned malformed response: "
                f"{exc_str[:120]}"
            )
            return ProviderMalformedResponseError(
                msg, provider=provider_name, tier=tier,
                failure_class="malformed_response", retryable=False,
                fallback_decision="skip_chain_if_exhausted",
            )
        return ProviderError(
            str(exc)[:200], provider=provider_name, tier=tier,
            failure_class=type(exc).__name__, retryable=True,
            fallback_decision="attempt_next_in_chain",
        )

    def _classify_unexpected_error(self, exc: Exception, provider: StaticModelProvider) -> ProviderError:
        return ProviderError(
            str(exc)[:200], provider=provider.name, tier=provider.provider_kind,
            failure_class=f"unexpected:{type(exc).__name__}", retryable=True,
            fallback_decision="attempt_next_in_chain",
        )

    def _log_provider_failure(self, exc: ProviderError, attempt: int, was_fallback: bool) -> None:
        if self.telemetry is None:
            return
        self.telemetry.increment("provider.failures_total", provider=exc.provider, failure_class=exc.failure_class)
        self.telemetry.increment("provider.attempts_total")
        self.telemetry.emit(
            "provider_attempt_failed",
            provider=exc.provider,
            tier=exc.tier,
            failure_class=exc.failure_class,
            retryable=exc.retryable,
            fallback_decision=exc.fallback_decision,
            fallback_was_already=was_fallback,
            chain_position=attempt,
            error_message=str(exc),
        )

    def _build_chain_exhausted_error(self, last_error: Exception | None, preferred: str) -> RuntimeError:
        if isinstance(last_error, ProviderError):
            details = last_error.to_dict()
            msg = (
                f"All providers in chain exhausted for preferred='{preferred}'. "
                f"Last provider={details['provider']}, failure_class={details['failure_class']}, "
                f"retryable={details['retryable']}, fallback_decision={details['fallback_decision']}. "
                f"Error: {last_error}"
            )
            return RuntimeError(msg)
        return RuntimeError(str(last_error) if last_error else f"All providers exhausted for preferred='{preferred}'.")

    async def _invoke_with_limit(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
        images: list[str] | None = None,
        messages: list[dict[str, Any]] | None = None,
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
                    result = await self._invoke(provider, prompt, fallback_used, images=images, messages=messages)
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
        images: list[str] | None = None,
        messages: list[dict[str, Any]] | None = None,
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
                    async for chunk in self._invoke_stream(provider, prompt, fallback_used, images=images, messages=messages):
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

    def _compute_cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)

    def _get_embedding(self, text: str, local_models: list[str]) -> list[float]:
        import sys
        if "pytest" in sys.modules:
            return [0.1] * 384
        if not self._sentence_transformer_loaded:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_transformer_model = SentenceTransformer('all-MiniLM-L6-v2')
                self._sentence_transformer_loaded = True
                logger.info("SentenceTransformer (all-MiniLM-L6-v2) successfully loaded.")
            except ImportError:
                self._sentence_transformer_loaded = False
            except Exception as e:
                logger.warning(f"Failed to initialize sentence-transformers: {e}")
                self._sentence_transformer_loaded = False

        if self._sentence_transformer_loaded and self._sentence_transformer_model:
            try:
                embedding = self._sentence_transformer_model.encode(text).tolist()
                return embedding
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding failed: {e}")

        # Mode 2: Ollama Embeddings API
        try:
            BackendManager.get_instance().ensure_running()
            api_base = BackendManager.get_instance().base_url
        except Exception:
            api_base = self.config.models.local_api_base
            
        active_model = self.config.models.local_model.replace("ollama/", "")
        candidate_models = [active_model] + local_models + ["gemma2:9b", "llama3.2:3b", "qwen2.5:1.5b-instruct"]
        
        seen = set()
        embed_models = [m for m in candidate_models if not (m in seen or seen.add(m))]
        
        for m in embed_models:
            m_clean = m.replace("ollama/", "")
            try:
                response = httpx.post(
                    f"{api_base}/api/embed",
                    json={"model": m_clean, "input": text},
                    timeout=2.0
                )
                if response.status_code == 200:
                    embeddings = response.json().get("embeddings", [])
                    if embeddings:
                        return embeddings[0]
            except Exception:
                pass

            try:
                response = httpx.post(
                    f"{api_base}/api/embeddings",
                    json={"model": m_clean, "prompt": text},
                    timeout=2.0
                )
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    if embedding:
                        return embedding
            except Exception:
                pass
                
        return [0.0] * 384

    def _get_available_models(self) -> list[str]:
        """Return cached list of available Ollama models, refreshing every 60s."""
        # Use cached /api/tags result (60s TTL) to avoid blocking HTTP per request
        import time as _time
        now = _time.time()
        if self._tags_cache and now - self._tags_cache_time < 60.0:
            return self._tags_cache
        try:
            BackendManager.get_instance().ensure_running()
            api_base = BackendManager.get_instance().base_url
            response = httpx.get(f"{api_base}/api/tags", timeout=1.0)
            if response.status_code == 200:
                self._tags_cache = [m.get("name") for m in response.json().get("models", [])]
                self._tags_cache_time = now
                return self._tags_cache
        except Exception:
            pass
        return self._tags_cache

    def _local_model_ready(self, model_name: str) -> bool:
        now = time.time()
        if self._local_ready_cache is not None and (now - self._local_ready_cache_time) < 60.0:
            return self._local_ready_cache
        
        try:
            available = self._get_available_models()
            clean_name = model_name.replace("ollama/", "")
            exact_match = any(clean_name in m for m in available)
            if exact_match:
                self._local_ready_cache = True
            else:
                # No exact match — still mark ready if any local model is running
                # (invoke will pick the best available model dynamically)
                self._local_ready_cache = len(available) > 0
            self._local_ready_cache_time = now
        except Exception:
            self._local_ready_cache = False
        return self._local_ready_cache

    def _get_dynamic_local_model(self, prompt: str) -> str:
        available_models = self._get_available_models()

        def find_model(target: str, keyword: str) -> str | None:
            for m in available_models:
                if keyword in m:
                    return f"ollama/{m}"
            if target in available_models:
                return f"ollama/{target}"
            return None

        # ═══════════════════════════════════════════════════════
        # HEURISTICS PRE-ROUTING STAGE (Fast, low-overhead bypass)
        # ═══════════════════════════════════════════════════════

        prompt_lower = prompt.lower()
        word_count = len(prompt.split())

        # Heuristic 1: Simple greeting/short acknowledgments
        trivial_patterns = [
            'hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay', 'bye',
            'yes', 'no', 'sure', 'good morning', 'good night', 'how are you',
            'lol', 'haha', 'cool', 'nice', 'great', 'awesome', 'wow', 'help',
            'please',
        ]
        if word_count <= 5 and prompt_lower.strip().rstrip('!?.') in trivial_patterns:
            result = find_model("gemma2:9b", "gemma2") or find_model("llama3.2:3b", "llama3.2")
            if result:
                self._last_model_reason = "Heuristic match (Trivial Greeting) → default chat model"
                return result

        # Heuristic 2: Explicit Code blocks syntax in prompt
        if "```" in prompt:
            result = find_model("antigravity-coder:latest", "antigravity-coder") or find_model("qwen2.5-coder:7b", "qwen2.5-coder")
            if result:
                self._last_model_reason = "Heuristic match (Code Syntax Block detected) → specialized code model"
                return result

        # Heuristic 3: Very long prompts (summarization/complex writing prompts)
        if word_count > 250:
            result = find_model("gemma2:9b", "gemma2")
            if result:
                self._last_model_reason = f"Heuristic match (Long Prompt: {word_count} words) → high-capacity model"
                return result

        # Heuristic 4: Keyword-based coding detection (avoids embedding computation)
        code_keywords = {'python', 'javascript', 'typescript', 'code', 'function', 'error', 'bug',
                         'fix', 'implement', 'class', 'variable', 'loop', 'array', 'list', 'dict',
                         'string', 'int', 'float', 'return', 'print', 'async', 'await', 'html',
                         'css', 'react', 'api', 'sql', 'database', 'git', 'compile', 'runtime',
                         'syntax', 'import', 'module', 'package', 'npm', 'pip', 'docker',
                         'debug', 'trace', 'exception', 'stack'}
        prompt_words_lower = set(w.lower().strip('.,;:!?()[]{}') for w in words)
        code_overlap = prompt_words_lower & code_keywords
        if len(code_overlap) >= 2:
            result = find_model("antigravity-coder:latest", "antigravity-coder") or find_model("qwen2.5-coder:7b", "qwen2.5-coder")
            if result:
                self._last_model_reason = f"Heuristic match (Code Keywords: {', '.join(list(code_overlap)[:3])}) → code model"
                return result

        # Heuristic 5: Keyword-based math/reasoning detection
        math_keywords = {'calculate', 'solve', 'equation', 'integral', 'derivative', 'sum',
                         'average', 'median', 'probability', 'statistics', 'theorem', 'proof',
                         'formula', 'algebra', 'geometry', 'calculus', 'matrix', 'vector'}
        math_overlap = prompt_words_lower & math_keywords
        if len(math_overlap) >= 1:
            result = find_model("deepseek-r1:8b", "deepseek-r1")
            if result:
                self._last_model_reason = f"Heuristic match (Math Keywords: {', '.join(list(math_overlap)[:3])}) → reasoning model"
                return result

        # Heuristic 6: Short conversational messages (< 8 words, no technical content)
        if word_count <= 8 and not code_overlap and not math_overlap:
            result = find_model("gemma2:9b", "gemma2") or find_model("llama3.2:3b", "llama3.2")
            if result:
                self._last_model_reason = "Heuristic match (Short Conversational) → default chat model"
                return result

        # Determine the current embedding mode and cache key

        # Determine the current embedding mode and cache key
        if self._sentence_transformer_loaded:
            mode_key = "sentence_transformers"
        else:
            active_model = self.config.models.local_model.replace("ollama/", "")
            candidate_models = [active_model] + available_models + ["gemma2:9b", "llama3.2:3b", "qwen2.5:1.5b-instruct"]
            mode_key = "ollama_fallback"
            for m in candidate_models:
                m_clean = m.replace("ollama/", "")
                if m_clean in available_models:
                    mode_key = f"ollama_{m_clean}"
                    break

        # Warm up/compute anchor embeddings if not already cached for this mode_key
        if mode_key not in self._anchor_embeddings:
            self._anchor_embeddings[mode_key] = {}
            for cat_name, cat_info in self._semantic_categories.items():
                cat_vectors = []
                for anchor in cat_info["anchors"]:
                    vector = self._get_embedding(anchor, available_models)
                    if vector and any(v != 0.0 for v in vector):
                        cat_vectors.append(vector)
                if cat_vectors:
                    self._anchor_embeddings[mode_key][cat_name] = cat_vectors

        # Semantic Similarity Routing
        best_category = None
        best_score = -1.0
        scores = {}
        
        prompt_vector = self._get_embedding(prompt, available_models)
        
        if prompt_vector and any(v != 0.0 for v in prompt_vector) and mode_key in self._anchor_embeddings:
            for cat_name, cat_vectors in self._anchor_embeddings[mode_key].items():
                cat_similarities = []
                for vec in cat_vectors:
                    sim = self._compute_cosine_similarity(prompt_vector, vec)
                    cat_similarities.append(sim)
                
                if cat_similarities:
                    max_sim = max(cat_similarities)
                    avg_top = sum(sorted(cat_similarities, reverse=True)[:2]) / min(2, len(cat_similarities))
                    score = 0.7 * max_sim + 0.3 * avg_top
                    scores[cat_name] = score
                    if score > best_score:
                        best_score = score
                        best_category = cat_name

        # Routing decision based on similarity scores
        # Confidence threshold: 0.40
        if best_category and best_score >= 0.40:
            cat_info = self._semantic_categories[best_category]
            result = find_model(cat_info["default_model"], cat_info["model_keyword"])
            if result:
                self._last_model_reason = f"Semantic match ({best_score:.2f}) to {cat_info['reason_name']} category → {best_category}"
                return result

        # Fallback to configured model
        self._last_model_reason = "Semantic match low/absent → fallback to default model"
        fallback_model = self.config.models.local_model
        if not fallback_model.startswith("ollama/"):
            fallback_model = f"ollama/{fallback_model}"
        return fallback_model

    async def _invoke(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
        images: list[str] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> ModelInvocationResult:
        if provider.uses_mock:
            return await self._mock_completion(provider, prompt, fallback_used)
        if provider.provider_kind == "local":
            try:
                BackendManager.get_instance().ensure_running()
                api_base = BackendManager.get_instance().base_url
            except Exception:
                api_base = self.config.models.local_api_base

            if provider is self.local:
                if "auto" in self.config.models.local_model.lower():
                    provider.name = self._get_dynamic_local_model(prompt)
                else:
                    provider.name = self.config.models.local_model
                if not provider.name.startswith("ollama/"):
                    provider.name = f"ollama/{provider.name}"
                # If the configured model doesn't exist on this machine, fallback to first available
                available_local = self._get_available_models()
                clean = provider.name.replace("ollama/", "")
                if available_local and not any(clean in m for m in available_local):
                    fallback = available_local[0]
                    logger.warning("Configured model %s not found, falling back to %s", clean, fallback)
                    provider.name = f"ollama/{fallback}"
                    self._last_model_reason = f"Fallback (configured {clean} not found) → {fallback}"
                else:
                    self._last_model_reason = "Manual override active → locked to " + provider.name.replace("ollama/", "")
            elif provider.provider_kind == "local":
                if not provider.name.startswith("ollama/"):
                    provider.name = f"ollama/{provider.name}"
                self._last_model_reason = "User Requested Model → " + provider.name.replace("ollama/", "")
            
            logger.info(f"Requested Model: {provider.name} | Actual Model: {provider.name}")
            return await self._litellm_completion(
                provider=provider,
                prompt=prompt,
                fallback_used=fallback_used,
                api_base=api_base,
                api_key="ollama",
                messages=messages,
            )
        KNOWN_LITELLM_PREFIXES = ("groq/", "openai/", "anthropic/", "google/", "ollama/")
        openrouter_key = self.secret_registry.get_secret("openrouter_api_key") or os.environ.get("NEXUS_OPENROUTER_API_KEY")
        is_openrouter_candidate = not provider.name.startswith(KNOWN_LITELLM_PREFIXES)
        
        api_key = self.secret_registry.get_secret(self.config.models.byok_secret_name) if self.config.models.byok_secret_name else None
        
        if not api_key and not (is_openrouter_candidate and openrouter_key):
            secret_name = self.config.models.byok_secret_name or "API key"
            raise ProviderAuthError(
                f"API key not found for {provider.name}: configure keyring secret '{secret_name}' or 'openrouter_api_key'",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="missing_credentials", retryable=False,
                fallback_decision="skip_chain_if_exhausted",
            )
            
        logger.info(f"Requested Model: {provider.name} | Actual Model: {provider.name}")
        
        if is_openrouter_candidate and openrouter_key:
            return await self._litellm_completion(
                provider=provider,
                prompt=prompt,
                fallback_used=fallback_used,
                api_key=openrouter_key,
                api_base="https://openrouter.ai/api/v1",
                messages=messages,
            )
            
        return await self._litellm_completion(
            provider=provider,
            prompt=prompt,
            fallback_used=fallback_used,
            api_key=api_key,
            messages=messages,
        )

    async def _invoke_stream(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
        images: list[str] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:

        if provider.provider_kind != "local":
            KNOWN_LITELLM_PREFIXES = ("groq/", "openai/", "anthropic/", "google/", "ollama/")
            openrouter_key = self.secret_registry.get_secret("openrouter_api_key") or os.environ.get("NEXUS_OPENROUTER_API_KEY")
            is_openrouter_candidate = not provider.name.startswith(KNOWN_LITELLM_PREFIXES)
            
            api_key = self.secret_registry.get_secret(self.config.models.byok_secret_name) if self.config.models.byok_secret_name else None
            
            if not api_key and not (is_openrouter_candidate and openrouter_key):
                secret_name = self.config.models.byok_secret_name or "API key"
                raise ProviderAuthError(
                    f"API key not found for {provider.name}: configure keyring secret '{secret_name}' or 'openrouter_api_key'",
                    provider=provider.name, tier=provider.provider_kind,
                    failure_class="missing_credentials", retryable=False,
                    fallback_decision="skip_chain_if_exhausted",
                )
            
            logger.info(f"Requested Model: {provider.name} | Actual Model: {provider.name}")
                
            if messages:
                msgs = messages
                if images:
                    for i in range(len(msgs) - 1, -1, -1):
                        if msgs[i].get("role") == "user":
                            content = msgs[i].get("content", "")
                            multi_content = [{"type": "text", "text": content}]
                            for img in images:
                                multi_content.append({"type": "image_url", "image_url": {"url": img}})
                            msgs[i] = {"role": "user", "content": multi_content}
                            break
            else:
                msg_content = prompt
                if images:
                    msg_content = [{"type": "text", "text": prompt}]
                    for img in images:
                        msg_content.append({"type": "image_url", "image_url": {"url": img}})
                msgs = [{"role": "user", "content": msg_content}]
            
            # Route bare model names through OpenRouter if its API key exists.
            # This handles model IDs like "moonshotai/kimi-k2.6:free" selected from
            # the chat dropdown regardless of which provider is "default" in settings.
            if openrouter_key and is_openrouter_candidate:
                async for chunk in self._openrouter_stream(
                    provider=provider,
                    api_key=openrouter_key,
                    api_base="https://openrouter.ai/api/v1",
                    messages=msgs,
                    fallback_used=fallback_used,
                ):
                    yield chunk
                return
            
            from litellm import acompletion
            from litellm.exceptions import (
                AuthenticationError, LiteLLMTimeout
            )
                    
            try:
                response = await acompletion(
                    model=provider.name,
                    messages=msgs,
                    api_key=api_key,
                    timeout=self.config.models.stream_timeout_seconds,
                    temperature=0,
                    stream=True,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    yield ModelStreamChunk(
                        text=delta,
                        model_name=provider.name,
                        used_mock=False,
                        fallback_used=fallback_used,
                        done=False,
                    )
                yield ModelStreamChunk(
                    text="",
                    model_name=provider.name,
                    used_mock=False,
                    fallback_used=fallback_used,
                    done=True,
                )
            except Exception as e:
                raise self._classify_provider_error(e, provider)
            return
        if provider is self.local:
            if "auto" in self.config.models.local_model.lower():
                provider.name = self._get_dynamic_local_model(prompt)
            else:
                provider.name = self.config.models.local_model
            if not provider.name.startswith("ollama/"):
                provider.name = f"ollama/{provider.name}"
            available_local = self._get_available_models()
            clean = provider.name.replace("ollama/", "")
            if available_local and not any(clean in m for m in available_local):
                fallback = available_local[0]
                logger.warning("Configured model %s not found in stream, falling back to %s", clean, fallback)
                provider.name = f"ollama/{fallback}"
            self._last_model_reason = "Manual override active → locked to " + provider.name.replace("ollama/", "")
        elif provider.provider_kind == "local":
            if not provider.name.startswith("ollama/"):
                provider.name = f"ollama/{provider.name}"
            self._last_model_reason = "User Requested Model → " + provider.name.replace("ollama/", "")
        
        logger.info(f"Requested Model: {provider.name} | Actual Model: {provider.name}")
        
        try:
            BackendManager.get_instance().ensure_running()
            api_base = BackendManager.get_instance().base_url
        except Exception:
            api_base = self.config.models.local_api_base

        model_name = self._provider_model_name(provider.name)
        if model_name.endswith('.gguf'):
            model_name = model_name[:-5]
        msgs_for_ollama = messages if messages else [{"role": "user", "content": prompt}]
        payload = {
            "model": model_name,
            "messages": msgs_for_ollama,
            "stream": True,
            "options": {"temperature": 0},
            "keep_alive": -1,
        }
        timeout = httpx.Timeout(self.config.models.stream_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{api_base}/api/chat",
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

    async def _openrouter_stream(
        self,
        provider: StaticModelProvider,
        api_key: str,
        api_base: str,
        messages: list[dict],
        fallback_used: bool,
    ) -> AsyncIterator[ModelStreamChunk]:

        payload = {
            "model": provider.name,
            "messages": messages,
            "stream": True,
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        timeout = httpx.Timeout(self.config.models.stream_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", f"{api_base}/chat/completions", json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    saw_done = False
                    reasoning_tokens: int | None = None

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        data = json.loads(data_str)
                        usage = data.get("usage")
                        if usage:
                            saw_done = True
                            reasoning_tokens = usage.get("reasoning_tokens") or usage.get("reasoningTokens")
                            yield ModelStreamChunk(
                                text="",
                                model_name=provider.name,
                                used_mock=False,
                                fallback_used=fallback_used,
                                done=True,
                                reasoning_tokens=reasoning_tokens,
                            )
                            continue

                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        text = delta.get("content", "") or ""
                        if text:
                            yield ModelStreamChunk(
                                text=text,
                                model_name=provider.name,
                                used_mock=False,
                                fallback_used=fallback_used,
                                done=False,
                            )

                    if not saw_done:
                        yield ModelStreamChunk(
                            text="",
                            model_name=provider.name,
                            used_mock=False,
                            fallback_used=fallback_used,
                            done=True,
                            reasoning_tokens=reasoning_tokens,
                        )
        except httpx.HTTPStatusError as exc:
            raise self._classify_provider_error(exc, provider)
        except httpx.TimeoutException as exc:
            raise self._classify_provider_error(exc, provider)
        except httpx.ConnectError as exc:
            raise self._classify_provider_error(exc, provider)

    async def _litellm_completion(
        self,
        provider: StaticModelProvider,
        prompt: str,
        fallback_used: bool,
        api_key: str,
        api_base: str | None = None,
        images: list[str] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> ModelInvocationResult:
        from litellm import acompletion
        from litellm.exceptions import (
            AuthenticationError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout as LiteLLMTimeout,
        )

        started = perf_counter()
        if messages:
            msgs = messages
            if images:
                for i in range(len(msgs) - 1, -1, -1):
                    if msgs[i].get("role") == "user":
                        content = msgs[i].get("content", "")
                        multi_content = [{"type": "text", "text": content}]
                        for img in images:
                            multi_content.append({"type": "image_url", "image_url": {"url": img}})
                        msgs[i] = {"role": "user", "content": multi_content}
                        break
        else:
            msg_content = prompt
            if images:
                msg_content = [{"type": "text", "text": prompt}]
                for img in images:
                    msg_content.append({"type": "image_url", "image_url": {"url": img}})
            msgs = [{"role": "user", "content": msg_content}]

        kwargs = {
            "model": provider.name,
            "messages": msgs,
            "api_key": api_key,
            "api_base": api_base,
            "timeout": self.config.models.provider_timeout_seconds,
            "temperature": 0,
        }
        if provider.provider_kind == "local":
            kwargs["extra_body"] = {"keep_alive": -1}

        try:
            response = await acompletion(**kwargs)
        except asyncio.TimeoutError:
            raise self._classify_provider_error(asyncio.TimeoutError(), provider)
        except httpx.TimeoutException as exc:
            raise self._classify_provider_error(exc, provider)
        except LiteLLMTimeout as exc:
            base = asyncio.TimeoutError()
            raise self._classify_provider_error(base, provider) from exc
        except httpx.ConnectError as exc:
            raise self._classify_provider_error(exc, provider)
        except httpx.HTTPStatusError as exc:
            raise self._classify_provider_error(exc, provider)
        except AuthenticationError as exc:
            raise ProviderAuthError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} authentication failed: "
                f"verify API key is valid. {exc}",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="authentication", retryable=False,
                fallback_decision="skip_chain_if_exhausted",
            )
        except RateLimitError as exc:
            raise ProviderRateLimitError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} rate-limited: "
                f"retry after cooldown or fallback. {exc}",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="rate_limit", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        except ServiceUnavailableError as exc:
            raise ProviderConnectionError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} service unavailable: "
                f"provider may be overloaded. {exc}",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="service_unavailable", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        except httpx.HTTPError as exc:
            raise self._classify_provider_error(exc, provider)
        except json.JSONDecodeError as exc:
            raise ProviderMalformedResponseError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} returned invalid JSON: {exc}",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="malformed_json", retryable=False,
                fallback_decision="skip_chain_if_exhausted",
            )
        except Exception as exc:
            raise self._classify_provider_error(exc, provider)

        latency_ms = (perf_counter() - started) * 1000
        choices = getattr(response, "choices", None)
        if not choices:
            raise ProviderMalformedResponseError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} returned no choices in response.",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="no_choices", retryable=False,
                fallback_decision="skip_chain_if_exhausted",
            )
        message = getattr(choices[0], "message", None)
        content = self._coerce_message_content(getattr(message, "content", ""))
        if not content.strip():
            raise ProviderEmptyResponseError(
                f"{'Groq' if provider.provider_kind == 'byok' else 'Provider'} returned empty content.",
                provider=provider.name, tier=provider.provider_kind,
                failure_class="empty_content", retryable=True,
                fallback_decision="attempt_next_in_chain",
            )
        estimated_cost = self._estimate_cost(provider, response)
        return ModelInvocationResult(
            text=content,
            model_name=provider.name,
            estimated_cost=max(estimated_cost, provider.estimated_cost),
            latency_ms=latency_ms,
            used_mock=False,
            fallback_used=fallback_used,
        )



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

    async def warm_up(self) -> None:
        # Trigger embedder warmup
        self._get_embedding("warm-up", [])
        
        if not self.local.available():
            return
        if self.telemetry is not None:
            self.telemetry.emit("model_warm_up_started", provider=self.local.name)
        try:
            await self._litellm_completion(
                provider=self.local,
                prompt="warm-up",
                fallback_used=False,
                api_base=self.config.models.local_api_base,
                api_key="ollama",
            )
            if self.telemetry is not None:
                self.telemetry.increment("model.warm_ups_total")
                self.telemetry.emit("model_warm_up_completed")
            # Pre-warm the dynamic model routing cache (anchor embeddings)
            if "auto" in self.config.models.local_model.lower():
                try:
                    self._get_dynamic_local_model("hello")
                except Exception:
                    pass
        except Exception:
            if self.telemetry is not None:
                self.telemetry.increment("model.warm_up_failures_total")

        # Pre-warm semantic anchor cache if dynamic model selection is active
        if "auto" in self.config.models.local_model.lower():
            try:
                self._get_dynamic_local_model("hello")
                logger.info("Anchor embedding cache pre-warmed during startup.")
            except Exception:
                logger.debug("Anchor pre-warm failed (non-critical), will lazy-init on first request.")

    def _local_model_ready(self, model_name: str) -> bool:
        import time as _time
        now = _time.time()
        if self._local_ready_cache is not None and now - self._local_ready_cache_time < 60.0:
            return self._local_ready_cache
        try:
            available = self._get_available_models()
            clean_name = model_name.replace("ollama/", "")
            self._local_ready_cache = any(clean_name in m for m in available)
            self._local_ready_cache_time = now
        except Exception:
            self._local_ready_cache = shutil.which("ollama") is not None
        return self._local_ready_cache

    def _provider_model_name(self, model_name: str) -> str:
        return model_name.split("/", 1)[-1]

    def _emit_queue_metrics(self) -> None:
        if self.telemetry is None:
            return
        self.telemetry.set_gauge("provider.queue_depth", float(self._queued_requests))
        self.telemetry.set_gauge("provider.active_requests", float(self._active_requests))
