from parley.spec import Constraint


def test_list_value_true_is_not_one():
    assert not Constraint("x", "==", [1]).check({"x": [True]})
    assert not Constraint("x", "in", [[1]]).check({"x": [True]})


def test_not_in_and_ne_reject_container_confusion():
    assert not Constraint("x", "not_in", [[1]]).check({"x": [True]})
    assert not Constraint("x", "!=", [1]).check({"x": [True]})


def test_equal_containers_still_match():
    assert Constraint("x", "==", [1, "a"]).check({"x": [1, "a"]})
    assert Constraint("x", "in", [{"k": [True]}]).check({"x": {"k": [True]}})
    assert Constraint("x", "!=", [1]).check({"x": [2]})
