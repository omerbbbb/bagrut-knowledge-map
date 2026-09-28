#!/usr/bin/env bash
# Capture a screenshot of each page with a headless Chromium-family browser.
# Pages 2-4 open with #demo, which runs a simulated student to the summary.
# Usage: docs/screenshots/capture.sh   (or: make screenshots)
set -euo pipefail
cd "$(dirname "$0")/../.."

BROWSER="${BROWSER:-}"
if [ -z "$BROWSER" ]; then
  for c in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
    "$(command -v chromium || true)" "$(command -v google-chrome || true)"; do
    if [ -n "$c" ] && [ -x "$c" ]; then BROWSER="$c"; break; fi
  done
fi
if [ -z "$BROWSER" ]; then
  echo "No Chrome/Chromium/Edge found. Set BROWSER=/path/to/chrome, or open web/*.html and capture by hand." >&2
  exit 1
fi

shoot() { # page, hash, output, height
  "$BROWSER" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1440,"$4" --virtual-time-budget=3000 \
    --screenshot="$PWD/docs/screenshots/$3" "file://$PWD/web/$1$2" >/dev/null 2>&1
  echo "→ docs/screenshots/$3"
}
shoot map.html "" map.png 1500
shoot diagnostic_static.html "#demo" diagnostic_static.png 1900
shoot diagnostic_adaptive.html "#demo" diagnostic_adaptive.png 1700
shoot journey.html "" journey_stage1.png 1500
shoot journey.html "#demo" journey.png 2400
shoot guided.html "#section=ד" guided.png 1600
shoot guided.html "#section=ד&teacher=1" guided_teacher.png 1600
