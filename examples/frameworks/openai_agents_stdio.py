"""Call Parley from the OpenAI Agents SDK over MCP stdio.

Needs: pip install openai-agents parley-consensus
Runs offline: it calls the tools directly, no model key. To let an agent decide
when to call Parley, pass `mcp_servers=[server]` to `agents.Agent` instead.
"""
import asyncio
import json
import pathlib

from agents.mcp import MCPServerStdio

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"


async def main() -> None:
    async with MCPServerStdio(params={"command": "parley-mcp"}) as server:
        names = [t.name for t in await server.list_tools()]
        print("tools:", names)
        spec = json.loads(SPEC.read_text())
        result = await server.call_tool("parley_decide", {"spec": spec})
        out = json.loads(result.content[0].text)
        print("decision:", json.dumps(out.get("decision", out), indent=2)[:600])
        check = await server.call_tool(
            "parley_verify_receipt",
            {"transcript": out["transcript"], "sha256": out["transcript_sha256"]},
        )
        print("verify:", check.content[0].text[:200])


asyncio.run(main())
