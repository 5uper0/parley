"""The MCP server is a thin stdio shell around the engine, and the engine must be what answers.

Every test drives `python -m parley.mcp` as a real subprocess over newline-delimited JSON-RPC,
exactly as an MCP host would, so what is checked is the wire: the handshake, the tool catalogue,
and that a decision reached over the wire is byte-for-byte the decision `DecisionSpec.run()`
reaches in-process. Tool failures must come back as `isError` results, never as JSON-RPC errors,
because a host treats the two differently (one is shown to the model, the other kills the call).
"""
import io
import json
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECIPE = os.path.join(ROOT, "examples", "demo", "recipe_committee.json")

sys.path.insert(0, ROOT)

from parley import mcp  # noqa: E402
from parley.spec import DecisionSpec, PartySpec  # noqa: E402
from parley.transcript import Transcript  # noqa: E402


def _strict(text: str):
    """json.loads that refuses NaN/Infinity: what the server writes must be JSON, not Python."""
    def reject(token):
        raise ValueError(f"not JSON: {token}")
    return json.loads(text, parse_constant=reject)

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
    return [_strict(ln) for ln in lines], proc.stderr.decode("utf-8", "replace")


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
    older = dict(INIT, params=dict(INIT["params"], protocolVersion="2024-11-05"))
    replies, _ = _talk([older])
    assert replies[0]["result"]["protocolVersion"] == "2024-11-05"
    for unsupported in ("1999-01-01", "2025-03-26"):  # 2025-03-26 requires batching, which we do not do
        req = dict(INIT, params=dict(INIT["params"], protocolVersion=unsupported))
        replies, _ = _talk([req])
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
    assert "expected_owners" in tools["parley_verify_receipt"]["inputSchema"]["properties"]
    assert set(tools["parley_check_party"]["inputSchema"]["required"]) == {"party", "decision"}
    # the host holds every sheet in this mode: the description must say so, not imply privacy
    assert "privacy" in tools["parley_decide"]["description"].lower()
    assert "run_env.py" in tools["parley_decide"]["description"]
    # the hash is unsigned and not stored here: a caller-supplied hash proves nothing on its own
    assert "unsigned" in tools["parley_verify_receipt"]["description"]
    assert "max_min_verified" in tools["parley_verify_receipt"]["description"]
    spec_schema = tools["parley_decide"]["inputSchema"]["properties"]["spec"]
    assert spec_schema["properties"]["options"]["maxItems"] == mcp.MAX_OPTIONS
    assert spec_schema["properties"]["parties"]["maxItems"] == mcp.MAX_PARTIES
    value_schema = spec_schema["properties"]["parties"]["items"]["properties"]["hard"]["items"]["properties"]["value"]
    assert value_schema["maxItems"] == mcp.MAX_CONSTRAINT_VALUES
    utility = spec_schema["properties"]["parties"]["items"]["properties"]["utility"]["items"]
    assert "[0, 1]" not in utility["description"], "spec.py never clamps; negative weights leave that range"


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


def _oversized_specs(recipe):
    """One spec per bound: a real recipe stretched past exactly one limit."""
    option, party = recipe["options"][0], recipe["parties"][0]
    too_many_options = dict(recipe, options=[dict(option, id=str(i)) for i in range(mcp.MAX_OPTIONS + 1)])
    too_many_parties = dict(recipe, parties=[dict(party, owner=str(i)) for i in range(mcp.MAX_PARTIES + 1)])
    n_opts = mcp.MAX_PRODUCT // mcp.MAX_PARTIES + 1
    assert n_opts <= mcp.MAX_OPTIONS and n_opts * mcp.MAX_PARTIES > mcp.MAX_PRODUCT
    too_big_product = dict(recipe,
                           options=[dict(option, id=str(i)) for i in range(n_opts)],
                           parties=[dict(party, owner=str(i)) for i in range(mcp.MAX_PARTIES)])
    long_list = dict(party, hard=[{"attr": "id", "op": "in",
                                   "value": list(range(mcp.MAX_CONSTRAINT_VALUES + 1))}])
    too_long_value = dict(recipe, parties=[long_list])
    return {"options": too_many_options, "parties": too_many_parties,
            "product": too_big_product, "value_list": too_long_value}


