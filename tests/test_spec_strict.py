"""R9 (security review 2026-11-05): strict red-line comparisons and spec validation."""
import math

import pytest

from parley.spec import Constraint, DecisionSpec


def test_equality_does_not_conflate_bool_and_int():
    assert Constraint("reviewed", "==", True).check({"reviewed": 1}) is False
    assert Constraint("reviewed", "==", False).check({"reviewed": 0}) is False
    assert Constraint("n", "==", 1).check({"n": True}) is False
    assert Constraint("reviewed", "==", True).check({"reviewed": True}) is True
    assert Constraint("n", "==", 1).check({"n": 1}) is True


def test_inequality_fails_closed_on_bool_int_confusion():
    # 1 is loosely equal to True: a negative red line must not be satisfied by retyping the value.
    assert Constraint("reviewed", "!=", True).check({"reviewed": 1}) is False
    assert Constraint("reviewed", "!=", True).check({"reviewed": True}) is False
    assert Constraint("reviewed", "!=", True).check({"reviewed": False}) is True


def test_ordering_rejects_booleans_fail_closed():
    assert Constraint("n", "<=", 5).check({"n": True}) is False
    assert Constraint("n", ">=", 0).check({"n": False}) is False


def test_in_does_not_conflate_bool_and_int():
    assert Constraint("x", "in", [True]).check({"x": 1}) is False
    assert Constraint("x", "in", [1, 2]).check({"x": 2}) is True


def _spec(options):
    return {"title": "t", "options": options, "parties": []}


def test_duplicate_option_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate option id"):
        DecisionSpec.from_dict(_spec([{"id": "a", "n": 1}, {"id": "a", "n": 2}]))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_option_numbers_are_rejected(bad):
    with pytest.raises(ValueError, match="non-finite"):
        DecisionSpec.from_dict(_spec([{"id": "a", "n": bad}]))


def test_valid_spec_still_loads():
    spec = DecisionSpec.from_dict(_spec([{"id": "a", "n": 1, "ok": True}, {"id": "b", "n": 2.5, "ok": False}]))
    assert len(spec.options) == 2
