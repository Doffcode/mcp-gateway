#!/usr/bin/env bash
# Convert a Gateway Studio recording (WebM) to H.264 MP4 for VLC / PowerPoint.
# Uses the static ffmpeg bundled with imageio-ffmpeg (dev tool only, not a project dependency).
#   scripts/to_mp4.sh var/video/gateway-studio.webm      -> var/video/gateway-studio.mp4
set -euo pipefail
IN="$1"; OUT="${2:-${IN%.*}.mp4}"
FF=$(uv run --with imageio-ffmpeg python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -y -i "$IN" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 -movflags +faststart "$OUT"
echo "wrote $OUT"
