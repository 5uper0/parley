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


def test_static_build_emits_committee_replay_page(tmp_path):
    """The replay page is the stable URL posts and catalog listings link: a finished synthetic
    run with the full transcript hash, no form, no signup, and the command to rerun it."""
    build = _load_build_module()
    out = tmp_path / "static-demo"
    build.OUT = out
    build.main()
    page = (out / "replay" / "committee" / "index.html").read_text(encoding="utf-8")
    from examples.demo.server import run_recipe
    data = run_recipe(os.path.join(_ROOT, "examples", "demo", "recipe_committee.json"))
    assert data["hash"] in page
    assert "https://parleyprotocol.com/demo/replay/committee/" in page
    assert "recipe_committee.json" in page
    assert "git clone https://github.com/5uper0/parley" in page
    assert os.path.exists(os.path.join(_ROOT, "examples", "demo", "proofcard.py"))
    assert os.path.exists(os.path.join(_ROOT, "examples", "demo", "recipe_committee.json"))
    for party in data["parties"]:
        for redline in party["redlines"]:
            assert redline not in page
    assert "<form" not in page and "<input" not in page
    import re
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", page)


def test_card_escapes_recipe_text():
    from examples.demo.proofcard import card_html
    from examples.demo.server import run_recipe
    data = run_recipe(os.path.join(_ROOT, "examples", "demo", "recipe_committee.json"))
    data["title"] = "<script>x</script>"
    assert "<script>" not in card_html(data)


def test_static_build_emits_spanish_heirs_replay_page(tmp_path):
    """Public Spanish page: invented case, the legal line, no citation outside the verified set,
    nothing collected, no private limit text."""
    import re
    build = _load_build_module()
    out = tmp_path / "static-demo"
    build.OUT = out
    build.main()
    page = (out / "replay" / "herencia-hermanos" / "index.html").read_text(encoding="utf-8")
    from examples.demo.server import run_recipe
    from tests.test_es_legal_claims import ALLOWED_ARTICLES, ALLOWED_LAWS, cited_articles, cited_laws
    data = run_recipe(os.path.join(_ROOT, "examples", "demo", "recipe_herencia_hermanos.json"))
    assert '<html lang="es">' in page
    assert data["hash"] in page
    assert data["status"] == "agreed"
    assert "No es asesoramiento jurídico" in page
    assert "inventado" in page
    text = re.sub(r"<[^>]+>", " ", page)
    assert cited_articles(text) <= ALLOWED_ARTICLES
    assert cited_laws(text) <= ALLOWED_LAWS
    assert "<form" not in page and "<input" not in page
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", page)
    for party in data["parties"]:
        for redline in party["redlines"]:
            assert redline not in page
    recipe = open(os.path.join(_ROOT, "examples", "demo", "recipe_herencia_hermanos.json"),
                  encoding="utf-8").read()
    assert '"url"' not in recipe and '"source"' not in recipe


def test_blocked_example_prefers_the_option_marked_tempting():
    from examples.demo.proofcard import _blocked_and_decision
    entries = [
        {"option": {"id": "a", "revenue": 9}, "feasible": False},
        {"option": {"id": "b", "revenue": 1}, "feasible": False},
    ]
    data = {"entries": entries, "decision": None,
            "presentation": {"options": {"b": {"tempting": True}}}}
    assert _blocked_and_decision(data)[0]["id"] == "b"
    del data["presentation"]
    assert _blocked_and_decision(data)[0]["id"] == "a"