def test_oversized_spec_is_refused_before_it_runs(recipe):
    specs = _oversized_specs(recipe)
    calls = [_call("parley_decide", {"spec": s}, i) for i, s in enumerate(specs.values(), 1)]
    started = time.monotonic()
    replies, _ = _talk([INIT, *calls])
    elapsed = time.monotonic() - started
    results = {r["id"]: r["result"] for r in replies if r["id"] != 0}
    assert len(results) == len(specs)
    for name, result in zip(specs, results.values()):
        assert result["isError"] is True, name
        assert "limit" in result["content"][0]["text"].lower(), name
    assert elapsed < 5, f"refusal must be cheap, took {elapsed:.1f}s"
    # the largest spec that passes every bound still runs
    limit_ok = dict(recipe, options=[dict(recipe["options"][0], id=str(i)) for i in range(mcp.MAX_OPTIONS)],
                    parties=[dict(recipe["parties"][0], owner=str(i))
                             for i in range(mcp.MAX_PRODUCT // mcp.MAX_OPTIONS)])
    replies, _ = _talk([INIT, _call("parley_decide", {"spec": limit_ok})])
    assert replies[-1]["result"]["isError"] is False


def test_verify_receipt_round_trip_and_tamper(decided):
    ok = _call("parley_verify_receipt",
               {"transcript": decided["transcript"], "sha256": decided["transcript_sha256"]})
    replies, _ = _talk([INIT, ok])
    out = _payload(replies[-1])
    assert out["match"] is True and out["max_min_verified"] is True

    tampered = json.loads(json.dumps(decided["transcript"]))
    verdict = tampered["entries"][0]["verdicts"][0]
    verdict["acceptable"] = not verdict["acceptable"]
    bad = _call("parley_verify_receipt",
                {"transcript": tampered, "sha256": decided["transcript_sha256"]})
    replies, _ = _talk([INIT, bad])
    out = _payload(replies[-1])
    assert out["match"] is False
    assert out["recomputed_sha256"] != decided["transcript_sha256"]


def test_verify_receipt_catches_a_forged_decision_the_hash_cannot(recipe, decided):
    """A caller who edits the record and re-hashes it gets match=true; only the recomputation
    over the recorded verdicts notices the winner was swapped."""
    forged = json.loads(json.dumps(decided["transcript"]))
    other = next(o for o in recipe["options"] if o["id"] == "fund-literacy")
    assert other != decided["decision"]
    forged["result"]["decision"] = other
    rehashed = Transcript.from_dict(forged).hash()
    assert rehashed != decided["transcript_sha256"]
    owners = [p["owner"] for p in recipe["parties"]]
    replies, _ = _talk([
        INIT,
        _call("parley_verify_receipt", {"transcript": forged, "sha256": rehashed}, 1),
        _call("parley_verify_receipt",
              {"transcript": forged, "sha256": rehashed, "expected_owners": owners}, 2),
        _call("parley_verify_receipt",
              {"transcript": decided["transcript"], "sha256": decided["transcript_sha256"],
               "expected_owners": owners + ["Stranger"]}, 3),
    ])
    by_id = {r["id"]: _payload(r) for r in replies if r["id"] in (1, 2, 3)}
    assert by_id[1]["match"] is True and by_id[1]["max_min_verified"] is False
    assert by_id[2]["match"] is True and by_id[2]["max_min_verified"] is False
    assert by_id[3]["match"] is True and by_id[3]["max_min_verified"] is False, \
        "a roster the record does not carry must fail the recomputation"


def test_verify_receipt_cannot_catch_verdicts_rewritten_to_fit_the_swap(recipe, decided):
    """Pins the stated limit: unsigned verdicts rewritten to crown a new winner pass both checks."""
    forged = json.loads(json.dumps(decided["transcript"]))
    other = next(o for o in recipe["options"] if o["id"] == "fund-literacy")
    for entry in forged["entries"]:
        winner = entry["option"] == other
        for v in entry["verdicts"]:
            v["acceptable"], v["score"], v["reason"] = (True, 1.0, "ok") if winner else (v["acceptable"], 0.0, v["reason"])
    forged["result"]["decision"] = other
    replies, _ = _talk([INIT, _call("parley_verify_receipt",
                                    {"transcript": forged, "sha256": Transcript.from_dict(forged).hash()}, 1)])
    payload = _payload(replies[-1])
    assert payload["match"] is True and payload["max_min_verified"] is True


def test_notification_with_a_bad_jsonrpc_field_gets_no_reply():
    replies, _ = _talk([INIT, {"jsonrpc": "1.0", "method": "notifications/initialized"},
                        {"jsonrpc": "2.0", "id": 9, "method": "ping"}])
    assert [r["id"] for r in replies] == [0, 9]


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


def test_deeply_nested_line_is_a_parse_error_and_the_session_survives():
    """`json.loads` raises RecursionError, not ValueError, on 200k open brackets."""
    ping = {"jsonrpc": "2.0", "id": 8, "method": "ping"}
    replies, _ = _talk([INIT], raw=b"[" * 200000 + b"\n" + json.dumps(ping).encode() + b"\n")
    assert replies[1]["error"]["code"] == -32700 and replies[1]["id"] is None
    assert replies[2] == {"jsonrpc": "2.0", "id": 8, "result": {}}


def test_unexpected_exception_in_a_request_is_minus_32603_and_the_session_survives(monkeypatch):
    def boom(method, params):
        if method == "tools/list":
            raise RuntimeError("wiring fault")
        return {}
    monkeypatch.setattr(mcp, "dispatch", boom)
    stdin = io.BytesIO(b'{"jsonrpc":"2.0","id":"a","method":"tools/list"}\n'
                       b'{"jsonrpc":"2.0","id":"b","method":"ping"}\n')
    stdout = io.BytesIO()
    mcp.serve(stdin, stdout)
    replies = [_strict(ln) for ln in stdout.getvalue().decode().splitlines()]
    assert replies[0]["id"] == "a" and replies[0]["error"]["code"] == -32603
    assert replies[1] == {"jsonrpc": "2.0", "id": "b", "result": {}}


def test_invalid_ids_and_non_json_constants_never_reach_stdout():
    """A NaN id echoed back is not JSON; a bool or float id is not a JSON-RPC id we accept."""
    raw = b"\n".join([
        b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}',
        b'{"jsonrpc":"2.0","id":true,"method":"ping"}',
        b'{"jsonrpc":"2.0","id":1.5,"method":"ping"}',
        b'{"id":3,"method":"ping"}',
        b'{"jsonrpc":"1.0","id":4,"method":"ping"}',
        b'{"jsonrpc":"2.0","id":"ok","method":"ping"}',
    ]) + b"\n"
    replies, _ = _talk([], raw=raw)  # _talk's strict parser rejects NaN on stdout
    assert replies[0]["error"]["code"] == -32700 and replies[0]["id"] is None
    assert replies[1]["error"]["code"] == -32600 and replies[1]["id"] is None
    assert replies[2]["error"]["code"] == -32600 and replies[2]["id"] is None
    assert replies[3]["error"]["code"] == -32600 and replies[3]["id"] == 3
    assert replies[4]["error"]["code"] == -32600 and replies[4]["id"] == 4
    assert replies[5] == {"jsonrpc": "2.0", "id": "ok", "result": {}}


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
    assert "parley MCP server" in stderr and "ready" in stderr, stderr


def test_console_script_is_declared():
    tomllib = pytest.importorskip("tomllib")
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as fh:
        scripts = tomllib.load(fh)["project"].get("scripts", {})
    assert scripts.get("parley-mcp") == "parley.mcp:main"
