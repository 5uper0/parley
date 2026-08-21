"""The static build is what actually deploys to parleyprotocol.com — keep its output honest."""
import importlib.util
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCRIPT = os.path.join(_ROOT, "scripts", "build-static-demo.py")


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_static_demo", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_static_demo"] = module
    spec.loader.exec_module(module)
    return module


def test_privacy_page_is_wired_into_the_static_copy_list():
    build = _load_build_module()
    assert "privacy.html" in build.STATIC_COPIES.values()
    src = next(k for k, v in build.STATIC_COPIES.items() if v == "privacy.html")
    assert src.exists()


def test_footer_links_to_the_privacy_page():
    index = os.path.join(_ROOT, "examples", "demo", "index.html")
    with open(index, encoding="utf-8") as fh:
        html = fh.read()
    assert 'href="/privacy"' in html


def test_static_build_emits_privacy_html(tmp_path):
    build = _load_build_module()
    out = tmp_path / "static-demo"
    build.OUT = out
    build.main()
    assert (out / "privacy.html").is_file()
    assert (out / "sitemap.xml").is_file()
    assert "parleyprotocol.com/privacy" in (out / "sitemap.xml").read_text(encoding="utf-8")
