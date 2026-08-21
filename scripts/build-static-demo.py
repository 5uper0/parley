#!/usr/bin/env python3
"""Pre-render the money-shot demo as a fully STATIC site (no server, no Docker).

The demo API is deterministic over a fixed whitelist of recipes, so every `/api/run?recipe=X`
response can be baked to a static JSON file. This emits a static tree that deploys to Vercel /
Cloudflare Pages / any static host with zero backend:

    build/
      index.html            # the demo page, fetches rewritten to static paths
      api/recipes.json      # = list_recipes()
      api/run/<key>.json     # = run_recipe(path) for each whitelisted recipe

Usage: scripts/build-static-demo.py [out_dir]   (default: build/static-demo)
"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from examples.demo.server import RECIPES, HERE, run_recipe, list_recipes, _recipe_path  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/static-demo")

# Analytics is injected at build time rather than committed into index.html, so the published
# demo source carries no tracking tag and a contributor building locally is not silently
# instrumented. Opt in with PARLEY_GA4_ID; unset means no analytics.
GA4_ID = os.environ.get("PARLEY_GA4_ID", "")
GA4_SNIPPET = """<script async src="https://www.googletagmanager.com/gtag/js?id={id}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{id}');</script>
<script>document.addEventListener('click',function(e){{var el=e.target.closest&&e.target.closest('.cta,.btn,.vbtn,a[href]');if(!el)return;if(el.matches('.vbtn')){{gtag('event','demo_verify_click',{{transport_type:'beacon'}});}}else if(el.matches('.cta,.btn')){{gtag('event','demo_run_click',{{transport_type:'beacon',cta_location:el.matches('.cta')?'hero':'panel'}});}}else{{var h=el.getAttribute('href')||'';if(el.matches('.arena-btn')){{gtag('event','arena_interest_click',{{transport_type:'beacon'}});}}else if(/github\\.com\\/5uper0\\/parley\\/discussions/.test(h)){{gtag('event','discussions_click',{{transport_type:'beacon'}});}}else if(/github\\.com\\/5uper0\\/parley/.test(h)){{gtag('event','github_click',{{transport_type:'beacon'}});}}else if(/linkedin\\.com/.test(h)){{gtag('event','linkedin_click',{{transport_type:'beacon'}});}}}}}});</script>"""
# The `.arena-btn` check runs BEFORE the discussions-href regex on purpose: the Arena fake-door
# CTA links into /discussions too, and arena_interest_click must fire INSTEAD OF the generic
# discussions_click so the interest signal is attributable to that CTA alone (a footer
# Discussions click still logs discussions_click as before).

# Static files copied verbatim into the deploy root alongside index.html.
_ASSETS = Path(HERE).parent.parent / "docs" / "brand" / "assets"
STATIC_COPIES = {
    Path(HERE, "robots.txt"): "robots.txt",
    Path(HERE, "sitemap.xml"): "sitemap.xml",
    Path(HERE, "privacy.html"): "privacy.html",
    _ASSETS / "og-card.png": "og-card.png",
    _ASSETS / "og-card-demo.png": "og-card-demo.png",
    # index.html <head> links these; manifest.json additionally needs icon-192/512.
    _ASSETS / "favicon" / "favicon.svg": "favicon.svg",
    _ASSETS / "favicon" / "favicon-16.png": "favicon-16.png",
    _ASSETS / "favicon" / "favicon-32.png": "favicon-32.png",
    _ASSETS / "favicon" / "apple-touch-icon.png": "apple-touch-icon.png",
    _ASSETS / "favicon" / "icon-192.png": "icon-192.png",
    _ASSETS / "favicon" / "icon-512.png": "icon-512.png",
    _ASSETS / "manifest.json": "manifest.json",
    _ASSETS / "llms.txt": "llms.txt",
    # Orphan-but-live URLs: nothing on the site links these, but they are served today and
    # the proof cards were built to be shared, so a deploy that dropped them would 404 links
    # already in the wild. Cloudflare Pages replaces the whole tree, so absent means deleted.
    Path(HERE, "proofcard_p2p.html"): "proofcard_p2p.html",
    Path(HERE, "proofcard_dao.html"): "proofcard_dao.html",
    Path(HERE, "proofcard_estate_real.html"): "proofcard_estate_real.html",
    Path(HERE, "proofcard_partnership.html"): "proofcard_partnership.html",
    _ASSETS / "proofcard.png": "proofcard.png",
    _ASSETS / "parley-money-shot.gif": "parley-money-shot.gif",
    _ASSETS.parent / "built-by-a-fleet.html": "built-by-a-fleet.html",
}


def main():
    out = OUT.resolve()
    (out / "api" / "run").mkdir(parents=True, exist_ok=True)

    (out / "api" / "recipes.json").write_text(
        json.dumps(list_recipes(), ensure_ascii=False), encoding="utf-8")

    for key in RECIPES:
        result = run_recipe(_recipe_path(key))
        (out / "api" / "run" / f"{key}.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8")

    # Rewrite the two fetches from server routes to static files.
    html = Path(HERE, "index.html").read_text(encoding="utf-8")
    html = html.replace("fetch('/api/recipes')", "fetch('/api/recipes.json')")
    html = html.replace(
        "fetch('/api/run?recipe='+encodeURIComponent(key))",
        "fetch('/api/run/'+encodeURIComponent(key)+'.json')")
    if GA4_ID:
        marker = "<head>"
        assert marker in html, "index.html has no <head> to inject analytics into"
        html = html.replace(marker, marker + "\n" + GA4_SNIPPET.format(id=GA4_ID), 1)
    (out / "index.html").write_text(html, encoding="utf-8")

    for src, name in STATIC_COPIES.items():
        if src.exists():
            shutil.copy2(src, out / name)
        else:
            print(f"  ! skipped missing static file: {src}")

    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    print(f"✓ static demo → {out}")
    for f in files:
        print(f"  {f}")


if __name__ == "__main__":
    main()
