import json
import subprocess
import sys
from pathlib import Path

RUN_ENV_PY = Path(__file__).resolve().parent.parent / "examples" / "run_env.py"


def run_env(*args, timeout=30):
    return subprocess.run(
        [sys.executable, str(RUN_ENV_PY), *args],
        capture_output=True, text=True, check=True, timeout=timeout,
    )


def _assert_scenario_shape(scenario, profiles):
    assert set(scenario) == {"status", "decision", "transcript_sha256", "non_betrayal"}
    assert scenario["status"] in ("agreed", "deadlock")
    assert isinstance(scenario["transcript_sha256"], str) and len(scenario["transcript_sha256"]) == 64
    assert set(scenario["non_betrayal"]) == set(profiles)
    assert all(isinstance(v, bool) for v in scenario["non_betrayal"].values())


def test_json_flag_with_explicit_profiles_emits_one_scenario():
    out = run_env("ana", "bob", "--json").stdout
    scenario = json.loads(out)
    _assert_scenario_shape(scenario, ["ana", "bob"])


def test_json_flag_with_no_profiles_emits_both_default_scenarios():
    out = run_env("--json", timeout=60).stdout
    scenarios = json.loads(out)

    assert isinstance(scenarios, list) and len(scenarios) == 2
    _assert_scenario_shape(scenarios[0], ["ana", "bob"])
    _assert_scenario_shape(scenarios[1], ["ana", "bob", "cara", "dan", "eve"])


def test_default_output_is_unchanged_human_text():
    out = run_env("ana", "bob").stdout

    assert "ENVIRONMENT: 2 bots as separate processes over HTTP" in out
    assert "Each owner verifies non-betrayal with their OWN local sheet" in out
    stripped = out.lstrip()
    assert not stripped.startswith("[")
    assert not stripped.startswith("{")
