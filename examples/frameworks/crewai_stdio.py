"""Call Parley from CrewAI over MCP stdio.

Needs: pip install crewai "crewai-tools[mcp]" parley-consensus   (CrewAI needs Python below 3.14)
Runs offline: it calls the tools directly, no model key. To let a CrewAI agent decide when to
call Parley, pass `tools=tools` to `crewai.Agent` instead.
"""
import json
import pathlib

from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

SPEC = pathlib.Path(__file__).parent.parent / "demo" / "recipe_committee.json"


def main() -> None:
    params = StdioServerParameters(command="parley-mcp", args=[])
    with MCPServerAdapter(params) as tools:
        by_name = {t.name: t for t in tools}
        print("tools:", sorted(by_name))
        spec = json.loads(SPEC.read_text())
        spec = {k: spec[k] for k in ("title", "options", "parties")}  # CrewAI validates the schema strictly
        out = by_name["parley_decide"].run(spec=spec)
        out = json.loads(out) if isinstance(out, str) else out
        print("decision:", out.get("decision", out)["id"])
        check = by_name["parley_verify_receipt"].run(
            transcript=out["transcript"], sha256=out["transcript_sha256"]
        )
        print("verify:", str(check)[:160])


main()
