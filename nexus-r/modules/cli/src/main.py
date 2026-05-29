from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
from pathlib import Path
import sys

import typer

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.web_ui.src.launcher import DashboardLauncherError, start_dashboard_server


app = typer.Typer(help="NEXUS-R Phase 1 CLI")
dashboard_app = typer.Typer(help="Dashboard commands.")
app.add_typer(dashboard_app, name="dashboard")


def build_orchestrator(workspace: str) -> MainOrchestrator:
    config = NEXUSConfig.from_env(workspace)
    return MainOrchestrator(config)


async def _run_task_command(task: str, workspace: str) -> dict[str, object]:
    orchestrator = build_orchestrator(workspace)
    try:
        return await orchestrator.run_task(task)
    finally:
        await orchestrator.close()


async def _run_history_command(workspace: str) -> list[dict[str, object]]:
    orchestrator = build_orchestrator(workspace)
    try:
        return await orchestrator.get_history()
    finally:
        await orchestrator.close()


async def _run_cost_command(workspace: str) -> dict[str, object]:
    orchestrator = build_orchestrator(workspace)
    try:
        return await orchestrator.get_cost_summary()
    finally:
        await orchestrator.close()


@app.command()
def run(task: str, workspace: str = typer.Option(str(ROOT), help="Workspace root.")) -> None:
    result = asyncio.run(_run_task_command(task, workspace))
    print(json.dumps(result, indent=2, default=str))
    raise typer.Exit(code=0 if result["success"] else 1)


@app.command()
def history(workspace: str = typer.Option(str(ROOT), help="Workspace root.")) -> None:
    result = asyncio.run(_run_history_command(workspace))
    print(json.dumps(result, indent=2, default=str))


@app.command()
def cost(workspace: str = typer.Option(str(ROOT), help="Workspace root.")) -> None:
    result = asyncio.run(_run_cost_command(workspace))
    print(json.dumps(result, indent=2, default=str))


@app.command()
def config(workspace: str = typer.Option(str(ROOT), help="Workspace root.")) -> None:
    orchestrator = build_orchestrator(workspace)
    print(json.dumps(orchestrator.get_config(), indent=2, default=str))


@dashboard_app.command("start")
def dashboard_start(
    workspace: str = typer.Option(str(ROOT), help="Workspace root."),
    host: str = typer.Option("127.0.0.1", help="Host interface to bind."),
    port: int = typer.Option(8000, help="Preferred starting port."),
    token: str | None = typer.Option(None, help="Dashboard auth token. Defaults to NEXUS_DASHBOARD_TOKEN."),
) -> None:
    try:
        start_dashboard_server(workspace, host=host, start_port=port, token=token)
    except DashboardLauncherError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
