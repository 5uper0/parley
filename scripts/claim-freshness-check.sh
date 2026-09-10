#!/usr/bin/env bash
# claim-freshness-check.sh — does any document claim a test count it should not?
#
# Added 2026-09-06 after an investor-materials audit found five different test counts across
# the packet (64, 77, 104+, 107) while the suite actually had 148. The one number an investor
# can check in ten seconds by cloning the repo was wrong in every single document.
#
# Rewritten 2026-09-10. Keeping thirteen documents in sync with one integer was the real defect:
# every added test forced a thirteen-file sweep, and the sweep was skipped often enough that the
# packet carried five different answers. So the count now lives in exactly ONE place, the data
# room, where an investor is entitled to a precise number next to the command that produces it.
# Every other live document says what is true without an integer ("a full suite green across
# Python 3.11-3.14"), which no longer goes stale when a test is added.
#
# This script therefore checks two different things:
#   1. The data room's number still matches pytest.
#   2. No other live, forward-facing document has grown a test count back.
#
# Historical records are exempt by design: a dated journal, retro, archive or ops log SHOULD say
# what was true on its date. capital/submissions/ is exempt for a stronger reason — each file
# records what was actually sent to a funder, so editing one to match today would falsify the
# record of the application.
#
# Usage: scripts/claim-freshness-check.sh
# Exit 0 "OK"    — the data room agrees with pytest and no other live doc names a count.
# Exit 1 "STALE" — fix the document, not this script.

set -euo pipefail

COUNTED_FILE="docs/capital/data-room/README.md"

REAL="$(.venv/bin/pytest -q 2>&1 | tail -1 | grep -oE '^[0-9]+' || true)"
if [[ -z "$REAL" ]]; then
  echo "SKIP could not read a test count from pytest"
  exit 0
fi

COUNT_RE='[0-9]{2,4}\+? (passing )?tests|tests: [0-9]{2,4}|[0-9]{2,4} passing|[0-9]{2,4} green|[0-9]{2,4} tests'

# A line that anchors itself to a specific past event — a commit, a merged PR, a done/closed
# stamp, a date — is a record of what was true then, not a claim about now. Those stay: a
# closed backlog row saying "104 tests green" at the commit that shipped it is correct history,
# and rewriting it every time the suite grows would be falsifying the record.
HISTORICAL_RE='commit: *[0-9a-f]{7}|PR #[0-9]+|(^|[^a-z])(done|closed|merged|shipped):? |20[0-9]{2}-[01][0-9]-[0-3][0-9]|\xe2\x9c\x85'

# Prints "LINE:CONTENT" for every live test-count claim in $1, skipping historical records.
# The anchor is looked for in a small window around the hit, not only on the hit's own line:
# a closed backlog row wraps across several lines and carries its `commit:`/`Done <date>` stamp
# on a neighbouring one, so a line-only test would flag correct history as a stale claim.
count_hits() {
  local file="$1" n content window
  while IFS= read -r hit; do
    [[ -n "$hit" ]] || continue
    n="${hit%%:*}"
    content="${hit#*:}"
    window="$(sed -n "$(( n > 3 ? n - 3 : 1 )),$(( n + 2 ))p" "$file")"
    grep -qE "$HISTORICAL_RE" <<< "$window" && continue
    printf '%s:%s\n' "$n" "$content"
  done <<< "$(grep -nE "$COUNT_RE" "$file" 2>/dev/null || true)"
}

problems=""

# The public mirror is a filtered snapshot that does not carry docs/capital/, so the counted
# file is simply absent there. Say that plainly rather than reporting agreement with a file
# this tree does not have.
if [[ -f "$COUNTED_FILE" ]]; then
  HAVE_COUNTED=1
else
  HAVE_COUNTED=0
fi

# 1. The one file allowed to name a number must name the right one.
[[ "$HAVE_COUNTED" == 1 ]] && while IFS= read -r hit; do
  [[ -n "$hit" ]] || continue
  n="$(echo "${hit#*:}" | grep -oE "$COUNT_RE" | grep -oE '[0-9]{2,4}' | head -1)"
  [[ "$n" == "$REAL" ]] || problems="$problems
  $COUNTED_FILE: \"${hit#*:}\" (real: $REAL)"
done <<< "$(count_hits "$COUNTED_FILE")"

# 2. Every other live, forward-facing surface must not name one at all.
FILES="$(git ls-files \
  'docs/*.md' 'docs/capital/*.md' 'docs/capital/**/*.md' 'docs/capital/pitch-deck/*.html' \
  'docs/press/*.md' 'docs/strategy/*.md' 'landing/src/**/*.astro' 'docs/dashboard/index.html' \
  'README.md' 2>/dev/null \
  | grep -vE '(archive|retros/|autopilot/|ops/|launch/|cycles/|kaizen/|capital/submissions/|docs/INCOMING-|-2026-[0-9]{2}-[0-9]{2}\.md)' || true)"

for f in $FILES; do
  [[ -f "$f" ]] || continue
  [[ "$f" == "$COUNTED_FILE" ]] && continue
  while IFS= read -r hit; do
    [[ -n "$hit" ]] || continue
    problems="$problems
  $f: \"${hit#*:}\" — no live doc but the data room may name a test count"
  done <<< "$(count_hits "$f")"
done

if [[ -n "$problems" ]]; then
  echo "STALE test-count claims (real: $REAL):$problems"
  echo "  The count belongs in $COUNTED_FILE only, next to the command that produces it."
  echo "  Elsewhere say what is true without an integer, e.g. \"a full suite green across Python 3.11-3.14\"."
  exit 1
fi

if [[ "$HAVE_COUNTED" == 1 ]]; then
  echo "OK the data room agrees with pytest ($REAL); no other live doc names a count"
else
  echo "OK no live doc names a test count (this tree carries no data room)"
fi
