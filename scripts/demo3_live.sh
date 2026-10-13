#!/usr/bin/env bash
# Demo 3: live before/after with a local model (Ollama, qwen3:8b). LLM behaviour is non-deterministic.
#   scripts/demo3_live.sh            one run gateway OFF, then one run gateway ON (seed 0), full transcript
#   scripts/demo3_live.sh 10         10 runs per mode, summary table
# Backup recording of a 10x10 run: recordings/demo3/terminal_10x10.log (+ transcripts/*.json)
set -euo pipefail
cd "$(dirname "$0")/.."
RUNS="${1:-1}"
uv run python -m agent.loop --gateway both --runs "$RUNS" 2>/dev/null
