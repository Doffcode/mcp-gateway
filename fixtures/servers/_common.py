"""Shared paths for fixture servers. Fixtures are local test doubles only."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = Path(os.environ.get("GATEWAY_SANDBOX", ROOT / "fixtures" / "sandbox")).resolve()
VAR = Path(os.environ.get("GATEWAY_VAR", ROOT / "var")).resolve()
