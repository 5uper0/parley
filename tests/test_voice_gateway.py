"""The voice gateway is the agent's brain — assert it can't betray or leak over the wire.

Emulates what ElevenLabs' Custom-LLM mode sends (`POST /v1/chat/completions`, OpenAI shape) and
reads the SSE reply. The invariants under test are the same non-betrayal guarantees as the core,
now on the speech path: a red-line proposal yields a MASKED refusal (no constraint, no reason, no
score), a feasible one yields acceptance, an unparsable turn fails closed to a clarify, and no
bearer is a 401.
"""
import json
import os
import sys
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # repo root, so `voice` is importable

from voice.gateway import serve
from voice.policy import ACCEPT, REFUSE, CLARIFY

RECIPE = "examples/demo/recipe_estate.json"
OWNER = "Heir 2"  # red line: heir2 >= 30


def _start(bearer=None):
    httpd = serve(RECIPE, OWNER, bearer, port=0)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/v1/chat/completions"


def _say(url, content, bearer=None):
    """Send one counterparty turn, return the assembled assistant reply text."""
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    body = json.dumps({"messages": [{"role": "user", "content": content}], "stream": True})
    req = urllib.request.Request(url, data=body.encode(), headers=headers)
    raw = urllib.request.urlopen(req, timeout=5).read().decode()
    reply = ""
    for line in raw.splitlines():
        if line.startswith("data: ") and "[DONE]" not in line:
            for ch in json.loads(line[6:]).get("choices", []):
                reply += ch.get("delta", {}).get("content", "")
    return reply


def test_feasible_proposal_is_accepted():
    httpd, url = _start()
    try:
        assert _say(url, '{"heir1":50,"heir2":50,"legal_ok":true}') == ACCEPT
    finally:
        httpd.shutdown()


def test_red_line_proposal_is_refused_and_masked():
    httpd, url = _start()
    try:
        reply = _say(url, '{"heir1":90,"heir2":10,"legal_ok":true}')  # heir2=10 crosses heir2>=30
        assert reply == REFUSE
        # the masked refusal must not leak the crossed constraint, its attr, or the threshold
        assert "heir2" not in reply and "30" not in reply and "red" not in reply.lower()
    finally:
        httpd.shutdown()


def test_key_value_speech_also_parses():
    httpd, url = _start()
    try:
        assert _say(url, "let's do heir1=50 heir2=50 legal_ok=true") == ACCEPT
    finally:
        httpd.shutdown()


def test_unparsable_turn_fails_closed_to_clarify():
    httpd, url = _start()
    try:
        # no concrete option in the speech -> never invent agreement, ask to restate
        assert _say(url, "hi there, so how are we going to work this out?") == CLARIFY
    finally:
        httpd.shutdown()


def test_missing_bearer_is_unauthorized():
    httpd, url = _start(bearer="s3cret")
    try:
        try:
            _say(url, '{"heir2":50}')  # no token supplied
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        httpd.shutdown()
