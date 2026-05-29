from __future__ import annotations

import socket

from modules.web_ui.src import launcher


def test_choose_dashboard_token_prefers_existing() -> None:
    token, generated = launcher.choose_dashboard_token("fixed-token", interactive=False)
    assert token == "fixed-token"
    assert generated is False


def test_choose_dashboard_token_prompts_interactively() -> None:
    token, generated = launcher.choose_dashboard_token(
        None,
        interactive=True,
        prompt_func=lambda _: "prompt-token",
    )
    assert token == "prompt-token"
    assert generated is False


def test_choose_dashboard_token_generates_when_prompt_blank() -> None:
    token, generated = launcher.choose_dashboard_token(
        None,
        interactive=True,
        prompt_func=lambda _: "",
    )
    assert token.startswith("nexus-")
    assert generated is True


def test_find_available_port_skips_blocked_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocked_port = blocker.getsockname()[1]
        blocker.listen(1)
        port = launcher.find_available_port(start_port=blocked_port, attempts=3)
    assert port != blocked_port


def test_build_dashboard_runtime_sets_env_and_uses_fallback_port(tmp_path, monkeypatch) -> None:
    class FakeServer:
        def __init__(self, config) -> None:
            self.config = config

        def run(self) -> None:
            raise AssertionError("run() should not be called in this test")

    class FakeConfig:
        def __init__(self, app, host: str, port: int, log_level: str) -> None:
            self.app = app
            self.host = host
            self.port = port
            self.log_level = log_level

    class FakeUvicorn:
        Config = FakeConfig
        Server = FakeServer

    monkeypatch.setattr(launcher, "import_dashboard_runtime", lambda: (FakeUvicorn, lambda event_store, etd_store, **kwargs: {"ok": True}))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 8088))
        blocker.listen(1)
        runtime = launcher.build_dashboard_runtime(tmp_path, token="abc123", interactive=False)

    assert runtime["port"] != 8000
    assert runtime["token"] == "abc123"
    assert runtime["generated_token"] is False
    assert runtime["url"] == f"http://localhost:{runtime['port']}"


def test_print_dashboard_startup_shows_token_and_url(capsys) -> None:
    launcher.print_dashboard_startup(
        {
            "url": "http://localhost:8001",
            "token": "abc123",
            "generated_token": True,
            "port": 8001,
        }
    )
    out = capsys.readouterr().out
    assert "Dashboard running at http://localhost:8001" in out
    assert "Open: http://localhost:8001?token=abc123" in out
    assert "Token: abc123" in out


def test_start_dashboard_server_runs_server(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    class FakeServer:
        def run(self) -> None:
            calls.append("run")

    monkeypatch.setattr(
        launcher,
        "build_dashboard_runtime",
        lambda *args, **kwargs: {
            "url": "http://localhost:8000",
            "token": "abc123",
            "generated_token": False,
            "port": 8000,
            "server": FakeServer(),
        },
    )

    launcher.start_dashboard_server(tmp_path, interactive=False)
    assert calls == ["run"]
