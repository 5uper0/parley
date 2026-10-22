"""Entry point of the MCPB bundle: run parley's stdio MCP server from the bundled copy of the package."""
import json
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))

from parley import mcp  # noqa: E402

# The bundle is not pip-installed, so importlib.metadata cannot find the version.
_version = json.loads((here.parent / "manifest.json").read_text(encoding="utf-8"))["version"]
mcp._version = lambda: _version

if __name__ == "__main__":
    raise SystemExit(mcp.main())
