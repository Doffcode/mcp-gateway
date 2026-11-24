#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x .review-runtime/python/bin/python3.12 ]]; then
  review_python=.review-runtime/python/bin/python3.12
elif [[ -x .venv/bin/python ]]; then
  review_python=.venv/bin/python
else
  printf '%s\n' 'Extract the private review assets or run scripts/setup_review.sh first.' >&2
  exit 1
fi

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
export PYTHONDONTWRITEBYTECODE=1
printf 'Open http://127.0.0.1:%s/lab. For the walkthrough, select only Weather, then Connect servers.\n' "${STUDIO_PORT:-8765}"
exec "$review_python" -m demo_ui.server
