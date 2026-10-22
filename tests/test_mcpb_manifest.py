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


def test_bundle_entry_script_boots_and_reports_the_manifest_version(tmp_path):
    import shutil
    import subprocess
    import sys
    shutil.copytree(ROOT / "mcpb" / "server", tmp_path / "server")
    shutil.copytree(ROOT / "parley", tmp_path / "server" / "parley")
    shutil.copy(ROOT / "mcpb" / "manifest.json", tmp_path / "manifest.json")
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "t", "version": "1"}}})
    out = subprocess.run([sys.executable, "-I", str(tmp_path / "server" / "main.py")],
                         input=request + "\n", capture_output=True, text=True, timeout=30).stdout
    assert json.loads(out.splitlines()[0])["result"]["serverInfo"]["version"] == MANIFEST["version"]
