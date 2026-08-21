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


def test_footer_links_to_the_privacy_page():
    index = os.path.join(_ROOT, "examples", "demo", "index.html")
    with open(index, encoding="utf-8") as fh:
        html = fh.read()
    assert 'href="/privacy"' in html


def test_root_only_files_are_not_duplicated_under_the_demo_build():
    """privacy.html/sitemap.xml/robots.txt/llms.txt are root-only in the merged deploy tree
    (landing/src/pages/privacy.astro + landing/public/*) — scripts/build-site.sh copies them
    in exactly once. A demo-local copy of any of these previously drifted silently (stale
    design tokens, a sitemap missing /demo/ prefixes) since nothing kept two copies in sync;
    guard against it coming back."""
    build = _load_build_module()
    for name in ("privacy.html", "sitemap.xml", "robots.txt", "llms.txt"):
        assert name not in build.STATIC_COPIES.values(), (
            f"{name} should not be emitted by the demo build — it belongs at the merged "
            "site's root only (see scripts/build-site.sh)"
        )


def test_static_build_emits_manifest_with_root_absolute_paths(tmp_path):
    """The demo build itself is intentionally NOT /demo/-aware (it doesn't know it'll be
    merged under a subpath) — scripts/build-site.sh rewrites these to /demo/-prefixed paths
    afterward. This test pins the PRE-rewrite shape so that rewrite has something correct to
    rewrite from."""
    build = _load_build_module()
    out = tmp_path / "static-demo"
    build.OUT = out
    build.main()
    manifest = (out / "manifest.json").read_text(encoding="utf-8")
    assert '"start_url": "/"' in manifest
    assert '"/icon-192.png"' in manifest
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="/manifest.json"' in index
