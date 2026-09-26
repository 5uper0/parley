"""Parley as an MCP tool: a stdio server any MCP host (Claude Desktop, Claude Code, Cursor) can
launch with `parley-mcp` or `python -m parley.mcp`. Stdlib only, like the rest of the core.

What this mode is honest about: the host process holds every party's spec and hands them all
to one tool call, so there is NO privacy from the host here. What still holds is everything the
engine enforces in code: red lines reject an option deterministically, the max-min rule picks
among what is feasible for everyone, and the receipt is a SHA-256 over the canonical transcript
that anyone can recompute. Private sheets need one process per owner (`examples/run_env.py`).

Wire format: newline-delimited JSON-RPC 2.0, one message per line, at most 1 MB per line.
Stdout carries replies only; everything else goes to stderr, because a stray print on stdout
corrupts the host's framing.
"""
import json
import logging
import sys
from importlib import metadata
from typing import Any, Callable, Dict, Optional

from .spec import DecisionSpec, PartySpec
from .transcript import Transcript

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = frozenset({"2025-06-18", "2025-03-26", "2024-11-05"})
MAX_LINE_BYTES = 1024 * 1024

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602

log = logging.getLogger("parley.mcp")

_NO_PRIVACY = (
    "HONESTY NOTE: in this mode you, the caller, hold every party's spec and pass them all in "
    "one call, so there is no privacy between parties or from you. What still holds: red lines "
    "reject an option deterministically (a violating option cannot win), the max-min rule picks "
    "among options feasible for everyone, and the returned transcript is tamper-evident via "
    "transcript_sha256. For private sheets run one process per owner: examples/run_env.py."
)

_CONSTRAINT_SCHEMA = {
    "type": "object",
    "description": "A red line: option[attr] <op> value must hold or the option is rejected "
                   "for this party. A missing attr fails closed.",
    "properties": {
        "attr": {"type": "string"},
        "op": {"type": "string", "enum": ["==", "!=", "<", "<=", ">", ">=", "in", "not_in"]},
        "value": {"description": "Compared against option[attr]; a list for in/not_in."},
    },
    "required": ["attr", "op", "value"],
}

_UTILITY_SCHEMA = {
    "type": "object",
    "description": "One soft-preference term. Categorical: set `prefer`. Numeric: set "
                   "`direction` (higher|lower) with `lo` and `hi` to normalise on. A party's "
                   "score is the weighted average of its terms, in [0, 1].",
    "properties": {
        "attr": {"type": "string"},
        "weight": {"type": "number", "default": 1.0},
        "prefer": {"description": "Full weight when option[attr] equals this value."},
        "direction": {"type": "string", "enum": ["higher", "lower"]},
        "lo": {"type": "number"},
        "hi": {"type": "number"},
    },
    "required": ["attr"],
}

_PARTY_SCHEMA = {
    "type": "object",
    "description": "One party: a distinct owner name, hard red lines, soft utility terms.",
    "properties": {
        "owner": {"type": "string"},
        "hard": {"type": "array", "items": _CONSTRAINT_SCHEMA, "default": []},
        "utility": {"type": "array", "items": _UTILITY_SCHEMA, "default": []},
    },
    "required": ["owner"],
}

_SPEC_SCHEMA = {
    "type": "object",
    "description": "A DecisionSpec: the shared options plus every party's position, the same "
                   "JSON as examples/demo/recipe_*.json. Extra keys are ignored.",
    "properties": {
        "title": {"type": "string"},
        "options": {
            "type": "array",
            "items": {"type": "object",
                      "description": "One candidate outcome as flat attributes; every attr a "
                                     "constraint or utility term names should be present."},
            "minItems": 1,
        },
        "parties": {"type": "array", "items": _PARTY_SCHEMA, "minItems": 1},
    },
    "required": ["title", "options", "parties"],
}

_TRANSCRIPT_SCHEMA = {
    "type": "object",
    "description": "The `transcript` object returned by parley_decide, unmodified.",
    "properties": {
        "entries": {"type": "array", "items": {"type": "object"}},
        "result": {"type": ["object", "null"]},
    },
    "required": ["entries", "result"],
}

TOOLS = [
    {
        "name": "parley_decide",
        "description": (
            "Reach a decision among parties with conflicting interests. Give the options and each "
            "party's red lines (hard constraints, checked in code) and soft preferences. An option "
            "that crosses any party's red line is rejected outright; among the options acceptable "
            "to everyone the max-min rule picks the one whose least-satisfied party is best off, "
            "tie-broken by total score. No option acceptable to all parties yields an honest "
            "status 'deadlock' with decision null, never a forced choice. Returns JSON: status "
            "('agreed'|'deadlock'), decision (the winning option object or null), transcript "
            "(every option with each party's masked verdict), and transcript_sha256 (the "
            "receipt hash; keep it to verify the transcript later with parley_verify_receipt). "
            + _NO_PRIVACY
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": _SPEC_SCHEMA,
                "rule": {"type": "string", "enum": ["egalitarian"], "default": "egalitarian",
                         "description": "Selection rule. Only 'egalitarian' (max-min) exists."},
            },
            "required": ["spec"],
        },
    },
    {
        "name": "parley_verify_receipt",
        "description": (
            "Check that a transcript is the one a transcript_sha256 was issued for. Rebuilds the "
            "transcript from its dict form (strict shape check) and recomputes the SHA-256 over "
            "the canonical record. Returns JSON: match (true if the recomputed hash equals "
            "sha256), expected_sha256 and recomputed_sha256. Any edit to an option, a verdict or "
            "the result changes the hash, so match=false means the record was altered after the "
            "hash was issued. A malformed transcript is a tool error, not a mismatch."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transcript": _TRANSCRIPT_SCHEMA,
                "sha256": {"type": "string", "minLength": 64, "maxLength": 64,
                           "description": "The transcript_sha256 you were given, hex."},
            },
            "required": ["transcript", "sha256"],
        },
    },
    {
        "name": "parley_check_party",
        "description": (
            "Replay one party's red lines against a decision: did the outcome cross any of "
            "them? Pass the party's spec (the same object you would put in parley_decide's "
            "parties) and the decision object returned by parley_decide. Returns JSON: owner and "
            "holds (true when every red line of that party holds on the decision). A null "
            "decision (deadlock) forces nothing on anyone, so holds is true. Soft preferences "
            "are not judged here, only red lines."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "party": _PARTY_SCHEMA,
                "decision": {"type": ["object", "null"],
                             "description": "The decision from parley_decide, or null for a deadlock."},
            },
            "required": ["party", "decision"],
        },
    },
]


