"""Dual-era MCP: the 2026-07-28 revision drops `initialize` and carries version, identity and
capabilities in each request's `_meta`; the 2025-11-25-and-earlier revisions keep the handshake.

These tests drive `python -m parley.mcp` over a real pipe, as test_mcp.py does. The legacy
regression fixture was recorded from the server before dual-era support existed, so a change to
the legacy bytes fails here even if every behavioural assertion still passes.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
RECIPE = os.path.join(ROOT, "examples", "demo", "recipe_committee.json")
sys.path.insert(0, ROOT)

from parley import mcp  # noqa: E402

PV = "io.modelcontextprotocol/protocolVersion"
CI = "io.modelcontextprotocol/clientInfo"
CC = "io.modelcontextprotocol/clientCapabilities"
SI = "io.modelcontextprotocol/serverInfo"


def _meta(version="2026-07-28", **extra):
    meta = {PV: version, CI: {"name": "pytest", "version": "0"}, CC: {}}
    meta.update(extra)
    return meta


def _req(req_id, method, params=None, meta=True):
    params = dict(params or {})
    if meta:
        params["_meta"] = _meta() if meta is True else meta
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


def _run(payload: bytes):
    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    proc = subprocess.run([sys.executable, "-m", "parley.mcp"], input=payload,
                          capture_output=True, env=env, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc.stdout


def _talk(messages):
    out = _run(b"".join(json.dumps(m).encode("utf-8") + b"\n" for m in messages))
    return [json.loads(ln) for ln in out.decode("utf-8").splitlines() if ln.strip()]


@pytest.fixture(scope="module")
def recipe():
    with open(RECIPE, encoding="utf-8") as fh:
        return json.load(fh)


def test_discover_returns_a_valid_discover_result():
    (reply,) = _talk([_req("d1", "server/discover")])
    assert reply["id"] == "d1"
    result = reply["result"]
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28", "2025-11-25"]
    assert "tools" in result["capabilities"]
    info = result["_meta"][SI]
    assert info["name"] == "parley" and info["version"] == mcp._version()
    assert isinstance(result["ttlMs"], int) and result["ttlMs"] >= 0
    assert result["cacheScope"] == "public"
    assert "serverInfo" not in result, "2026-07-28 moved serverInfo into _meta"


def test_discover_without_the_required_meta_is_invalid_params():
    (reply,) = _talk([_req("d", "server/discover", meta=False)])
    assert reply["error"]["code"] == -32602
    (reply,) = _talk([_req("d", "server/discover", meta={PV: "2026-07-28"})])
    assert reply["error"]["code"] == -32602, "clientCapabilities is required on every request"


def test_tools_list_is_served_statelessly_with_cache_hints():
    (reply,) = _talk([_req(1, "tools/list")])
    result = reply["result"]
    assert result["resultType"] == "complete"
    assert [t["name"] for t in result["tools"]] == [t["name"] for t in mcp.TOOLS]
    assert result["tools"] == mcp.TOOLS
    assert result["ttlMs"] >= 0 and result["cacheScope"] == "public"
    assert result["_meta"][SI]["name"] == "parley"


def test_tools_call_is_served_statelessly(recipe):
    (reply,) = _talk([_req(2, "tools/call", {"name": "parley_decide", "arguments": {"spec": recipe}})])
    result = reply["result"]
    assert result["resultType"] == "complete" and result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["status"] == "agreed" and len(payload["transcript_sha256"]) == 64


def test_tool_failure_is_a_complete_result_with_iserror():
    (reply,) = _talk([_req(3, "tools/call", {"name": "parley_decide", "arguments": {}})])
    assert reply["result"]["resultType"] == "complete" and reply["result"]["isError"] is True


def test_unknown_tool_and_unknown_method_keep_their_codes():
    unknown_tool, unknown_method, ping = _talk([
        _req(1, "tools/call", {"name": "nope", "arguments": {}}),
        _req(2, "resources/list"),
        _req(3, "ping"),
    ])
    assert unknown_tool["error"]["code"] == -32602
    assert unknown_method["error"]["code"] == -32601
    assert ping["error"]["code"] == -32601, "ping was removed in 2026-07-28"


@pytest.mark.parametrize("version", ["1900-01-01", "2026-12-31", "2025-11-25", ""])
def test_unsupported_modern_version_is_minus_32022(version):
    (reply,) = _talk([_req(1, "tools/list", meta=_meta(version))])
    error = reply["error"]
    assert error["code"] == -32022
    assert error["message"] == "Unsupported protocol version"
    assert error["data"] == {"supported": ["2026-07-28", "2025-11-25"], "requested": version}
    assert reply["id"] == 1


def test_unsupported_version_on_discover_is_minus_32022_too():
    (reply,) = _talk([_req("d", "server/discover", meta=_meta("1900-01-01"))])
    assert reply["error"]["code"] == -32022


def test_modern_request_missing_a_required_field_is_invalid_params():
    no_caps = {PV: "2026-07-28"}
    no_version = {CC: {}}
    bad_caps = {PV: "2026-07-28", CC: "x"}
    bad_version = {PV: 7, CC: {}}
    replies = _talk([_req(1, "tools/list", meta=no_caps), _req(2, "tools/list", meta=no_version),
                     _req(3, "tools/list", meta=bad_caps), _req(4, "tools/list", meta=bad_version)])
    assert [r["error"]["code"] for r in replies] == [-32602] * 4


def test_progress_token_alone_is_not_a_modern_request():
    """A 2025-era client may put progressToken in _meta; that must stay a legacy request."""
    (reply,) = _talk([_req(1, "tools/list", meta={"progressToken": "p"})])
    assert reply["result"] == {"tools": mcp.TOOLS}


def test_legacy_session_is_byte_for_byte_unchanged():
    with open(os.path.join(FIXTURES, "mcp_legacy_session.in.jsonl"), "rb") as fh:
        payload = fh.read()
    with open(os.path.join(FIXTURES, "mcp_legacy_session.out.jsonl"), encoding="utf-8") as fh:
        expected = fh.read().replace("{version}", mcp._version())
    assert _run(payload).decode("utf-8") == expected


def test_initialize_after_modern_requests_selects_legacy_semantics(recipe):
    init = {"jsonrpc": "2.0", "id": 10, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "pytest", "version": "0"}}}
    replies = _talk([
        _req(1, "server/discover"),
        _req(2, "tools/list"),
        init,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 11, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 12, "method": "ping"},
        {"jsonrpc": "2.0", "id": 13, "method": "tools/call",
         "params": {"name": "parley_decide", "arguments": {"spec": recipe}}},
        _req(14, "tools/list"),
    ])
    assert [r["id"] for r in replies] == [1, 2, 10, 11, 12, 13, 14]
    assert "resultType" in replies[0]["result"] and "resultType" in replies[1]["result"]
    assert replies[2]["result"]["protocolVersion"] == "2025-06-18"
    assert replies[2]["result"]["serverInfo"]["name"] == "parley"
    assert replies[3]["result"] == {"tools": mcp.TOOLS}
    assert replies[4]["result"] == {}
    assert "resultType" not in replies[5]["result"]
    assert "resultType" in replies[6]["result"], "a request that carries modern _meta is still modern"


def test_initialize_accepts_2025_11_25_because_discover_advertises_it():
    init = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                       "clientInfo": {"name": "pytest", "version": "0"}}}
    (reply,) = _talk([init])
    assert reply["result"]["protocolVersion"] == "2025-11-25"


def test_same_decision_hash_on_both_eras(recipe):
    legacy = _talk([
        {"jsonrpc": "2.0", "id": 0, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "parley_decide", "arguments": {"spec": recipe}}},
    ])[-1]
    modern = _talk([_req(1, "tools/call", {"name": "parley_decide", "arguments": {"spec": recipe}})])[0]
    assert legacy["result"]["content"] == modern["result"]["content"]
