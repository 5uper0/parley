"""Q1 of the collusion sprint: no coalition report crosses the honest owner's red line.

Smoke-sized grid; the full grid is run by examples/collusion_sprint/harness.py.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "collusion_harness",
    Path(__file__).resolve().parent.parent / "examples" / "collusion_sprint" / "harness.py")
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def test_no_red_line_violation_and_outcome_verifies_on_smallest_grid():
    rows = list(harness.sweep([3, 5], [4, 8], [1, 2], harness.STRATEGIES, 10))
    assert rows
    assert sum(r["h_violated"] for r in rows) == 0
    assert all(r["atk_verifies"] == 1 for r in rows)


def test_grief_always_deadlocks():
    rows = [r for r in harness.sweep([3], [4], [1], ["S4"], 10)]
    assert all(r["atk_status"] == "deadlock" for r in rows)
