"""Call Parley from Pydantic AI over MCP stdio.

Needs: pip install "pydantic-ai-slim[mcp]" parley-consensus
Runs offline: it calls the tools directly, no model key. To let an agent decide when to
call Parley, pass `toolsets=[server]` to `pydantic_ai.Agent` instead.
"""
import asyncio
import json
import pathlib

from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"


async def main() -> None:
    server = MCPToolset(StdioTransport(command="parley-mcp", args=[]))
    async with server:
        print("tools:", sorted(t.name for t in await server.list_tools()))
        spec = json.loads(SPEC.read_text())
        out = await server.direct_call_tool("parley_decide", {"spec": spec})
        out = json.loads(out) if isinstance(out, str) else out
        print("decision:", out.get("decision", out)["id"])
        check = await server.direct_call_tool(
            "parley_verify_receipt",
            {"transcript": out["transcript"], "sha256": out["transcript_sha256"]},
        )
        print("verify:", str(check)[:160])


asyncio.run(main())
