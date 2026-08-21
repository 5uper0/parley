#!/usr/bin/env bash
# Builds the full parleyprotocol.com tree: the Astro landing page at the root, the static
# demo at /demo/. Two independent static builds merged into one Cloudflare Pages deploy tree
# (Pages replaces the whole tree on deploy, so both must ship together every time).
#
# Usage: scripts/build-site.sh [out_dir]   (default: build/site)
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-build/site}"
DEMO_RAW="build/.demo-raw"
PY="python3"; [ -x .venv/bin/python ] && PY=".venv/bin/python"

rm -rf "$OUT" "$DEMO_RAW"
mkdir -p "$OUT"

echo "▸ building demo (examples/demo/) -> $DEMO_RAW"
PARLEY_GA4_ID="${PARLEY_GA4_ID:-}" "$PY" scripts/build-static-demo.py "$DEMO_RAW"

echo "▸ rewriting demo's root-absolute API/SEO paths for the /demo/ subpath"
python3 - "$DEMO_RAW/index.html" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
text = text.replace("fetch('/api/recipes.json')", "fetch('/demo/api/recipes.json')")
text = text.replace("fetch('/api/run/'", "fetch('/demo/api/run/'")
text = text.replace('href="https://parleyprotocol.com/"', 'href="https://parleyprotocol.com/demo/"')
text = text.replace('content="https://parleyprotocol.com/"', 'content="https://parleyprotocol.com/demo/"')
text = text.replace('"url":"https://parleyprotocol.com/"', '"url":"https://parleyprotocol.com/demo/"')
text = text.replace('content="https://parleyprotocol.com/og-card-demo.png"', 'content="https://parleyprotocol.com/demo/og-card-demo.png"')
open(path, "w", encoding="utf-8").write(text)
PY

echo "▸ building landing (landing/) -> landing/dist"
( cd landing && npm run build --silent )

echo "▸ merging: landing/dist -> $OUT (root), $DEMO_RAW -> $OUT/demo"
cp -r landing/dist/. "$OUT/"
mkdir -p "$OUT/demo"
cp -r "$DEMO_RAW/." "$OUT/demo/"
rm -rf "$DEMO_RAW"

test -f "$OUT/index.html" || { echo "missing $OUT/index.html" >&2; exit 1; }
test -f "$OUT/demo/index.html" || { echo "missing $OUT/demo/index.html" >&2; exit 1; }
test -f "$OUT/privacy.html" || { echo "missing $OUT/privacy.html" >&2; exit 1; }
grep -q "/demo/api/recipes.json" "$OUT/demo/index.html" || { echo "demo API paths were not rewritten" >&2; exit 1; }

echo "✓ built $OUT (landing at /, demo at /demo/)"
