"""The framework recipes stay valid Python and point at a recipe that exists."""
import pathlib
import py_compile

DIR = pathlib.Path(__file__).resolve().parent.parent / "examples" / "frameworks"


def test_recipes_compile_and_reference_an_existing_spec():
    scripts = sorted(DIR.glob("*_stdio.py"))
    assert len(scripts) >= 2
    for s in scripts:
        py_compile.compile(str(s), doraise=True)
        assert "recipe_committee.json" in s.read_text()
    assert (DIR.parent / "demo" / "recipe_committee.json").exists()
