from __future__ import annotations

"""
Provider Interruption — Phase C failure validation.
Runs comprehensive provider chaos scenarios via scripts/phase_c_validation.py
See: RUNTIME STABILITY — T1 Provider Chaos
"""

import subprocess
import sys
from pathlib import Path


def test_provider_chaos_validation() -> None:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[2] / "scripts" / "phase_c_validation.py")],
        capture_output=True, text=True, timeout=300,
    )
    assert "CRITICAL: 0" in result.stdout, f"Phase C validation failed:\n{result.stdout[-500:]}"
