#!/usr/bin/env bash
# Demo 4: numbers slide. Re-running the eval resumes from var/eval/ (cached per case), so this is cheap
# once the run has finished; the report itself is deterministic.
set -euo pipefail
cd "$(dirname "$0")/.."
N="${N:-300}"; THINK="${THINK:-on}"
uv run python -m eval.run_mcptox --n "$N" --think "$THINK"
uv run python -m eval.report "var/eval/mcptox_heldout_n${N}_think-${THINK}.jsonl"