def _require(arguments: dict, *keys: str) -> None:
    missing = [k for k in keys if k not in arguments]
    if missing:
        raise ValueError(f"missing argument(s): {', '.join(missing)}")


def tool_decide(arguments: dict) -> dict:
    _require(arguments, "spec")
    spec = DecisionSpec.from_dict(arguments["spec"])
    result = spec.run(rule=arguments.get("rule", "egalitarian"))
    return {
        "status": result.status,
        "decision": result.decision,
        "transcript": result.transcript.to_dict(),
        "transcript_sha256": result.transcript.hash(),
    }


def tool_verify_receipt(arguments: dict) -> dict:
    _require(arguments, "transcript", "sha256")
    expected = arguments["sha256"]
    if not isinstance(expected, str):
        raise ValueError("sha256 must be a hex string")
    recomputed = Transcript.from_dict(arguments["transcript"]).hash()
    return {"match": recomputed == expected.lower(),
            "expected_sha256": expected, "recomputed_sha256": recomputed}


def tool_check_party(arguments: dict) -> dict:
    _require(arguments, "party", "decision")
    party = PartySpec.from_dict(arguments["party"])
    decision = arguments["decision"]
    if decision is not None and not isinstance(decision, dict):
        raise ValueError("decision must be an option object or null")
    holds = Transcript().verify_non_betrayal(party.to_sheet(), decision)
    return {"owner": party.owner, "holds": holds}


TOOL_HANDLERS: Dict[str, Callable[[dict], dict]] = {
    "parley_decide": tool_decide,
    "parley_verify_receipt": tool_verify_receipt,
    "parley_check_party": tool_check_party,
}


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def _version() -> str:
    try:
        return metadata.version("parley-consensus")
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _initialize(params: Any) -> dict:
    requested = params.get("protocolVersion") if isinstance(params, dict) else None
    version = requested if requested in SUPPORTED_VERSIONS else PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "parley", "version": _version()},
    }


def _tools_call(params: Any) -> dict:
    if not isinstance(params, dict):
        raise RpcError(INVALID_PARAMS, "params must be an object")
    name = params.get("name")
    if name not in TOOL_HANDLERS:
        raise RpcError(INVALID_PARAMS, f"unknown tool: {name!r}")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        raise RpcError(INVALID_PARAMS, "arguments must be an object")
    try:
        payload = TOOL_HANDLERS[name](arguments)
    except Exception as exc:  # a tool failure is a result the model can read, per the MCP spec
        log.info("tool %s failed: %s: %s", name, type(exc).__name__, exc)
        return {"isError": True,
                "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}]}
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return {"isError": False, "content": [{"type": "text", "text": text}]}


def dispatch(method: str, params: Any) -> dict:
    """Route one request. Notifications never reach here."""
    if method == "initialize":
        return _initialize(params)
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return _tools_call(params)
    raise RpcError(METHOD_NOT_FOUND, f"method not found: {method}")


def handle_line(line: bytes) -> Optional[dict]:
    """One inbound line to at most one reply. None means: say nothing (a notification, or a
    response the client sent us)."""
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _error(None, PARSE_ERROR, "parse error")
    if not isinstance(message, dict):
        return _error(None, INVALID_REQUEST, "expected a JSON-RPC 2.0 object")
    req_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        if "id" in message and ("result" in message or "error" in message):
            return None
        return _error(req_id, INVALID_REQUEST, "missing method")
    if "id" not in message:
        if not method.startswith("notifications/"):
            log.info("ignoring notification with unknown method %s", method)
        return None
    try:
        return {"jsonrpc": "2.0", "id": req_id, "result": dispatch(method, message.get("params"))}
    except RpcError as exc:
        return _error(req_id, exc.code, str(exc))


def _error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _read_line(stream) -> Optional[bytes]:
    """Next line, or None at EOF, or b"" for a line over the cap (its remainder is drained so
    the next message still parses)."""
    line = stream.readline(MAX_LINE_BYTES + 1)
    if not line:
        return None
    if len(line) <= MAX_LINE_BYTES or line.endswith(b"\n"):
        return line
    while True:
        chunk = stream.readline(MAX_LINE_BYTES)
        if not chunk or chunk.endswith(b"\n"):
            break
    return b""


def serve(stdin=None, stdout=None) -> None:
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    log.info("parley MCP server %s ready (protocol %s)", _version(), PROTOCOL_VERSION)
    while True:
        line = _read_line(stdin)
        if line is None:
            break
        if line == b"":
            reply = _error(None, PARSE_ERROR, f"line exceeds {MAX_LINE_BYTES} bytes")
        elif not line.strip():
            continue
        else:
            reply = handle_line(line)
        if reply is None:
            continue
        stdout.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
        stdout.flush()
    log.info("stdin closed, exiting")


def main() -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="parley-mcp %(levelname)s %(message)s")
    try:
        serve()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
