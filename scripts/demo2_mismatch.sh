#!/usr/bin/env bash
# Demo 2: L2 capability mismatch. Deterministic: no LLM, no network.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/demo2_mismatch.py 2>/dev/null
