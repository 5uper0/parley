"""The wheel must carry the whole library, under a name pip can actually resolve to us.

The first published wheel listed `packages = ["parley"]` by hand, which setuptools takes
literally: `parley/net/` (signed verdicts, the HTTP bot layer) never made it into the archive
and nothing in the suite noticed, because the tests import from the working tree. These checks
read `pyproject.toml` and match it against the tree, so a new subpackage that the include
patterns miss fails here, before the wheel is built.
"""
import fnmatch
import json
import pathlib

import pytest

tomllib = pytest.importorskip("tomllib")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "parley"


def _pyproject() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def _packages_in_tree() -> set:
    """Every directory under parley/ that Python would import as a package."""
    found = set()
    for init in PACKAGE_DIR.rglob("__init__.py"):
        rel = init.parent.relative_to(ROOT)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        found.add(".".join(rel.parts))
    return found


def _configured_patterns(pyproject: dict) -> list:
    """The include patterns setuptools will match dotted package names against.

    A hand-written `packages = [...]` list is a set of exact names, which is what
    `find_packages(include=...)` also treats a pattern without wildcards as.
    """
    tool = pyproject.get("tool", {}).get("setuptools", {})
    packages = tool.get("packages")
    if isinstance(packages, dict) and "find" in packages:
        return list(packages["find"].get("include", ["*"]))
    if isinstance(packages, list):
        return list(packages)
    return ["*"]


def _matched(names: set, patterns: list) -> set:
    return {n for n in names if any(fnmatch.fnmatchcase(n, p) for p in patterns)}


def test_every_package_in_the_tree_is_matched_by_the_configured_patterns():
    pyproject = _pyproject()
    patterns = _configured_patterns(pyproject)
    in_tree = _packages_in_tree()
    assert "parley.net" in in_tree, "the signed/HTTP layer moved; update this test"
    missing = in_tree - _matched(in_tree, patterns)
    assert not missing, (
        f"pyproject.toml packages config {patterns} leaves {sorted(missing)} out of the wheel"
    )


def test_setuptools_discovers_every_package_in_the_tree():
    """The stdlib matcher above mirrors setuptools; ask setuptools itself where it is installed."""
    setuptools = pytest.importorskip("setuptools")
    patterns = _configured_patterns(_pyproject())
    in_tree = _packages_in_tree()
    discovered = set(setuptools.find_packages(where=str(ROOT), include=patterns))
    assert in_tree <= discovered, (
        f"setuptools.find_packages(include={patterns}) misses {sorted(in_tree - discovered)}"
    )



def test_distribution_name_is_not_the_taken_pypi_name():
    name = _pyproject()["project"]["name"]
    assert name != "parley", "PyPI's `parley` is an unrelated project; publish under another name"
    assert name.startswith("parley"), f"distribution {name!r} should still be findable as parley"


def test_registry_metadata_matches_the_package():
    """The MCP Registry verifies a PyPI package by an `mcp-name:` marker in the README of the
    uploaded version, and hosts launch it as `uvx <distribution>`; both break silently."""
    tomllib = pytest.importorskip("tomllib")
    root = pathlib.Path(__file__).resolve().parent.parent
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    server = json.loads((root / "server.json").read_text())
    assert f"mcp-name: {server['name']}" in (root / "README.md").read_text()
    assert server["version"] == project["version"]
    package = server["packages"][0]
    assert package["identifier"] == project["name"]
    assert package["version"] == project["version"]
    assert project["scripts"].get(project["name"]) == "parley.mcp:main"
    assert len(server["description"]) <= 100
