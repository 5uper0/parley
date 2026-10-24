"""Call Parley from smolagents over MCP stdio.

Needs: pip install "smolagents[mcp]" "mcp<2" websockets parley-consensus
(tested 2026-10-24: smolagents 1.26.0 with mcpadapt 0.1.20 fails to import against mcp 2.x, hence the pin)
Runs offline: it calls the tools directly, no model key. To let a CodeAgent decide when to
call Parley, pass `tools=[*tools]` to `smolagents.CodeAgent` inside the same `with` block.
"""
import json
import pathlib

from mcp import StdioServerParameters
from smolagents import MCPClient

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"

with MCPClient(StdioServerParameters(command="parley-mcp")) as tools:
    by_name = {t.name: t for t in tools}
    print("tools:", sorted(by_name))
    spec = json.loads(SPEC.read_text())
    out = by_name["parley_decide"](spec=spec)
    out = json.loads(out) if isinstance(out, str) else out
    print("decision:", out.get("decision", out)["id"])
    check = by_name["parley_verify_receipt"](transcript=out["transcript"], sha256=out["transcript_sha256"])
    print("verify:", str(check)[:160])
