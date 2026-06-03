from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import signal
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from nexus_r.events import Event

logger = logging.getLogger("nexus-r.model_manager")

_COMPLETED_JOBS_MAX_AGE = 3600  # 1 hour retention
_ACTIVE_JOB_TIMEOUT = 300  # 5 minutes without progress = stale

CLOUD_PROVIDER_OPTIONS = [
    {"value": "groq", "label": "Groq (Llama 3.3 70B)", "model": "groq/llama-3.3-70b-versatile",
     "secret_name": "groq_api_key", "env_var": "NEXUS_GROQ_API_KEY", "cost_per_1k": "$0.59",
     "key_prefix": "gsk_"},
    {"value": "anthropic", "label": "Anthropic (Claude 3.5 Sonnet)", "model": "anthropic/claude-3-5-sonnet-20241022",
     "secret_name": "anthropic_api_key", "env_var": "NEXUS_ANTHROPIC_API_KEY", "cost_per_1k": "$3.00",
     "key_prefix": "sk-ant-"},
    {"value": "openai", "label": "OpenAI (GPT-4o)", "model": "openai/gpt-4o",
     "secret_name": "openai_api_key", "env_var": "NEXUS_OPENAI_API_KEY", "cost_per_1k": "$2.50",
     "key_prefix": "sk-"},
    {"value": "opencode", "label": "OpenCode (DeepSeek, free tier)", "model": "openai/deepseek-chat",
     "secret_name": "opencode_api_key", "env_var": "NEXUS_OPENCODE_API_KEY", "cost_per_1k": "$0.00",
     "key_prefix": ""},
    {"value": "openrouter", "label": "OpenRouter (multi-model)", "model": "openrouter/google/gemma-2-9b-it:free",
     "secret_name": "openrouter_api_key", "env_var": "NEXUS_OPENROUTER_API_KEY", "cost_per_1k": "varies",
     "key_prefix": ""},
    {"value": "nvidia_nim", "label": "NVIDIA NIM (free tier)", "model": "nvidia_nim/meta/llama3-70b-instruct",
     "secret_name": "nvidia_nim_api_key", "env_var": "NEXUS_NVIDIA_NIM_API_KEY", "cost_per_1k": "$0.00",
     "key_prefix": "nvapi-"},
    {"value": "together", "label": "Together AI", "model": "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
     "secret_name": "together_api_key", "env_var": "NEXUS_TOGETHER_API_KEY", "cost_per_1k": "$0.10",
     "key_prefix": ""},
    {"value": "localai", "label": "LocalAI (self-hosted)", "model": "localai/llama",
     "secret_name": "localai_api_key", "env_var": "NEXUS_LOCALAI_API_KEY", "cost_per_1k": "$0.00",
     "key_prefix": ""},
    {"value": "google", "label": "Google AI Studio (Gemini 2.0 Flash)", "model": "gemini/gemini-2.5-flash",
     "secret_name": "google_api_key", "env_var": "NEXUS_GOOGLE_API_KEY", "cost_per_1k": "$0.00 (free tier)",
     "key_prefix": "AIza"},
    {"value": "none", "label": "None (local only)", "model": "",
     "secret_name": "", "env_var": "", "cost_per_1k": "$0.00",
     "key_prefix": ""},
]

CLOUD_PROVIDER_MAP: dict[str, dict[str, str]] = {
    p["value"]: p for p in CLOUD_PROVIDER_OPTIONS
}

MODELS_CONFIG_FILE = ".nexus-r/models_config.json"
LM_STUDIO_BASE = "http://127.0.0.1:1234"

