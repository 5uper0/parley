"""The MCP server is a thin stdio shell around the engine, and the engine must be what answers.

Every test drives `python -m parley.mcp` as a real subprocess over newline-delimited JSON-RPC,
exactly as an MCP host would, so what is checked is the wire: the handshake, the tool catalogue,
and that a decision reached over the wire is byte-for-byte the decision `DecisionSpec.run()`
reaches in-process. Tool failures must come back as `isError` results, never as JSON-RPC errors,
because a host treats the two differently (one is shown to the model, the other kills the call).
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECIPE = os.path.join(ROOT, "examples", "demo", "recipe_committee.json")

sys.path.insert(0, ROOT)

from parley.spec import DecisionSpec, PartySpec  # noqa: E402

INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "pytest", "version": "0"}}}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def _talk(messages, raw: bytes = b""):
    """Feed the server a full session on stdin and collect every stdout line as JSON.

    `messages` are encoded one per line; `raw` is appended verbatim for malformed input. Closing
    stdin ends the session, so the server must exit cleanly on EOF.
    """
    payload = b"".join(json.dumps(m).encode("utf-8") + b"\n" for m in messages) + raw
    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    proc = subprocess.run([sys.executable, "-m", "parley.mcp"], input=payload,
                          capture_output=True, env=env, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    lines = [ln for ln in proc.stdout.decode("utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines], proc.stderr.decode("utf-8", "replace")


def _call(name, arguments, req_id=2):
    return {"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}


def _payload(reply):
    """The JSON a tool wrote into its single text content block."""
    assert "result" in reply, reply
    content = reply["result"]["content"]
    assert len(content) == 1 and content[0]["type"] == "text"
    return json.loads(content[0]["text"])


@pytest.fixture(scope="module")
def recipe():
    with open(RECIPE, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def decided(recipe):
    """One decide call over the wire, shared by the tests that inspect its output."""
    replies, _ = _talk([INIT, INITIALIZED, _call("parley_decide", {"spec": recipe})])
    return _payload(replies[-1])


def test_handshake_reports_parley_and_tools_capability():
    replies, _ = _talk([INIT, INITIALIZED])
    assert len(replies) == 1, "a notification must not be answered"
    r = replies[0]
    assert r["jsonrpc"] == "2.0" and r["id"] == 0
    result = r["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["serverInfo"]["name"] == "parley"
    assert isinstance(result["serverInfo"]["version"], str) and result["serverInfo"]["version"]
    assert result["capabilities"] == {"tools": {}}


def test_handshake_echoes_a_supported_older_version_and_falls_back_otherwise():
    older = dict(INIT, params=dict(INIT["params"], protocolVersion="2025-03-26"))
    replies, _ = _talk([older])
    assert replies[0]["result"]["protocolVersion"] == "2025-03-26"
    unknown = dict(INIT, params=dict(INIT["params"], protocolVersion="1999-01-01"))
    replies, _ = _talk([unknown])
    assert replies[0]["result"]["protocolVersion"] == "2025-06-18"


def test_ping_returns_empty_result():
    replies, _ = _talk([INIT, {"jsonrpc": "2.0", "id": 7, "method": "ping"}])
    assert replies[-1] == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_tools_list_names_and_schemas():
    replies, _ = _talk([INIT, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
    tools = {t["name"]: t for t in replies[-1]["result"]["tools"]}
    assert set(tools) == {"parley_decide", "parley_verify_receipt", "parley_check_party"}
    for tool in tools.values():
        schema = tool["inputSchema"]
        assert schema["type"] == "object" and schema["required"]
        assert tool["description"].strip()
    assert set(tools["parley_decide"]["inputSchema"]["required"]) == {"spec"}
    assert "rule" in tools["parley_decide"]["inputSchema"]["properties"]
    assert set(tools["parley_verify_receipt"]["inputSchema"]["required"]) == {"transcript", "sha256"}
    assert set(tools["parley_check_party"]["inputSchema"]["required"]) == {"party", "decision"}
    # the host holds every sheet in this mode: the description must say so, not imply privacy
    assert "privacy" in tools["parley_decide"]["description"].lower()
    assert "run_env.py" in tools["parley_decide"]["description"]


def test_decide_matches_the_in_process_engine(recipe, decided):
    expected = DecisionSpec.from_dict(recipe).run()
    assert decided["status"] == expected.status == "agreed"
    assert decided["decision"] == expected.decision
    assert decided["transcript"] == expected.transcript.to_dict()
    assert decided["transcript_sha256"] == expected.transcript.hash()
    assert len(decided["transcript_sha256"]) == 64


def test_decide_rejects_an_unknown_rule_as_a_tool_error(recipe):
    replies, _ = _talk([INIT, _call("parley_decide", {"spec": recipe, "rule": "majority"})])
    result = replies[-1]["result"]
    assert result["isError"] is True
    assert "majority" in result["content"][0]["text"]


def test_verify_receipt_round_trip_and_tamper(decided):
    ok = _call("parley_verify_receipt",
               {"transcript": decided["transcript"], "sha256": decided["transcript_sha256"]})
    replies, _ = _talk([INIT, ok])
    assert _payload(replies[-1])["match"] is True

    tampered = json.loads(json.dumps(decided["transcript"]))
    verdict = tampered["entries"][0]["verdicts"][0]
    verdict["acceptable"] = not verdict["acceptable"]
    bad = _call("parley_verify_receipt",
                {"transcript": tampered, "sha256": decided["transcript_sha256"]})
    replies, _ = _talk([INIT, bad])
    out = _payload(replies[-1])
    assert out["match"] is False
    assert out["recomputed_sha256"] != decided["transcript_sha256"]


def test_verify_receipt_malformed_transcript_is_a_tool_error():
    replies, _ = _talk([INIT, _call("parley_verify_receipt",
                                    {"transcript": {"entries": "nope"}, "sha256": "0" * 64})])
    result = replies[-1]["result"]
    assert result["isError"] is True
    assert "entries" in result["content"][0]["text"]
    assert "error" not in replies[-1]


def test_check_party_replays_red_lines(recipe, decided):
    budget = next(p for p in recipe["parties"] if p["owner"] == "Budget")
    rubber_stamp = next(o for o in recipe["options"] if o["id"] == "rubber-stamp")
    replies, _ = _talk([
        INIT,
        _call("parley_check_party", {"party": budget, "decision": decided["decision"]}, 1),
        _call("parley_check_party", {"party": budget, "decision": rubber_stamp}, 2),
        _call("parley_check_party", {"party": budget, "decision": None}, 3),
    ])
    by_id = {r["id"]: _payload(r) for r in replies if r["id"] in (1, 2, 3)}
    assert by_id[1] == {"owner": "Budget", "holds": True}
    assert by_id[2] == {"owner": "Budget", "holds": False}
    assert by_id[3] == {"owner": "Budget", "holds": True}, "a deadlock forces nothing on anyone"
    sheet = PartySpec.from_dict(budget).to_sheet()
    assert sheet.evaluate(rubber_stamp).feasible is False


def test_unknown_method_is_minus_32601():
    replies, _ = _talk([INIT, {"jsonrpc": "2.0", "id": 9, "method": "resources/list"}])
    err = replies[-1]
    assert err["id"] == 9 and err["error"]["code"] == -32601


def test_unknown_tool_and_bad_params_are_minus_32602():
    replies, _ = _talk([
        INIT,
        _call("parley_nope", {}, 1),
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"arguments": {}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "parley_decide", "arguments": "not-an-object"}},
    ])
    codes = {r["id"]: r["error"]["code"] for r in replies if "error" in r}
    assert codes == {1: -32602, 2: -32602, 3: -32602}


def test_parse_error_is_minus_32700_and_the_session_survives():
    ping = {"jsonrpc": "2.0", "id": 5, "method": "ping"}
    replies, _ = _talk([INIT], raw=b"{this is not json\n" + json.dumps(ping).encode() + b"\n")
    assert replies[1]["error"]["code"] == -32700 and replies[1]["id"] is None
    assert replies[2] == {"jsonrpc": "2.0", "id": 5, "result": {}}


def test_oversize_line_is_rejected_without_killing_the_session():
    ping = {"jsonrpc": "2.0", "id": 6, "method": "ping"}
    huge = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"pad": "x" * (1024 * 1024)}})
    assert len(huge) > 1024 * 1024
    replies, stderr = _talk([INIT], raw=huge.encode() + b"\n" + json.dumps(ping).encode() + b"\n")
    assert replies[1]["error"]["code"] == -32700 and replies[1]["id"] is None
    assert replies[2] == {"jsonrpc": "2.0", "id": 6, "result": {}}


def test_stdout_carries_only_json_rpc(recipe):
    """Anything the server has to say that is not a reply goes to stderr, or hosts choke."""
    replies, stderr = _talk([INIT, INITIALIZED, _call("parley_decide", {"spec": recipe})])
    assert all(r.get("jsonrpc") == "2.0" for r in replies)
    assert len(replies) == 2


def test_console_script_is_declared():
    tomllib = pytest.importorskip("tomllib")
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as fh:
        scripts = tomllib.load(fh)["project"].get("scripts", {})
    assert scripts.get("parley-mcp") == "parley.mcp:main"
