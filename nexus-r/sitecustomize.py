from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FOUNDATION = ROOT / "foundation"

if FOUNDATION.exists():
    foundation_path = str(FOUNDATION)
    if foundation_path not in sys.path:
        sys.path.insert(0, foundation_path)
