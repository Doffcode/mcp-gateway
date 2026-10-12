#!/usr/bin/env bash
# One-shot setup on any machine (laptop or lab PC): identical env from uv.lock + data fetch.
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --all-extras
scripts/fetch_mcptox.sh
if command -v ollama >/dev/null; then
  MODEL="${GATEWAY_MODEL:-}"
  [ -n "$MODEL" ] && ollama pull "$MODEL" || echo "ollama found; set GATEWAY_MODEL to pull the agent model (Day 2)"
else
  echo "ollama not installed: needed only for Demo 3/4"
fi
