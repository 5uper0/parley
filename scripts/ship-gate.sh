#!/usr/bin/env bash
# Parley ship gate — run before every commit (the six hard-stops the conductor/autopilot enforce).
# Bundles: tests green · zero-dependency core intact · examples smoke.
# The redteam extraction + net hardening are covered inside the test suite (tests/test_redteam.py,
# tests/test_net.py), so a green pytest already exercises them.
#
# Usage:  scripts/ship-gate.sh        (uses ./.venv)
# Exit 0 = all gates pass; non-zero = a gate failed (with which one).
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PARLEY_PY:-.venv/bin/python}"
[ -x "$PY" ] || PY="python3"

fail() { echo "✗ ship-gate FAILED: $1" >&2; exit 1; }

echo "▸ 1/3 tests"
"$PY" -m pytest -q || fail "pytest not green"

echo "▸ 2/3 zero-dependency core"
# The core (parley/, minus the optional signed layer net/identity.py) must import only stdlib
# or local parley modules. Correct check via sys.stdlib_module_names — not an ad-hoc grep.
"$PY" - <<'PYCHECK' || fail "core imports a third-party package (keep it zero-dependency)"
import ast, sys, pathlib
ALLOWED_NONSTDLIB_FILE = {"parley/net/identity.py"}  # the optional Ed25519 layer may import nacl
std = set(sys.stdlib_module_names)
bad = []
for p in sorted(pathlib.Path("parley").rglob("*.py")):
    rel = p.as_posix()
    if rel in ALLOWED_NONSTDLIB_FILE:
        continue
    tree = ast.parse(p.read_text(), rel)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [(a.name.split(".")[0], a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import (from . / from ..) is local — fine
                continue
            roots = [(node.module.split(".")[0], node.module)] if node.module else []
        else:
            continue
        for root, full in roots:
            if root == "parley" or root in std:
                continue
            bad.append(f"{rel}: import {full}")
if bad:
    print("\n".join(bad)); sys.exit(1)
print("  core is stdlib-only (nacl confined to net/identity.py)")
PYCHECK

echo "▸ 3/3 examples smoke"
"$PY" examples/meeting.py >/dev/null || fail "examples/meeting.py errored"

echo "✓ ship-gate passed — tests green · zero-dep core · examples run"
