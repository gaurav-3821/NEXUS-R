from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSettings(BaseModel):
    local_model: str = "ollama/qwen2.5:1.5b-instruct"
    local_fallback_model: str = "mock-local"
    byok_model: str = "groq/llama-3.3-70b-versatile"
    byok_fallback_model: str = "mock-byok"
    local_api_base: str = "http://127.0.0.1:11434"
    local_cost_per_call: float = 0.001
    byok_cost_per_call: float = 0.02
    complexity_threshold: float = 0.65
    byok_api_key_env: str = "NEXUS_BYOK_API_KEY"
    byok_secret_name: str = "groq_api_key"
    provider_timeout_seconds: int = 120
    stream_timeout_seconds: int = 120
    provider_max_concurrency: int = 4
    mock_latency_ms: int = 175
    mock_response_prefix: str = "Mock provider response:"
    enable_mock_fallbacks: bool = True


class SandboxSettings(BaseModel):
    allowed_commands: list[str] = Field(
        default_factory=lambda: ["dir", "ls", "pwd", "type", "echo"]
    )
    command_timeout_seconds: int = 15
    use_docker_if_available: bool = False


class DatabaseSettings(BaseModel):
    path: Path
    compact_after_days: int = 30
    sqlite_cache_size_mb: int = 50


class ObservabilitySettings(BaseModel):
    enabled: bool = True
    log_path: Path


class NEXUSConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    workspace_root: Path
    database: DatabaseSettings
    observability: ObservabilitySettings
    models: ModelSettings = Field(default_factory=ModelSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    app_name: str = "nexus-r"

    @classmethod
    def default(cls, workspace_root: str | Path) -> "NEXUSConfig":
        root = Path(workspace_root).resolve()
        state_dir = root / ".nexus-r"
        state_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            workspace_root=root,
            database=DatabaseSettings(path=state_dir / "events.sqlite3"),
            observability=ObservabilitySettings(log_path=state_dir / "runtime.log"),
        )

    @classmethod
    def from_env(cls, workspace_root: str | Path | None = None) -> "NEXUSConfig":
        if workspace_root is None:
            base = Path.cwd()
        else:
            base = Path(workspace_root)
        root = base.resolve()
        state_dir = root / ".nexus-r"
        state_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            workspace_root=root,
            database=DatabaseSettings(path=state_dir / "events.sqlite3"),
            observability=ObservabilitySettings(log_path=state_dir / "runtime.log"),
        )

    def redacted_dict(self) -> dict[str, object]:
        data = self.model_dump(mode="json")
        data["workspace_root"] = str(self.workspace_root)
        data["database"]["path"] = str(self.database.path)
        data["observability"]["log_path"] = str(self.observability.log_path)
        data["models"]["byok_api_key_env"] = f"{self.models.byok_api_key_env} (lookup only)"
        return data
