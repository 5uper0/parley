"""Call Parley from LangGraph / LangChain over MCP stdio.

Needs: pip install langgraph langchain-mcp-adapters "mcp<2" parley-consensus
(tested 2026-10-26 against parley-mcp 0.2.1: langgraph 1.2.17, langchain-mcp-adapters 0.3.2, mcp 1.30.0;
the adapter fails to import against mcp 2.x, hence the pin)
Runs offline: the tools are LangChain tools, called directly with no model key. To let a graph
agent decide when to call Parley, pass `tools` to `langgraph.prebuilt.create_react_agent`.
"""
import asyncio
import json
import pathlib

from langchain_mcp_adapters.client import MultiServerMCPClient

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"


async def main() -> None:
    client = MultiServerMCPClient({"parley": {"command": "parley-mcp", "args": [], "transport": "stdio"}})
    tools = {t.name: t for t in await client.get_tools()}
    print("tools:", sorted(tools))
    out = await tools["parley_decide"].ainvoke({"spec": json.loads(SPEC.read_text())})
    out = json.loads(out[0]["text"]) if isinstance(out, list) else json.loads(out)
    print("decision:", out["decision"]["id"])
    check = await tools["parley_verify_receipt"].ainvoke(
        {"transcript": out["transcript"], "sha256": out["transcript_sha256"]})
    print("verify:", str(check)[:170])


asyncio.run(main())
