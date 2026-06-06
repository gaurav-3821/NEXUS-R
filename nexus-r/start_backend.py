"""Start the NEXUS-R dashboard server (lightweight mode — no BackendManager)."""
import os, sys, secrets
sys.path.insert(0, os.getcwd())
from pathlib import Path
from nexus_r.config import NEXUSConfig
from modules.state_core.src.event_store import EventStore
from modules.workflow_engine.src.store import ETDStore
from modules.web_ui.src.app import create_app
import uvicorn

token = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
if not token:
    try:
        token = Path(".nexus_token").read_text().strip()
    except FileNotFoundError:
        token = f"nexus-{secrets.token_urlsafe(12)}"
        Path(".nexus_token").write_text(token)
os.environ["NEXUS_DASHBOARD_TOKEN"] = token

workspace = Path(os.getcwd())
config = NEXUSConfig.from_env(workspace)
event_store = EventStore(config.database.path)
etd_store = ETDStore()
app = create_app(event_store, etd_store, config=config)

print(f"[NEXUS] Dashboard starting at http://localhost:8000")
print(f"[NEXUS] Token: {token}")
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
