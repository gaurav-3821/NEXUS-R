from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.web_ui.src.launcher import DashboardLauncherError, start_dashboard_server


def main() -> int:
    try:
        start_dashboard_server(ROOT)
    except DashboardLauncherError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
