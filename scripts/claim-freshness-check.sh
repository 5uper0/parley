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
# This script checks three things:
#   1. The data room still states a count at all.
#   2. That count matches pytest.
#   3. No other live, forward-facing document has grown a count back.
#
# Historical records are exempt by design: a dated journal, retro, archive or ops log SHOULD say
# what was true on its date. capital/submissions/ is exempt for a stronger reason — each file
# records what was actually sent to a funder, so editing one to match today would falsify the
# record of the application.
#
# Usage: scripts/claim-freshness-check.sh
# Exit 0 "OK"    — the data room states the real count and no other live doc names one.
# Exit 1 "STALE" — fix the document, not this script.

set -euo pipefail

COUNTED_FILE="docs/capital/data-room/README.md"

COUNT_RE='[0-9]{2,4}\+? (passing )?tests|tests: [0-9]{2,4}|[0-9]{2,4} passing|[0-9]{2,4} green'

# A claim that carries proof of a specific past event is a record of what was true then, not an
# assertion about now: a closed backlog row saying "104 tests green" beside the commit that
# shipped it is correct history, and rewriting it whenever the suite grows would falsify it.
#
# The anchors below are deliberately strong — a commit hash, a merged PR, a completion stamp.
# Bare English words and bare dates were tried first and are wrong: "this section is done" or a
# "Reviewed 2026-09-06" line sitting near a genuinely stale claim would exempt it, which is the
# one thing this script exists to prevent.
HISTORICAL_RE='commit: *[0-9a-f]{7}|PR #[0-9]+|✅|`(done|closed|held|promoted|dropped): |\*\*Done +[0-9]{4}-[0-9]{2}-[0-9]{2}'

# The anchor is looked for in the markdown block the claim belongs to — bounded by blank lines,
# so a multi-line backlog row is judged as one record — rather than in a fixed slide window,
# which would reach into neighbouring prose that has nothing to do with the claim.
block_around() {
  awk -v n="$2" '
    NR == 1 { start = 1 }
    /^[[:space:]]*$/ { if (NR < n) start = NR + 1; else if (NR > n) { end = NR - 1; exit } }
    END { if (!end) end = NR; print start ":" end }
  ' "$1"
}

# Prints "LINE:CONTENT" for every live test-count claim in $1, skipping historical records.
count_hits() {
  local file="$1" hit n content range
  while IFS= read -r hit; do
    [[ -n "$hit" ]] || continue
    n="${hit%%:*}"
    content="${hit#*:}"
    range="$(block_around "$file" "$n")"
    if sed -n "${range%%:*},${range##*:}p" "$file" | grep -qE "$HISTORICAL_RE"; then
      continue
    fi
    printf '%s:%s\n' "$n" "$content"
  done <<< "$(grep -nE "$COUNT_RE" "$file" 2>/dev/null || true)"
}

# An unreadable count fails: it used to SKIP with exit 0, and every ship-gate run from a worktree
# (no .venv of its own) passed step 5 without comparing anything while the data room drifted.
PY="${PARLEY_PY:-.venv/bin/python}"
REAL="$("$PY" -m pytest -q 2>&1 | tail -1 | grep -oE '^[0-9]+' || true)"
if [[ -z "$REAL" ]]; then
  echo "STALE could not read a test count from $PY -m pytest; set PARLEY_PY to a python with pytest"
  exit 1
fi

problems=""

# The public mirror is a filtered snapshot that does not carry docs/capital/, so the counted
# file is simply absent there. Say that plainly rather than reporting agreement with a file
# this tree does not have.
if [[ -f "$COUNTED_FILE" ]]; then HAVE_COUNTED=1; else HAVE_COUNTED=0; fi

# 1 and 2. The one file allowed to name a number must name one, and name the right one.
# The "must name one" half matters: if the line is reworded or deleted, an empty result would
# otherwise read as agreement, and the single authoritative number could vanish silently.
if [[ "$HAVE_COUNTED" == 1 ]]; then
  counted_hits="$(count_hits "$COUNTED_FILE")"
  if [[ -z "$counted_hits" ]]; then
    problems="$problems
  $COUNTED_FILE: states no test count at all — it is the one file that must state one, beside the command that produces it"
  else
    while IFS= read -r hit; do
      [[ -n "$hit" ]] || continue
      n="$(grep -oE "$COUNT_RE" <<< "${hit#*:}" | grep -oE '[0-9]{2,4}' | head -1)"
      [[ "$n" == "$REAL" ]] || problems="$problems
  $COUNTED_FILE: \"${hit#*:}\" (real: $REAL)"
    done <<< "$counted_hits"
  fi
fi

# 3. Every other live, forward-facing surface must not name one at all.
FILES="$(git ls-files \
  'docs/*.md' 'docs/capital/*.md' 'docs/capital/**/*.md' 'docs/capital/pitch-deck/*.html' \
  'docs/press/*.md' 'docs/strategy/*.md' 'landing/src/**/*.astro' 'docs/dashboard/index.html' \
  'README.md' 2>/dev/null \
  | grep -vE '(archive|retros/|autopilot/|ops/|launch/|cycles/|kaizen/|capital/submissions/|docs/INCOMING-|-20[0-9]{2}-[0-9]{2}-[0-9]{2}\.md)' || true)"

for f in $FILES; do
  [[ -f "$f" ]] || continue
  [[ "$f" == "$COUNTED_FILE" ]] && continue
  while IFS= read -r hit; do
    [[ -n "$hit" ]] || continue
    problems="$problems
  $f: \"${hit#*:}\" — only $COUNTED_FILE may state a test count; say it without an integer here"
  done <<< "$(count_hits "$f")"
done

if [[ -n "$problems" ]]; then
  echo "STALE test-count claims (real: $REAL):$problems"
  echo "  The count belongs in $COUNTED_FILE only, next to the command that produces it."
  echo "  Elsewhere say what is true without an integer, e.g. \"a full suite green across Python 3.11-3.14\"."
  exit 1
fi

if [[ "$HAVE_COUNTED" == 1 ]]; then
  echo "OK the data room states the real count ($REAL); no other live doc names one"
else
  echo "OK no live doc names a test count (this tree carries no data room)"
fi
