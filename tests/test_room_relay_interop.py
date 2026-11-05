"""A record produced by the JS relay core must verify under Python's own verifier: same signed
payload bytes, same transcript hash, run-bound to the session, keys pinned to the roster."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("nacl")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

from parley.net.identity import verify_transcript
from parley.transcript import Transcript

ROOT = Path(__file__).resolve().parent.parent


def _relay_result():
    out = subprocess.run([NODE, str(ROOT / "room/test/emit-record.mjs")], check=True,
                         capture_output=True, text=True, timeout=30).stdout
    return json.loads(out)


def test_js_relay_record_verifies_in_python():
    res = _relay_result()
    t = Transcript.from_dict(json.loads(res["transcript_json"]))
    assert res["status"] == "agreed" and res["decision"] == {"slot": "sat"}
    assert t.hash() == res["transcript_hash"]
    assert verify_transcript(t, expected_session=res["session"], roster=res["roster"])


def test_wrong_session_or_swapped_roster_fails():
    res = _relay_result()
    t = Transcript.from_dict(json.loads(res["transcript_json"]))
    assert not verify_transcript(t, expected_session="other", roster=res["roster"])
    swapped = {"ana": res["roster"]["ben"], "ben": res["roster"]["ana"]}
    assert not verify_transcript(t, expected_session=res["session"], roster=swapped)
