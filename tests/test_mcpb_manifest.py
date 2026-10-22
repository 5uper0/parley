"""The MCPB manifest is what Smithery and Claude Desktop show; keep it in step with the server it wraps."""
import json
import pathlib
import re

from parley import mcp

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_lists_exactly_the_servers_tools():
    assert [t["name"] for t in MANIFEST["tools"]] == [t["name"] for t in mcp.TOOLS]


def test_manifest_version_matches_pyproject():
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    assert MANIFEST["version"] == version


def test_manifest_entry_point_exists_and_runtime_matches_package():
    assert (ROOT / "mcpb" / MANIFEST["server"]["entry_point"]).is_file()
    assert MANIFEST["compatibility"]["runtimes"]["python"] == ">=3.10"
