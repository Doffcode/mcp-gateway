#!/usr/bin/env bash
# Demo 1: L1 rug-pull catch. Deterministic: no LLM, no network.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/demo1_rugpull.py
