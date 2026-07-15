"""The demo server is the public money-shot + the docker entrypoint — keep it honest and bindable."""
import os
import sys

import pytest

_DEMO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "demo")
sys.path.insert(0, _DEMO)

server = pytest.importorskip("server")


def test_bind_defaults_to_localhost():
    assert server.bind_from_env({}) == ("127.0.0.1", 8080)


def test_bind_reads_env_for_docker():
    # This is exactly what the Dockerfile sets so the container is reachable from the host.
    assert server.bind_from_env({"PARLEY_HOST": "0.0.0.0", "PARLEY_PORT": "9000"}) == ("0.0.0.0", 9000)


def test_run_recipe_reaches_a_verified_decision():
    data = server.run_recipe(os.path.join(_DEMO, "recipe_kyc.json"))
    assert data["status"] == "agreed"
    assert data["decision"] is not None
    # every party can replay their own sheet and confirm no red line was crossed
    assert all(data["non_betrayal"].values())
    # the deterministic red line blocked at least one option (the fast-track cheat)
    assert any(not e["feasible"] for e in data["entries"])


def test_recipe_whitelist_rejects_unknown_and_traversal():
    # the ?recipe key is a whitelist lookup, never a path — traversal/unknown keys fail closed
    assert server._recipe_path("nope") is None
    assert server._recipe_path("../server") is None
    assert server._recipe_path("../../etc/passwd") is None
    for key in server.RECIPES:
        assert os.path.isfile(server._recipe_path(key))


def test_every_whitelisted_scenario_runs_verified_with_a_blocked_cheat():
    for key in server.RECIPES:
        data = server.run_recipe(server._recipe_path(key))
        assert data["status"] == "agreed", key
        assert data["decision"] is not None, key
        assert all(data["non_betrayal"].values()), key
        # each scenario has a tempting option the red lines block
        assert any(not e["feasible"] for e in data["entries"]), key


def test_run_recipe_carries_the_plain_language_layer():
    data = server.run_recipe(server._recipe_path("p2p"))
    pres = data["presentation"]
    assert pres and pres.get("situation")
    assert pres["options"]  # human labels per option
    # parties now carry their raw red lines for the technical view
    platform = next(p for p in data["parties"] if p["owner"] == "Platform")
    assert platform["redlines"]  # e.g. "evidence_ok == True"


def test_list_recipes_is_the_picker():
    recipes = server.list_recipes()
    assert [r["key"] for r in recipes] == list(server.RECIPES)
    assert all(r["title"] and r["situation"] for r in recipes)
