from __future__ import annotations

import os
import secrets
import socket
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.state_core.src.event_store import EventStore
from modules.workflow_engine.src.store import ETDStore


class DashboardLauncherError(RuntimeError):
    """Raised when the dashboard launcher cannot start the server."""


def import_dashboard_runtime():
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise DashboardLauncherError(_missing_dependency_message(exc.name or "uvicorn")) from exc

    try:
        from modules.web_ui.src.app import create_app
    except ModuleNotFoundError as exc:
        missing = exc.name or "fastapi"
        if missing.startswith("fastapi") or missing.startswith("starlette"):
            raise DashboardLauncherError(_missing_dependency_message(missing)) from exc
        raise

    return uvicorn, create_app


def choose_dashboard_token(
    existing_token: str | None = None,
    *,
    interactive: bool | None = None,
    prompt_func: Callable[[str], str] = input,
) -> tuple[str, bool]:
    if existing_token:
        return existing_token, False

    if interactive is None:
        interactive = sys.stdin.isatty()

    if interactive:
        response = prompt_func(
            "NEXUS_DASHBOARD_TOKEN is not set. Enter a token or press Enter to use a generated temporary token: "
        ).strip()
        if response:
            return response, False

    generated = f"nexus-{secrets.token_urlsafe(12)}"

    # Persist token to .nexus_token file
    try:
        token_path = Path(os.getcwd()) / ".nexus_token"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(generated)
    except Exception as exc:
        import logging
        logging.getLogger("nexus-r.dashboard").warning("Could not persist token to .nexus_token: %s", exc)

    return generated, True


def find_available_port(host: str = "127.0.0.1", start_port: int = 8000, attempts: int = 10) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise DashboardLauncherError(
        f"Could not bind dashboard to ports {start_port}-{start_port + attempts - 1}. "
        "Close the conflicting process or specify a different port."
    )


def build_dashboard_runtime(
    workspace: str | Path,
    *,
    host: str = "127.0.0.1",
    start_port: int = 8000,
    token: str | None = None,
    interactive: bool | None = None,
    prompt_func: Callable[[str], str] = input,
) -> dict[str, object]:
    selected_token, generated = choose_dashboard_token(
        token or os.environ.get("NEXUS_DASHBOARD_TOKEN", ""),
        interactive=interactive,
        prompt_func=prompt_func,
    )
    os.environ["NEXUS_DASHBOARD_TOKEN"] = selected_token

    config = NEXUSConfig.from_env(workspace)
    event_store = EventStore(config.database.path)
    etd_store = ETDStore()
    port = find_available_port(host=host, start_port=start_port)
    uvicorn, create_app = import_dashboard_runtime()
    app = create_app(event_store, etd_store, config=config)
    server_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    url = f"http://{host if host != '127.0.0.1' else 'localhost'}:{port}"
    return {
        "config": config,
        "event_store": event_store,
        "server": server,
        "port": port,
        "host": host,
        "url": url,
        "token": selected_token,
        "generated_token": generated,
    }


def print_dashboard_startup(runtime: dict[str, object]) -> None:
    url = str(runtime["url"])
    token = str(runtime["token"])
    generated = bool(runtime["generated_token"])
    port = int(runtime["port"])

    if port != 8000:
        print(f"Port 8000 is unavailable. Using port {port}.")

    if generated:
        print("NEXUS_DASHBOARD_TOKEN was not set. Generated a temporary token for this session.")

    print(f"Dashboard running at {url}")
    print(f"Open: {url}?token={token}")
    print(f"Token: {token}")
    print("Press Ctrl+C to stop the server.")


def start_dashboard_server(
    workspace: str | Path,
    *,
    host: str = "127.0.0.1",
    start_port: int = 8000,
    token: str | None = None,
    interactive: bool | None = None,
    prompt_func: Callable[[str], str] = input,
) -> None:
    from foundation.nexus_r.backend_manager import BackendManager
    try:
        import json
        print(f"[NEXUS_LIFECYCLE] {json.dumps({'event_type': 'backend_init', 'data': {'status': 'Starting model engine'}})}", flush=True)
        BackendManager.get_instance().start(wait_ready=True)
        print(f"[NEXUS_LIFECYCLE] {json.dumps({'event_type': 'backend_ready', 'data': {'status': 'Model engine healthy'}})}", flush=True)
    except Exception as exc:
        import json
        print(f"[NEXUS_LIFECYCLE] {json.dumps({'event_type': 'backend_fatal_error', 'data': {'error': str(exc)}})}", flush=True)
        raise DashboardLauncherError(f"Failed to start Ollama backend: {exc}") from exc

    runtime = build_dashboard_runtime(
        workspace,
        host=host,
        start_port=start_port,
        token=token,
        interactive=interactive,
        prompt_func=prompt_func,
    )
    print_dashboard_startup(runtime)
    server = runtime["server"]
    assert hasattr(server, "run")
    server.run()


def _missing_dependency_message(package_name: str) -> str:
    return (
        f"Missing dashboard dependency '{package_name}'.\n"
        "Install dashboard dependencies with:\n"
        "  .\\.venv\\Scripts\\python.exe -m pip install fastapi uvicorn\n"
        "If 'python' is not recognized on Windows, try:\n"
        "  py -m pip install fastapi uvicorn"
    )
