#!/usr/bin/env bash
# roadmap-reality-check.sh — does every file the ROADMAP names as a concrete next
# engineering step actually exist? Added by /retro 2026-09-05.
#
# Why this exists. On 2026-09-05 examples/real_decision.py was found missing from every
# branch. The ROADMAP had named it as a concrete next step since Exp 1 was written, and
# parley/ratify.py had been sitting unmerged for a day with the note "no consumers" —
# because its consumer was the file that did not exist. Meanwhile six consecutive retro
# cycles scored the project "0/4, blocked on the operator" and the week-32-36 retro wrote
# that the remaining Exp 1 steps were "reasonable" to defer because "Exp 1's gate already
# closed via dogfood-02".
#
# Two different failures stacked:
#   1. ROADMAP stated two different gates for Exp 1 — the step line said "≥1 'this is
#      better because…'", the verification-gates section said "real people ran a decision
#      end-to-end, each ratified". The weaker one was met, declared closed, and the
#      stronger one stopped being tracked. That contradiction is now fixed in the doc.
#   2. Nobody ever asked the cheapest possible question: does the file the roadmap names
#      exist? It takes a second and would have surfaced this every single session.
#
# This script asks question 2 mechanically. It deliberately does NOT try to judge whether
# a file is any good, only whether the roadmap is describing a reality that exists. A
# roadmap that names files nobody wrote is a roadmap nobody is reading.
#
# Usage: scripts/roadmap-reality-check.sh [roadmap_path]
#
# Exit 0, prints "OK ..."      — every path the roadmap names exists.
# Exit 1, prints "MISSING ..." — the roadmap names something that does not exist. Either
#                                build it, or strike it from the roadmap. Both are fine.
#                                Leaving it named-but-absent is what cost seven weeks.

set -euo pipefail

ROADMAP="${1:-docs/ROADMAP.md}"

if [[ ! -f "$ROADMAP" ]]; then
  echo "OK (no $ROADMAP)"
  exit 0
fi

# Pull every backtick-quoted path that looks like a repo file out of the engineering-steps
# and critical-files sections. Checked-off ([x]) lines are skipped: a done step may name a
# file that was since renamed or folded into another, and re-litigating history is not the
# job here.
paths="$(awk '
  /^## Concrete next engineering steps/ { inblock = 1; next }
  /^## / && inblock && !/^## Concrete next engineering steps/ {
    if ($0 ~ /^## Critical files/) { inblock = 1; next }
    inblock = 0
  }
  inblock { print }
' "$ROADMAP" \
  | grep -v '^\s*-\s*\[x\]' \
  | grep -oE '`[A-Za-z0-9_./-]+\.(py|md|json|sh|yaml|yml|toml|html)`' \
  | tr -d '`' \
  | sort -u)"

missing=""
count=0
for p in $paths; do
  count=$((count + 1))
  [[ -e "$p" ]] || missing="$missing $p"
done

if [[ -n "$missing" ]]; then
  echo "MISSING checked=$count —$missing"
  echo "  Build it, or strike it from $ROADMAP. Named-but-absent is the failure mode."
  exit 1
fi

echo "OK checked=$count — every path the roadmap names exists"
