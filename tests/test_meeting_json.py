import json
import subprocess
import sys
from pathlib import Path

MEETING_PY = Path(__file__).resolve().parent.parent / "examples" / "meeting.py"


def run_meeting(*args):
    return subprocess.run(
        [sys.executable, str(MEETING_PY), *args],
        capture_output=True, text=True, check=True,
    )


def test_json_flag_emits_valid_json_with_expected_keys():
    out = run_meeting("--json").stdout
    scenarios = json.loads(out)

    assert isinstance(scenarios, list) and len(scenarios) == 2
    for scenario in scenarios:
        assert set(scenario) == {"status", "decision", "transcript_sha256", "entries"}
        assert scenario["status"] in ("agreed", "deadlock")
        assert isinstance(scenario["transcript_sha256"], str) and len(scenario["transcript_sha256"]) == 64
        assert isinstance(scenario["entries"], list) and scenario["entries"]
        for entry in scenario["entries"]:
            assert set(entry["option"]) == {"day", "hour"}
            for verdict in entry["verdicts"]:
                assert set(verdict) >= {"owner", "acceptable", "reason"}


def test_default_output_is_unchanged_human_text():
    out = run_meeting().stdout

    assert "PARLEY" in out
    assert "Each owner privately proves their agent was not betrayed" in out
    with_leading_whitespace_stripped = out.lstrip()
    assert not with_leading_whitespace_stripped.startswith("[")
    assert not with_leading_whitespace_stripped.startswith("{")
