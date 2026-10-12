#!/usr/bin/env bash
# Fetch MCPTox (arXiv:2508.14925) at a pinned upstream commit and verify checksums.
# Raw data is not committed: the upstream repo has no explicit license.
set -euo pipefail
cd "$(dirname "$0")/.."
COMMIT=f85189f9ad12504c197c7f920ab818a40657b1fa
BASE=https://raw.githubusercontent.com/zhiqiangwang4/MCPTox-Benchmark/$COMMIT
mkdir -p data/raw
for f in response_all.json pure_tool.json; do
  [ -f "data/raw/$f" ] || curl -fsSL "$BASE/$f" -o "data/raw/$f"
done
sha256sum -c - <<SUMS
79a90049be931c59e71446d6180b1d7f0d196d123d08a59bc155d142b5041c03  data/raw/response_all.json
54b1eb0e9d7b2f18465266aa9d9dfda828cd558b1269b74731ec2c5d8579e617  data/raw/pure_tool.json
SUMS
