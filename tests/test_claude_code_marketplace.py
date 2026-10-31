"""The Claude Code plugin marketplace must stay in step with the package it installs.

`/plugin install parley@parley` wires an MCP server by running a console script, so the script
name, the plugin version and the marketplace source path are checked against pyproject.toml.
"""
import json
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")

ROOT = Path(__file__).resolve().parent.parent


def _json(rel):
    return json.loads((ROOT / rel).read_text())


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_marketplace_manifest():
    m = _json(".claude-plugin/marketplace.json")
    assert m["name"] == "parley"
    assert m["owner"]["name"]
    entry = next(p for p in m["plugins"] if p["name"] == "parley")
    assert (ROOT / entry["source"]).is_dir()
    assert (ROOT / entry["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_plugin_manifest_matches_pyproject():
    p = _json("plugins/parley/.claude-plugin/plugin.json")
    proj = _pyproject()["project"]
    for key in ("name", "version", "description", "author", "homepage", "repository", "license", "keywords"):
        assert p.get(key), key
    assert p["version"] == proj["version"]


def test_mcp_config_runs_the_declared_console_script():
    scripts = _pyproject()["project"]["scripts"]
    server = _json("plugins/parley/.mcp.json")["mcpServers"]["parley"]
    assert server["command"] == "uvx"
    args = server["args"]
    assert args[args.index("--from") + 1] == _pyproject()["project"]["name"]
    assert args[-1] in scripts
