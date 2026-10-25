"""Cross-check against the official python SDK when it is installed (mcp >= 2.3 speaks 2026-07-28).
Skipped otherwise: the core stays dependency-free and CI does not need the SDK."""
import asyncio
import json
import os
import sys

import pytest

pytest.importorskip("mcp.client.stdio")
from mcp import Client  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECIPE = os.path.join(ROOT, "examples", "demo", "recipe_committee.json")


async def _decide(mode):
    params = StdioServerParameters(command=sys.executable, args=["-m", "parley.mcp"], cwd=ROOT,
                                   env={"PYTHONPATH": ROOT})
    with open(RECIPE, encoding="utf-8") as fh:
        spec = json.load(fh)
    async with Client(params, mode=mode) as client:
        tools = await client.list_tools()
        result = await client.call_tool("parley_decide", {"spec": spec})
        return client.protocol_version, len(tools.tools), json.loads(result.content[0].text)


def test_sdk_auto_mode_negotiates_the_modern_era_and_hash_matches_legacy():
    modern_version, n_tools, modern = asyncio.run(_decide("auto"))
    legacy_version, _, legacy = asyncio.run(_decide("legacy"))
    assert modern_version == "2026-07-28" and legacy_version != "2026-07-28"
    assert n_tools == 3
    assert modern["transcript_sha256"] == legacy["transcript_sha256"]
