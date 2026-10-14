#!/usr/bin/env bash
# Gateway Lab (/lab, default) and Story mode (/): demo UI driven by the real gateway. STUDIO_PAGE= opens Story mode.
#   scripts/demo_ui.sh                 present mode (→/Space next, A auto-play, R record)
# Scene 2 (live agent) needs Ollama + the model in config.local.yaml; every other scene needs no model.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${STUDIO_PORT:-8765}"
uv run --extra agent python -m demo_ui.server &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 50); do curl -s "http://127.0.0.1:$PORT/" >/dev/null && break; sleep 0.2; done
URL="http://127.0.0.1:$PORT/${STUDIO_PAGE:-lab}"
if command -v google-chrome >/dev/null; then google-chrome --app="$URL" --start-fullscreen >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null; then xdg-open "$URL"; else echo "open $URL"; fi
wait $SERVER