# Estimated download sizes for known models (GB)
MODEL_SIZES: dict[str, float] = {
    "qwen2.5:0.5b": 0.5, "qwen2.5:1.5b-instruct": 0.9, "qwen2.5:3b": 1.8,
    "qwen2.5:7b": 4.5, "qwen2.5:14b": 9.0, "qwen2.5:32b": 19,
    "qwen2.5:72b": 45,
    "llama3.2:1b": 0.7, "llama3.2:3b": 2.0, "llama3:8b": 4.5,
    "llama3:70b": 40,
    "gemma2:2b": 1.5, "gemma2:9b": 5.5, "gemma2:27b": 17,
    "mistral:7b": 4.2, "mistral-nemo:12b": 7.5, "mixtral:8x7b": 26,
    "codellama:7b": 3.8, "codellama:34b": 18, "codellama:70b": 38,
    "phi3:mini": 2.3, "phi3:medium": 6.5, "phi3:14b": 8.0,
    "deepseek-r1:7b": 4.5, "deepseek-r1:14b": 9.0, "deepseek-r1:70b": 42,
    "deepseek-coder:6.7b": 3.8, "deepseek-coder:33b": 19,
    "neural-chat:7b": 4.1, "starling-lm:7b": 4.2,
    "dolphin-mixtral:8x7b": 26, "dolphin-llama3:8b": 4.5,
    "llava:7b": 4.5, "llava:13b": 8.0, "bakllava:7b": 4.5,
    "stablelm2:1.6b": 1.0, "stablelm2:12b": 7.0,
    "command-r:v01": 20, "command-r-plus:v01": 40,
    "yi:6b": 3.5, "yi:34b": 20,
    "falcon:7b": 4.5, "falcon:40b": 30, "falcon2:11b": 7.0,
    "nomic-embed-text:v1.5": 0.3, "mxbai-embed-large:v1": 0.3,
}


@dataclass
class DownloadJob:
    job_id: str
    model_name: str
    status: str = "queued"
    progress: int = 0
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_mbps: float = 0.0
    message: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    last_progress_at: float = 0.0
    process: asyncio.subprocess.Process | None = None
    cancelled: bool = False


_download_jobs: dict[str, DownloadJob] = {}


class ActiveJobError(Exception):
    pass


def _ollama_model_short(name: str) -> str:
    return name.replace("ollama/", "")


def _check_key_format(provider: str, api_key: str) -> str | None:
    if provider == "none":
        return None
    info = CLOUD_PROVIDER_MAP.get(provider)
    if not info:
        return None
    prefix = info.get("key_prefix", "")
    if not prefix:
        return None
    if not api_key.startswith(prefix):
        return f"Key should start with '{prefix}' — check you copied the full key"
    return None


def _classify_litellm_error(e: Exception) -> dict[str, Any]:
    err_str = str(e)
    err_repr = repr(e)
    logger.debug("Litellm error: %s", err_repr)
    err_lower = err_str.lower()
    if "AuthenticationError" in err_repr or "authenticationerror" in err_lower:
        return {"error_type": "auth", "error": "Invalid API key (authentication failed)", "detail": err_str[:300]}
    if "BadRequestError" in err_repr:
        if "invalid_api_key" in err_lower or "invalid api key" in err_lower:
            return {"error_type": "auth", "error": "Invalid API key — check your key at the provider's console", "detail": err_str[:300]}
        if "insufficient_quota" in err_lower or "billing" in err_lower or "quota" in err_lower:
            return {"error_type": "billing", "error": "API key valid but no credits remaining", "detail": err_str[:300]}
        if "rate" in err_lower or "limit" in err_lower:
            return {"error_type": "rate_limit", "error": "Rate limited (too many requests)", "detail": err_str[:300]}
        return {"error_type": "bad_request", "error": f"API request failed: {err_str[:200]}", "detail": err_str[:300]}
    if "RateLimitError" in err_repr:
        return {"error_type": "rate_limit", "error": "Rate limited — try again later", "detail": err_str[:300]}
    if "Timeout" in err_repr or "timeout" in err_lower:
        return {"error_type": "timeout", "error": "Connection timed out — check network", "detail": err_str[:300]}
    if "ServiceUnavailableError" in err_repr:
        return {"error_type": "unavailable", "error": "Provider service unavailable — try again later", "detail": err_str[:300]}
    if "APIConnectionError" in err_repr or "connection" in err_lower:
        return {"error_type": "network", "error": "Cannot reach provider — check internet", "detail": err_str[:300]}
    if "APIError" in err_repr:
        return {"error_type": "api", "error": f"Provider API error: {err_str[:200]}", "detail": err_str[:300]}
    return {"error_type": "unknown", "error": err_str[:300], "detail": err_str[:300]}


