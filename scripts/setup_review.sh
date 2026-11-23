#!/usr/bin/env bash
# Prepare the CPU review demo when the offline runtime is unavailable.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync --locked --extra agent
uv pip install --python .venv/bin/python \
  scikit-learn==1.6.1 numpy==2.5.5 scipy==1.18.1 joblib==1.6.0 threadpoolctl==3.8.0
scripts/fetch_mcptox.sh

if [[ ! -e var/l3/manifest.json && ! -e var/l3/classifier.joblib ]]; then
  OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python -m eval.train_l3 --text-only --device cpu
  printf '%s\n' 'Built a local CPU demo artifact. The archived evaluation used the original frozen artifact.'
fi

.venv/bin/python -c 'from gateway.l3 import Scorer; print("L3 threshold:", Scorer("var/l3").threshold)'
