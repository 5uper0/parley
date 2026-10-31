"""The framework recipes stay valid Python and only call tools and keys that parley-mcp really has."""
import pathlib
import py_compile

from parley import mcp

DIR = pathlib.Path(__file__).resolve().parent.parent / "examples" / "frameworks"


def test_recipes_compile_and_reference_an_existing_spec():
    scripts = sorted(DIR.glob("*_stdio.py"))
    assert len(scripts) >= 2
    for s in scripts:
        py_compile.compile(str(s), doraise=True)
        assert "recipe_committee.json" in s.read_text()
    assert (DIR.parent / "demo" / "recipe_committee.json").exists()


def test_recipes_call_only_real_tools_and_output_keys():
    names = {t["name"] for t in mcp.TOOLS}
    out = mcp.tool_decide({"spec": __import__("json").loads((DIR.parent / "demo" / "recipe_committee.json").read_text())})
    for s in DIR.glob("*_stdio.py"):
        src = s.read_text()
        for tool in ("parley_decide", "parley_verify_receipt"):
            assert tool in names and tool in src, (s.name, tool)
        for key in ("decision", "transcript", "transcript_sha256"):
            assert key in out and f'"{key}"' in src, (s.name, key)


def test_pydantic_ai_recipe_uses_the_mcp_client_without_a_model_key():
    src = (DIR / "pydantic_ai_stdio.py").read_text()
    py_compile.compile(str(DIR / "pydantic_ai_stdio.py"), doraise=True)
    assert "MCPToolset" in src and "StdioTransport" in src
    assert "direct_call_tool" in src and "list_tools" in src
    assert "Agent(" not in src


def test_google_adk_recipe_uses_the_mcp_toolset_without_a_model_key():
    path = DIR / "google_adk_stdio.py"
    src = path.read_text()
    py_compile.compile(str(path), doraise=True)
    assert "McpToolset" in src and "StdioConnectionParams" in src
    assert "run_async" in src and "get_tools" in src
    assert "Agent(" not in src and "Runner(" not in src


def test_crewai_recipe_uses_the_mcp_adapter_without_a_model_key():
    src = (DIR / "crewai_stdio.py").read_text()
    py_compile.compile(str(DIR / "crewai_stdio.py"), doraise=True)
    assert "MCPServerAdapter" in src and "StdioServerParameters" in src
    assert ".run(" in src and "parley-mcp" in src
    assert "Agent(" not in src and "Crew(" not in src
