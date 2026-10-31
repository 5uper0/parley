# Parley from agent frameworks

Each script starts `parley-mcp` over stdio, lists the three tools, runs `parley_decide` on `examples/demo/recipe_committee.json` and verifies the receipt with `parley_verify_receipt`. They call the tools directly, so no model key is needed; to let an agent decide when to call Parley, hand it the same tools.

| Framework | Script | Tested with |
|---|---|---|
| OpenAI Agents SDK | `openai_agents_stdio.py` | openai-agents 0.24.0, mcp 2.3.0, parley-consensus 0.2.0 |
| LangGraph / LangChain | `langgraph_stdio.py` | langgraph 1.2.17, langchain-mcp-adapters 0.3.2, mcp 1.30.0 |
| smolagents | `smolagents_stdio.py` | smolagents 1.26.0, mcp 1.30.0 (needs `websockets`; mcpadapt 0.1.20 does not import against mcp 2.x) |
| Pydantic AI | `pydantic_ai_stdio.py` | pydantic-ai-slim 2.64.0 (`[mcp]` extra, `MCPToolset`; not run on 1.x), mcp 2.3.0, parley-consensus 0.2.1 |
| Google ADK | `google_adk_stdio.py` | google-adk 2.13.0 (`[mcp]` extra, `McpToolset`; tools called via `run_async`, no `Agent` or `Runner`), mcp 2.3.0, parley-consensus 0.2.1 |
| CrewAI | `crewai_stdio.py` | crewai 1.15.33, crewai-tools[mcp] 1.15.33 (`MCPServerAdapter`), mcpadapt 0.1.19, mcp 1.30.0, Python 3.11, parley-consensus 0.2.1 |

All runs produce the same transcript hash (`bc180fab...` on the current repository code; 0.2.0 records the real score of a rejected option, so its hash differs), which is the point of a deterministic referee: the result does not depend on the framework that called it.

Tested on 2026-10-24, Python 3.14, macOS. Pydantic AI, Google ADK and CrewAI tested 2026-10-31 (versions in their rows). The ADK recipe was not run with a model-driven `Agent`, only with direct tool calls. CrewAI needs Python below 3.14, so its run used 3.11; its script also calls the tools directly, not inside an `Agent` or `Crew`.