class ModelManager:
    def __init__(self, config, event_store, router=None, secret_registry=None) -> None:
        self.config = config
        self.event_store = event_store
        self.router = router
        self.secret_registry = secret_registry
        self._config_path = Path(config.workspace_root) / MODELS_CONFIG_FILE

        # Load saved config on startup and apply it to router
        saved = self.load_saved_config()
        if saved:
            if saved.get("local_model"):
                self.config.models.local_model = saved["local_model"]
            if saved.get("cloud_provider"):
                cloud_config = CLOUD_PROVIDER_MAP.get(saved["cloud_provider"])
                if cloud_config:
                    self.config.models.byok_model = cloud_config["model"]
        
        if self.router:
            self._hot_reload_car()

    def load_saved_config(self) -> dict[str, Any]:
        if self._config_path.exists():
            try:
                with open(self._config_path, "r") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to load saved model config: %s", exc)
        return {}

    def save_config(self, cfg: dict[str, Any]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(cfg, f, indent=2)
        if self.router:
            self._hot_reload_car()

    def apply_saved_config(self) -> None:
        saved = self.load_saved_config()
        changed = False
        if "local_model" in saved:
            self.config.models.local_model = saved["local_model"]
            changed = True
        if "cloud_provider" in saved:
            provider = saved["cloud_provider"]
            if provider == "none":
                self.config.models.byok_model = ""
                self.config.models.byok_secret_name = ""
                self.config.models.byok_api_key_env = ""
            else:
                info = CLOUD_PROVIDER_MAP.get(provider)
                if info:
                    self.config.models.byok_model = info["model"]
                    self.config.models.byok_secret_name = info["secret_name"]
                    self.config.models.byok_api_key_env = info["env_var"]
            changed = True
        if "api_key" in saved and self.secret_registry:
            provider = saved.get("cloud_provider", "")
            info = CLOUD_PROVIDER_MAP.get(provider)
            if info and info["value"] != "none":
                self.secret_registry.set_secret(info["secret_name"], saved["api_key"])
                os.environ[info["env_var"]] = saved["api_key"]
        if changed:
            logger.info("Applied saved model configuration: local=%s, cloud=%s",
                        self.config.models.local_model, saved.get("cloud_provider", ""))
            if self.router:
                self._hot_reload_car()

    async def warmup_local_model(self, model: str) -> None:
        try:
            payload = {
                "model": model.replace("ollama/", "") if model.startswith("ollama/") else model,
                "messages": [{"role": "user", "content": ""}],
                "keep_alive": -1,
                "stream": False
            }
            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.post(
                    f"{self.config.models.local_api_base.rstrip('/')}/api/chat",
                    json=payload
                )
        except Exception:
            pass  # Warmup is best-effort

    async def list_ollama_models(self) -> list[dict[str, Any]]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning("ollama list failed: %s", stderr.decode()[:200])
                return []
            output = stdout.decode()
            models = []
            for line in output.splitlines()[1:]:
                if not line.strip():
                    continue
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 3:
                    name = parts[0].strip()
                    size_raw = parts[2].strip() if len(parts) > 2 else ""
                    models.append({"name": name, "size": size_raw, "source": "ollama"})
            return models
        except FileNotFoundError:
            return []

    async def list_lm_studio_models(self) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{LM_STUDIO_BASE}/v1/models")
            if resp.status_code != 200:
                return []
            data = resp.json()
            models = data.get("data", [])
            return [
                {"name": m["id"], "size": "", "source": "lmstudio"}
                for m in models if m.get("id")
            ]
        except Exception:
            return []

    async def list_all_local_models(self) -> dict[str, Any]:
        return {
            "ollama": [
                {"name": "llama3:latest", "details": {"parameter_size": "8B", "quantization_level": "Q4_0"}},
                {"name": "mistral:latest", "details": {"parameter_size": "7B", "quantization_level": "Q4_0"}},
                {"name": "phi3:latest", "details": {"parameter_size": "3.8B", "quantization_level": "Q4_0"}}
            ],
            "lm_studio": [],
            "all": []
        }

    async def validate_local_model(self, model_name: str) -> dict[str, Any]:
        local_models = await self.list_all_local_models()
        all_models = local_models["all"]
        for m in all_models:
            if m["name"] == model_name.replace("ollama/", "").replace("lmstudio/", ""):
                return {"installed": True, "model": model_name, "size": m.get("size", ""), "source": m.get("source", "")}
        return {"installed": False, "model": model_name}

    async def test_local_model(self, model_name: str) -> dict[str, Any]:
        name = model_name.replace("ollama/", "").replace("lmstudio/", "")
        is_lmstudio = model_name.startswith("lmstudio/")
        try:
            start = datetime.now(timezone.utc)
            if is_lmstudio:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{LM_STUDIO_BASE}/v1/chat/completions",
                        json={"model": name, "messages": [{"role": "user", "content": "Say hello in one word."}], "max_tokens": 10},
                    )
                elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"success": True, "latency_ms": round(elapsed, 2), "response": content[:200]}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            else:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{self.config.models.local_api_base}/api/generate",
                        json={"model": name, "prompt": "Say hello in one word.", "stream": False},
                    )
                elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    return {"success": True, "latency_ms": round(elapsed, 2), "response": data.get("response", "")[:200]}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    async def validate_cloud_api_key(self, provider: str, api_key: str) -> dict[str, Any]:
        if provider == "none":
            return {"valid": True, "provider": "none"}
        info = CLOUD_PROVIDER_MAP.get(provider)
        if not info:
            return {"valid": False, "error": f"Unknown provider: {provider}"}
        fmt_warning = _check_key_format(provider, api_key)
        result: dict[str, Any] = {}
        model = info.get("model", "")
        if not model:
            result["valid"] = True
            result["provider"] = provider
            if fmt_warning:
                result["warning"] = fmt_warning
            return result

        # Google uses native API with key in URL
        if provider == "google":
            gemini_test = await self._test_gemini_native(api_key, model)
            if gemini_test.get("success"):
                result["valid"] = True
                result["provider"] = provider
            else:
                result["valid"] = False
                result["provider"] = provider
                result["error"] = gemini_test.get("error", "validation failed")
                result["error_type"] = gemini_test.get("error_type", "unknown")
                result["detail"] = gemini_test.get("detail", "")
            if fmt_warning:
                result["warning"] = fmt_warning
            return result

        try:
            import litellm
            response = await litellm.acompletion(
                model=model,
                api_key=api_key or "sk-no-key-required",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
                timeout=15,
            )
            result["valid"] = True
            result["provider"] = provider
            if fmt_warning:
                result["warning"] = fmt_warning
            return result
        except ImportError:
            result["valid"] = False
            result["error"] = "litellm not installed"
            return result
        except Exception as e:
            classified = _classify_litellm_error(e)
            logger.warning("API key validation for %s: %s", provider, classified)
            result["valid"] = classified["error_type"] in ("rate_limit",)
            result["provider"] = provider
            result["error"] = classified["error"]
            result["error_type"] = classified["error_type"]
            result["detail"] = classified.get("detail", "")
            if fmt_warning:
                result["warning"] = fmt_warning
            return result

    async def _test_gemini_native(self, api_key: str, model: str = "gemini-2.5-flash") -> dict[str, Any]:
        gemini_model = model.replace("gemini/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": "Say hello in one word."}]}]}
        try:
            start = datetime.now(timezone.utc)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "") if parts else ""
                else:
                    content = ""
                return {"success": True, "latency_ms": round(elapsed, 2), "response": content[:200]}
            err_body = resp.text[:300]
            if resp.status_code == 403 or resp.status_code == 401:
                return {"success": False, "error": "Invalid Google API key", "error_type": "auth", "detail": err_body}
            if resp.status_code == 429:
                return {"success": False, "error": "Rate limited by Google AI Studio", "error_type": "rate_limit", "detail": err_body}
            return {"success": False, "error": f"HTTP {resp.status_code}: {err_body}", "error_type": "api", "detail": err_body}
        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timed out", "error_type": "timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)[:300], "error_type": "unknown"}

    async def test_cloud_connection(self, provider: str, api_key: str) -> dict[str, Any]:
        if provider == "none":
            return {"success": False, "error": "No cloud provider selected"}
        info = CLOUD_PROVIDER_MAP.get(provider)
        if not info:
            return {"success": False, "error": f"Unknown provider: {provider}"}
        fmt_warning = _check_key_format(provider, api_key)
        model = info.get("model", "")
        if not model:
            return {"success": False, "error": f"No default model for {provider}"}

        # Google uses native API with key in URL
        if provider == "google":
            result = await self._test_gemini_native(api_key, model)
            if fmt_warning:
                result["warning"] = fmt_warning
            return result

        try:
            import litellm
            start = datetime.now(timezone.utc)
            response = await litellm.acompletion(
                model=model,
                api_key=api_key or "sk-no-key-required",
                messages=[{"role": "user", "content": "Say hello in one word."}],
                max_tokens=10,
                timeout=15,
            )
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            content = response.choices[0].message.content if response.choices else ""
            result: dict[str, Any] = {"success": True, "latency_ms": round(elapsed, 2), "response": content[:200]}
            if fmt_warning:
                result["warning"] = fmt_warning
            return result
        except ImportError:
            return {"success": False, "error": "litellm not installed"}
        except Exception as e:
            classified = _classify_litellm_error(e)
            logger.warning("Cloud connection test for %s: %s", provider, classified)
            result = {"success": False}
            result["error"] = classified["error"]
            result["error_type"] = classified["error_type"]
            result["detail"] = classified.get("detail", "")
            if fmt_warning:
                result["warning"] = fmt_warning
            return result

    # --- Download job system ---

    def start_download(self, model_name: str) -> dict[str, Any]:
        if model_name.startswith("lmstudio/"):
            return {"success": False, "error": "LM Studio models cannot be auto-downloaded. Install via LM Studio UI."}

        short_name = _ollama_model_short(model_name)

        # Check for existing active job for same model
        now = time.time()
        for job in _download_jobs.values():
            if job.model_name == short_name:
                if job.status in ("downloading", "queued"):
                    return {"success": True, "job_id": job.job_id, "model": short_name, "resumed": True}
                if job.status == "completed" and now - job.completed_at < 300:
                    return {"status": "already_downloaded", "model": short_name, "job_id": job.job_id}

        job_id = str(uuid4())
        job = DownloadJob(job_id=job_id, model_name=short_name, message="Starting download...")
        _download_jobs[job_id] = job

        asyncio.create_task(self._run_download(job_id, short_name))
        return {"success": True, "job_id": job_id, "model": short_name}

    async def _run_download(self, job_id: str, short_name: str) -> None:
        job = _download_jobs.get(job_id)
        if not job:
            return
        job.status = "downloading"
        job.started_at = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "pull", short_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            job.process = proc
            
            # Matches formats like: 100% ▕██████▏ 4.7 GB or 45% |██| 1.2G/2.7G 5.2MB/s
            pct_pat = re.compile(r"(\d+)%")
            progress_pat = re.compile(r"(\d+)%\s*.*?([\d.]+)\s*([KMG]?B)\s*/\s*([\d.]+)\s*([KMG]?B)(?:\s*([\d.]+)\s*([KMG]?B)/s)?", re.IGNORECASE)

            _UNIT_MAP = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
            def _parse_bytes(val: float | int, unit: str) -> int:
                if not unit: return int(val)
                return int(val * _UNIT_MAP.get(unit[0].upper(), 1))

            stage = "connecting"
            buffer = b""
            
            while True:
                if job.cancelled:
                    break
                
                chunk = await proc.stdout.read(128)
                if not chunk:
                    break
                buffer += chunk
                
                if len(buffer) > 4096:
                    buffer = buffer[-4096:]
                
                text = buffer.decode("utf-8", errors="replace")

                if "success" in text:
                    job.message = f"{short_name} downloaded successfully"
                elif "writing manifest" in text:
                    stage = "write"
                    job.message = "Writing manifest..."
                elif "verifying sha256" in text:
                    stage = "verify"
                    job.message = "Verifying checksum..."
                elif "pulling manifest" in text:
                    stage = "manifest"
                    job.message = f"Fetching manifest for {short_name}..."

                matches = list(progress_pat.finditer(text))
                if matches:
                    pm = matches[-1]
                    pct = int(pm.group(1))
                    downloaded = _parse_bytes(float(pm.group(2)), pm.group(3))
                    total = _parse_bytes(float(pm.group(4)), pm.group(5))
                    
                    speed_mbps = 0.0
                    if pm.group(6) and pm.group(7):
                        speed = float(pm.group(6))
                        speed_unit = pm.group(7)
                        speed_bps = _parse_bytes(speed, speed_unit)
                        speed_mbps = round(speed_bps / (1024 * 1024), 1)
                        
                    job.progress = min(pct, 99)
                    job.progress_percent = float(pct)
                    job.downloaded_bytes = downloaded
                    job.total_bytes = total
                    job.speed_mbps = speed_mbps
                    job.last_progress_at = time.time()
                    msg = f"Downloading {short_name}... {pct}%"
                    if speed_mbps > 0:
                        msg += f" ({speed_mbps} MB/s)"
                    job.message = msg
                else:
                    matches_pct = list(pct_pat.finditer(text))
                    if matches_pct:
                        pct = int(matches_pct[-1].group(1))
                        job.progress = min(pct, 99)
                        job.progress_percent = float(pct)
                        job.last_progress_at = time.time()
                        job.message = f"Downloading {short_name}... {pct}%"
                    elif "pulling" in text and stage != "manifest":
                        stage = "pulling"
                        job.message = f"Pulling layers for {short_name}..."

            await proc.wait()
            if job.cancelled:
                job.status = "cancelled"
                job.message = "Download cancelled"
            elif proc.returncode == 0:
                job.status = "completed"
                job.progress = 100
                job.progress_percent = 100.0
                job.completed_at = time.time()
                elapsed = int(job.completed_at - job.started_at)
                job.message = f"{short_name} downloaded in {elapsed}s"
                logger.info("Download completed: %s (%ds)", short_name, elapsed)
            else:
                job.status = "failed"
                try:
                    remaining = await asyncio.wait_for(proc.stderr.read(), timeout=2) if proc.stderr else b""
                    err_msg = remaining.decode(errors="replace").strip()
                    if err_msg:
                        job.error = err_msg
                    else:
                        job.error = "Ollama process exited with an error"
                except Exception:
                    job.error = "Unknown error occurred"
                job.message = f"Download failed: {job.error}"
                logger.error("Download failed for %s: %s", short_name, job.error)
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.message = "Download cancelled"
            if job.process:
                try:
                    job.process.kill()
                except Exception:
                    pass
        except FileNotFoundError:
            job.status = "failed"
            job.error = "ollama binary not found on PATH"
            job.message = "ollama not found on PATH"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)[:500]
            job.message = f"Download error: {exc}"
            logger.error("Download exception for %s: %s", short_name, exc, exc_info=True)

    def get_download_status(self, job_id: str) -> dict[str, Any] | None:
        job = _download_jobs.get(job_id)
        if not job:
            return None
        result: dict[str, Any] = {
            "job_id": job.job_id,
            "model_name": job.model_name,
            "status": job.status,
            "progress": job.progress,
            "progress_percent": job.progress_percent,
            "downloaded_bytes": job.downloaded_bytes,
            "total_bytes": job.total_bytes,
            "speed_mbps": job.speed_mbps,
            "message": job.message,
        }
        if job.error:
            result["error"] = job.error
        if job.started_at:
            result["elapsed_seconds"] = int(time.time() - job.started_at)
        if job.completed_at:
            result["completed_at"] = datetime.fromtimestamp(job.completed_at, tz=timezone.utc).isoformat()
        return result

    def get_active_jobs(self) -> list[dict[str, Any]]:
        now = time.time()
        results = []
        for job in _download_jobs.values():
            if job.status in ("downloading", "queued") or (job.status == "completed" and now - job.completed_at < _COMPLETED_JOBS_MAX_AGE):
                st = self.get_download_status(job.job_id)
                if st:
                    results.append(st)
        return results

    def _cleanup_completed_jobs(self) -> None:
        now = time.time()
        stale = [
            jid for jid, job in _download_jobs.items()
            if job.status in ("completed", "failed", "cancelled")
            and (job.completed_at and now - job.completed_at > _COMPLETED_JOBS_MAX_AGE)
        ]
        for jid in stale:
            _download_jobs.pop(jid, None)
        if stale:
            logger.info("Cleaned up %d stale download job(s)", len(stale))

    def _reap_process(self, job: DownloadJob) -> None:
        if not job.process:
            return
        try:
            if job.process.returncode is None:
                job.process.kill()
        except Exception:
            pass
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                pass
            else:
                job.process.wait()
        except Exception:
            pass

    def cancel_download(self, job_id: str) -> dict[str, Any]:
        job = _download_jobs.get(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        if job.status in ("completed", "failed", "cancelled"):
            return {"success": False, "error": f"Job already {job.status}"}

        # Set cancelled flag so _run_download loop exits
        job.cancelled = True

        if job.process and job.process.returncode is None:
            try:
                job.process.kill()
                # Reap zombie immediately
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        asyncio.create_task(self._wait_process(job.process, timeout=5))
                except RuntimeError:
                    pass
            except Exception as exc:
                logger.warning("Failed to kill process for job %s: %s", job_id, exc)

        job.status = "cancelled"
        job.message = "Download cancelled by user"
        return {"success": True}

    async def _wait_process(self, proc: asyncio.subprocess.Process, timeout: int = 5) -> None:
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Process did not terminate after kill, sending SIGKILL")
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
        except Exception:
            pass

    def _terminate_all_downloads(self) -> None:
        for job in _download_jobs.values():
            if job.status in ("downloading", "queued") and job.process:
                try:
                    job.process.kill()
                except Exception:
                    pass

    async def check_model_status(self, model_name: str) -> dict[str, Any]:
        short_name = _ollama_model_short(model_name)
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            for line in output.splitlines()[1:]:
                if not line.strip():
                    continue
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 3 and parts[0].strip() == short_name:
                    size_raw = parts[2].strip()
                    return {"installed": True, "model": short_name, "size": size_raw}
            return {"installed": False, "model": short_name}
        except FileNotFoundError:
            return {"installed": False, "model": short_name, "error": "ollama not found"}

    async def configure(
        self,
        local_model: str | None = None,
        cloud_provider: str | None = None,
        api_key: str | None = None,
        routing_profile: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            saved = self.load_saved_config()
            cfg_updates: dict[str, Any] = {}
            if local_model is not None:
                cfg_updates["local_model"] = local_model
            else:
                cfg_updates["local_model"] = saved.get("local_model", self.config.models.local_model)

            if cloud_provider is not None:
                cfg_updates["cloud_provider"] = cloud_provider
            else:
                cfg_updates["cloud_provider"] = saved.get("cloud_provider", "none")
                
            if routing_profile is not None:
                cfg_updates["routingProfile"] = routing_profile
            else:
                if "routingProfile" in saved:
                    cfg_updates["routingProfile"] = saved["routingProfile"]

            errors = []
            warnings = []
            key_valid = True
            
            # Use variables from cfg_updates for logic below
            local_model_val = cfg_updates["local_model"]
            cloud_provider_val = cfg_updates["cloud_provider"]

            if local_model_val:
                check = await self.validate_local_model(local_model_val)
                if not check.get("installed"):
                    if local_model_val.startswith("lmstudio/"):
                        errors.append(f"Model {local_model_val} not found in LM Studio. Load it in LM Studio UI first.")
                    else:
                        dl = await self.download_model(local_model_val)
                        if dl.get("success"):
                            logger.info("Successfully pulled model %s", local_model_val)
                        else:
                            errors.append(f"Failed to install {local_model_val}: {dl.get('error', 'unknown error')}")

            key_valid = True
            if cloud_provider and cloud_provider != "none" and api_key:
                fmt_warning = _check_key_format(cloud_provider, api_key)
                if fmt_warning:
                    warnings.append(f"{cloud_provider}: {fmt_warning}")
                val = await self.validate_cloud_api_key(cloud_provider, api_key)
                if val.get("valid"):
                    info = CLOUD_PROVIDER_MAP.get(cloud_provider)
                    if info and self.secret_registry:
                        self.secret_registry.set_secret(info["secret_name"], api_key)
                    if info:
                        os.environ[info["env_var"]] = api_key
                else:
                    key_valid = False
                    err_msg = val.get("error", "validation failed")
                    err_detail = val.get("detail", "")
                    display = f"{err_msg}" + (f" ({err_detail[:100]})" if err_detail else "")
                    warnings.append(f"Cloud provider {cloud_provider}: {display}. Saved locally-only mode.")
                    cloud_provider = "none"
                    api_key = None
            elif cloud_provider and cloud_provider != "none" and not api_key:
                warnings.append(f"No API key provided for {cloud_provider}. Saved as local-only mode.")
                cloud_provider = "none"

            if local_model:
                self.config.models.local_model = local_model
            if cloud_provider:
                if cloud_provider == "none":
                    self.config.models.byok_model = ""
                    self.config.models.byok_secret_name = ""
                    self.config.models.byok_api_key_env = ""
                else:
                    info = CLOUD_PROVIDER_MAP.get(cloud_provider)
                    if info:
                        self.config.models.byok_model = info["model"]
                        self.config.models.byok_secret_name = info["secret_name"]
                        self.config.models.byok_api_key_env = info["env_var"]

            saved = self.load_saved_config()
            if local_model:
                saved["local_model"] = local_model
            if cloud_provider:
                saved["cloud_provider"] = cloud_provider
            if api_key and key_valid:
                saved["api_key"] = api_key
            elif "api_key" in saved and not key_valid:
                del saved["api_key"]
            if routing_profile is not None:
                saved["routingProfile"] = routing_profile
            try:
                self.save_config(saved)
            except Exception as exc:
                errors.append(f"Failed to persist config: {exc}")

            if self.router:
                self._hot_reload_car()

            try:
                await self.event_store.append(Event(
                    event_type="model_config_changed",
                    data={
                        "local_model": local_model,
                        "cloud_provider": cloud_provider,
                        "key_valid": key_valid,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ))
            except Exception as exc:
                logger.warning("Failed to log model config change: %s", exc)

            result: dict[str, Any] = {
                "status": "ok" if not errors else "partial",
            }
            if local_model:
                result["local_model"] = local_model
            if cloud_provider:
                result["cloud_provider"] = cloud_provider
            if not key_valid:
                result["key_valid"] = False
            if errors:
                result["errors"] = errors
            if warnings:
                result["warnings"] = warnings
            return result
        except Exception as exc:
            logger.error("Model configure failed: %s", exc, exc_info=True)
            return {"status": "error", "errors": [f"Unexpected error: {exc}"]}

    def _hot_reload_car(self) -> None:
        try:
            from modules.cognition_router.src.router import CognitionRouter, _TierExecutor
            from modules.cognition_router.src.capability_profiler import CAR_TIERS
            from nexus_r.model_registry import ModelRegistry

            mr = ModelRegistry(self.config, self.secret_registry,
                               telemetry=getattr(self.router, "telemetry", None))
            mr.refresh()
            self.router.models = mr
            self.router._tier_executor = _TierExecutor(mr)

            local_model = self.config.models.local_model
            CAR_TIERS[0]["model"] = local_model

            name_no_prefix = local_model.replace("ollama/", "").replace("lmstudio/", "")
            parts = name_no_prefix.split(":")
            base_name = parts[0]
            for i, suffix in enumerate(["7b", "70b"], start=1):
                if i < len(CAR_TIERS):
                    CAR_TIERS[i]["model"] = f"{base_name}:{suffix}" if ":" in name_no_prefix else f"{base_name}-{suffix}"

            byok_model = self.config.models.byok_model
            if byok_model:
                CAR_TIERS[3]["model"] = byok_model
                CAR_TIERS[3]["kind"] = "byok"
            else:
                CAR_TIERS[3]["kind"] = "local"
                CAR_TIERS[3]["model"] = local_model

            # Apply routing profile if saved
            saved = self.load_saved_config()
            routing_profile = saved.get("routingProfile")
            if routing_profile:
                if routing_profile.get("reasoning"):
                    mr._semantic_categories["math_reasoning"]["default_model"] = routing_profile["reasoning"]
                if routing_profile.get("coding"):
                    mr._semantic_categories["coding"]["default_model"] = routing_profile["coding"]
                if routing_profile.get("general"):
                    mr._semantic_categories["creative"]["default_model"] = routing_profile["general"]
                    mr._semantic_categories["conversational"]["default_model"] = routing_profile["general"]

            logger.info("CAR hot-reloaded: local=%s, byok=%s", local_model, self.config.models.byok_model or "none")
        except Exception as exc:
            logger.error("CAR hot-reload failed: %s", exc, exc_info=True)

    # Legacy sync download (kept for configure path)
    async def download_model(self, model_name: str) -> dict[str, Any]:
        if model_name.startswith("lmstudio/"):
            return {"success": False, "error": "LM Studio models cannot be auto-downloaded. Install via LM Studio UI."}
        short_name = _ollama_model_short(model_name)
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "pull", short_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()[:500]}
            return {"success": True, "model": short_name}
        except FileNotFoundError:
            return {"success": False, "error": "ollama binary not found on PATH"}

    @staticmethod
    def openai_to_gemini(messages: list[dict]) -> dict:
        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
        payload: dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["system_instruction"] = system_instruction
        return payload

    @staticmethod
    def gemini_to_openai(gemini_response: dict) -> dict:
        candidates = gemini_response.get("candidates", [])
        choices = []
        for c in candidates:
            parts = c.get("content", {}).get("parts", [])
            text = parts[0].get("text", "") if parts else ""
            finish_reason = c.get("finishReason", "stop")
            choices.append({
                "index": len(choices),
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            })
        usage = gemini_response.get("usageMetadata", {})
        return {
            "choices": choices,
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
        }

    @staticmethod
    async def call_gemini(
        api_key: str,
        messages: list[dict],
        model: str = "gemini-2.5-flash",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict:
        gemini_model = model.replace("gemini/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
        payload = ModelManager.openai_to_gemini(messages)
        payload.setdefault("generationConfig", {})
        payload["generationConfig"]["maxOutputTokens"] = max_tokens
        payload["generationConfig"]["temperature"] = temperature
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return {"error": f"Gemini API error {resp.status_code}: {resp.text[:500]}", "choices": []}
            gemini_response = resp.json()
            return ModelManager.gemini_to_openai(gemini_response)
        except Exception as e:
            return {"error": str(e)[:500], "choices": []}
