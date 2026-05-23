from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("alpha\nbeta\nhello world\n", encoding="utf-8")
    return tmp_path
