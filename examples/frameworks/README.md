# Parley from agent frameworks

Each script starts `parley-mcp` over stdio, lists the three tools, runs `parley_decide` on `examples/demo/recipe_committee.json` and verifies the receipt with `parley_verify_receipt`. They call the tools directly, so no model key is needed; to let an agent decide when to call Parley, hand it the same tools.

| Framework | Script | Tested with |
|---|---|---|
| OpenAI Agents SDK | `openai_agents_stdio.py` | openai-agents 0.24.0, mcp 2.3.0, parley-consensus 0.2.0 |
| LangGraph / LangChain | `langgraph_stdio.py` | langgraph 1.2.17, langchain-mcp-adapters 0.3.2, mcp 1.30.0 |
| smolagents | `smolagents_stdio.py` | smolagents 1.26.0, mcp 1.30.0 (needs `websockets`; mcpadapt 0.1.20 does not import against mcp 2.x) |

All runs produce the same transcript hash (`d08a48eb...`), which is the point of a deterministic referee: the result does not depend on the framework that called it.

Tested on 2026-10-24, Python 3.14, macOS. Other frameworks (CrewAI, Google ADK, Pydantic AI) are not covered yet.
