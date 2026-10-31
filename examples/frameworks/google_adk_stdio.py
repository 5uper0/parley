"""Call Parley from Google ADK over MCP stdio.

Needs: pip install "google-adk[mcp]" parley-consensus
Runs offline: it calls the tools directly through ADK's `McpToolset`, no model key. To let an
agent decide when to call Parley, pass the toolset in `tools=[...]` of a `google.adk.agents.Agent`.
"""
import asyncio
import json
import pathlib

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"


def unwrap(res):
    if isinstance(res, dict) and res.get("structuredContent"):
        return res["structuredContent"]
    if isinstance(res, dict) and res.get("content"):
        return json.loads(res["content"][0]["text"])
    return res


async def main() -> None:
    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="parley-mcp", args=[])
        )
    )
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        print("tools:", sorted(tools))
        spec = json.loads(SPEC.read_text())
        out = unwrap(await tools["parley_decide"].run_async(args={"spec": spec}, tool_context=None))
        print("decision:", out["decision"]["id"])
        check = await tools["parley_verify_receipt"].run_async(
            args={"transcript": out["transcript"], "sha256": out["transcript_sha256"]},
            tool_context=None,
        )
        print("verify:", str(check)[:160])
    finally:
        await toolset.close()


asyncio.run(main())
