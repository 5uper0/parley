#!/usr/bin/env bash
# claim-freshness-check.sh — does any document claim a test count that is not the real one?
# Added 2026-09-06 after an investor-materials audit found five different test counts across
# the packet (64, 77, 104+, 107) while the suite actually had 148. The one number an investor
# can check in ten seconds by cloning the repo was wrong in every single document.
#
# Historical records are exempt by design: a dated journal, retro, archive or ops log SHOULD
# say what was true on its date. Only live, forward-facing documents are checked.
#
# Usage: scripts/claim-freshness-check.sh
# Exit 0 "OK"    — every live doc agrees with pytest.
# Exit 1 "STALE" — a live doc claims a different count. Fix the doc, not this script.

set -euo pipefail

REAL="$(.venv/bin/pytest -q 2>&1 | tail -1 | grep -oE '^[0-9]+' || true)"
if [[ -z "$REAL" ]]; then
  echo "SKIP could not read a test count from pytest"
  exit 0
fi

# Live, forward-facing surfaces only. Journals and archives are deliberately excluded.
# capital/submissions/ is exempt for a stronger reason: each file records what was actually
# sent to a funder on a given date. Editing one to match today's numbers would falsify the
# record of the application. Those files are frozen on purpose.
FILES="$(git ls-files \
  'docs/capital/*.md' 'docs/capital/**/*.md' 'docs/capital/pitch-deck/*.html' \
  'docs/press/*.md' 'landing/src/**/*.astro' \
  'README.md' 'docs/COMPASS.md' 'docs/STRATEGY.md' 'docs/PRD.md' 'docs/ROADMAP.md' 2>/dev/null \
  | grep -vE '(archive|retros/|autopilot/|ops/|launch/|cycles/|kaizen/|capital/submissions/)' || true)"

stale=""
for f in $FILES; do
  [[ -f "$f" ]] || continue
  hits="$(grep -oE '[0-9]{2,4}\+? (passing )?tests|tests: [0-9]{2,4}|[0-9]{2,4} passing' "$f" 2>/dev/null || true)"
  while IFS= read -r hit; do
    [[ -n "$hit" ]] || continue
    n="$(echo "$hit" | grep -oE '[0-9]{2,4}' | head -1)"
    [[ "$n" == "$REAL" ]] || stale="$stale
  $f: \"$hit\" (real: $REAL)"
  done <<< "$hits"
done

if [[ -n "$stale" ]]; then
  echo "STALE test-count claims against the real $REAL:$stale"
  echo "  Fix the documents. An investor who clones the repo runs pytest in ten seconds."
  exit 1
fi

echo "OK every live doc agrees with pytest ($REAL)"
