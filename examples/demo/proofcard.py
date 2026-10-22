"""Render a screenshot-native "proof card" from a real Parley run — the shareable viral unit.

    python examples/demo/proofcard.py [recipe.json] [out.html]     # defaults to the KYC recipe

The Moltbook lesson: the thing people screenshot and post is one self-explanatory card. Ours is the
same shape — but *true*: agents of rival owners reached a max-min decision, one tried to cheat and was
BLOCKED by a red line, and the receipt is verifiable. Zero-dependency (stdlib only). Also the README
demo asset. `card_html()`/`STYLE` are reused by the niche gallery.
"""
import html
import os
import sys

from server import RECIPE, run_recipe  # same dir

# The cards deploy under /demo/ of the merged site (scripts/build-static-demo.py copies them
# verbatim; scripts/build-site.sh only rewrites index.html), so absolute URLs are final here.
SITE = "https://parleyprotocol.com"
OG_IMAGE = f"{SITE}/demo/og-card-demo.png"

STYLE = """
:root{--indigo-600:#3A45B0;--verify-600:#0E8F63;--verify-sub:#E7F6EF;--redline-600:#C42121;
--redline-sub:#FCEAEA;--n0:#FFFFFF;--n100:#EDEFF3;--n200:#DCE0E8;--n500:#6B7383;--n600:#4A5163;--n900:#12151C;
--sans:'Inter',system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace}
*{margin:0;box-sizing:border-box}
.card{width:680px;max-width:100%;background:var(--n0);border:1px solid var(--n200);border-radius:16px;padding:32px 34px;box-shadow:0 12px 40px rgba(18,21,28,.14)}
.card .top{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.card .logo{font-size:26px;font-weight:600;letter-spacing:-.02em;color:var(--n900);font-family:var(--sans)}.card .logo .d{color:var(--redline-600)}
.card .hook{font-size:13.5px;color:var(--n600);font-weight:500;font-family:var(--sans)}
.card .rule{border:none;border-top:2px solid var(--redline-600);margin:18px 0 20px;opacity:.9}
.card .scn{font-size:20px;font-weight:700;color:var(--n900);letter-spacing:-.01em;font-family:var(--sans)}
.card .parties{font-size:13px;color:var(--n500);margin-top:4px;font-family:var(--sans)}
.card .row{display:flex;gap:13px;align-items:flex-start;padding:13px 15px;border-radius:12px;margin-top:14px;font-family:var(--sans)}
.card .row.block{background:var(--redline-sub)}.card .row.ok{background:var(--verify-sub)}
.card .row b{color:var(--n900);font-size:15px}.card .row .sub{font-size:13px;color:var(--n600)}
.card .mark{font-family:var(--mono);font-weight:700;font-size:18px;line-height:1.4}
.card .row.block .mark{color:var(--redline-600)}.card .row.ok .mark{color:var(--verify-600)}
.card .receipt{margin-top:20px;background:var(--n100);border-radius:10px;padding:13px 15px;font-family:var(--mono);font-size:12.5px;color:var(--n600);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.card .receipt .ok{color:var(--verify-600);font-weight:700}
.card .foot{margin-top:20px;font-size:12px;color:var(--n500);font-family:var(--sans)}
"""

_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&'
          'family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">')


_ES = {
    "hook": "Decisiones entre partes con límites privados, y tú puedes comprobarlas",
    "blocked": "BLOQUEADA por un límite privado: se rechaza en el código, no se negocia.",
    "pushed": "Alguien propuso",
    "parties": "partes con intereses distintos",
    "private": "cada una con límites privados",
    "agreed": "Elegida",
    "agreed_sub": "criterio max-min: se mejora la situación de la parte menos favorecida. Ningún límite privado se cruzó.",
    "ok": "✓ verificado · detecta alteraciones · ningún límite cruzado",
    "bad": "sin verificar",
    "foot": "parley · decisiones entre varias partes · autoalojado · sin cripto · repítelo tú mismo",
    "title": "Parley, tarjeta de prueba",
    "said": "Qué dijo cada agente",
    "option": "Opción",
    "acceptable": "aceptable, puntuación",
    "redline": "límite privado",
    "masked": "Solo estos veredictos enmascarados salen de un agente. El coordinador nunca ve la hoja de preferencias ni qué límite se activó.",
    "receipt": "Recibo",
    "fullhash": "SHA-256 completo del registro canónico:",
    "notauth": "Este recibo muestra que el registro no se ha alterado. No demuestra quién produjo cada veredicto salvo que se active la firma.",
    "run": "Compruébalo tú mismo",
    "match": "Los 12 primeros caracteres del hash de tu tarjeta coinciden con el de arriba. La receta es inventada para esta demostración: ninguna persona, caso ni dato real.",
    "source": "Código",
    "demo": "Demo interactiva",
    "legal": "Herramienta para ordenar la conversación entre coherederos. No es asesoramiento jurídico y no sustituye a un notario, mediador o abogado. El caso de esta página es inventado.",
}
_EN = {
    "hook": "AI that can't lie — and you can check",
    "blocked": "BLOCKED by a red line — rejected in code, not negotiated away.",
    "pushed": "One agent pushed",
    "parties": "rival parties",
    "private": "each with private red lines",
    "agreed": "Agreed",
    "agreed_sub": "max-min consensus — the least-happy party lifted. No one was betrayed.",
    "ok": "✓ verified · tamper-evident · every red line held",
    "bad": "unverified",
    "foot": "parley — provable-fairness for multi-party decisions · self-hosted · no crypto · replay it yourself",
    "title": "Parley proof card",
    "said": "What each agent said",
    "option": "Option",
    "acceptable": "acceptable, score",
    "redline": "red line",
    "masked": "Only these masked verdicts leave an agent. The coordinator never sees a preference sheet or which red line fired.",
    "receipt": "Receipt",
    "fullhash": "Full SHA-256 of the canonical transcript:",
    "notauth": "This receipt shows the record was not altered. It does not prove who produced a verdict unless signing is on.",
    "run": "Run it yourself",
    "match": "The first 12 characters of the hash on your card match the one above. The recipe is invented for this demo: no real person, case or data.",
    "source": "Source",
    "demo": "Interactive demo",
    "legal": "",
}
LANGS = {"en": _EN, "es": _ES}


def _blocked_and_decision(data):
    decision = data.get("decision")
    blocked = [e for e in data["entries"] if not e["feasible"]]
    tempting = (data.get("presentation") or {}).get("options") or {}
    blocked = sorted(blocked, key=lambda e: (bool(tempting.get(e["option"].get("id"), {}).get("tempting")),
                                             e["option"].get("revenue", 0)), reverse=True)
    return (blocked[0]["option"] if blocked else None), decision


def card_html(data: dict, lang: str = "en") -> str:
    """The card fragment (a single <div class="card">), reusable in a page or gallery."""
    blocked, decision = _blocked_and_decision(data)
    e = html.escape
    T = LANGS[lang]
    parties = " · ".join(e(p["owner"]) for p in data["parties"])
    short_hash = data["hash"][:12] + "…"
    dec_label = e(str(decision.get("label", decision.get("id")))) if decision else "HONEST DEADLOCK"
    block_html = ""
    if blocked:
        rev = blocked.get("revenue")
        rev_txt = f" (revenue {rev})" if rev is not None else ""
        block_html = (
            f'<div class="row block"><span class="mark">✕</span><div>'
            f'<b>{T["pushed"]} "{e(str(blocked.get("label", blocked.get("id"))))}"{rev_txt}</b><br>'
            f'<span class="sub">{T["blocked"]}</span></div></div>')
    verified = all(data["non_betrayal"].values())
    ok_txt = T["ok"] if verified else T["bad"]
    return f"""<div class="card">
  <div class="top"><span class="logo">parley<span class="d">.</span></span><span class="hook">{T["hook"]}</span></div>
  <hr class="rule">
  <div class="scn">{e(data["title"])}</div>
  <div class="parties">{len(data["parties"])} {T["parties"]}: {parties} — {T["private"]}</div>
  {block_html}
  <div class="row ok"><span class="mark">✓</span><div>
    <b>{T["agreed"]}: "{dec_label}"</b><br>
    <span class="sub">{T["agreed_sub"]}</span></div></div>
  <div class="receipt"><span><span style="color:var(--n500)">sha256</span> {short_hash}</span>
    <span class="ok">{ok_txt}</span></div>
  <div class="foot">{T["foot"]}</div>
</div>"""


def _head_meta(data: dict, path, lang: str = "en") -> str:
    """Title/description/canonical/OG/Twitter, derived from the scenario data (same tag shape as
    landing/src/layouts/Layout.astro). Nothing here touches the card body."""
    _, decision = _blocked_and_decision(data)
    dec_label = decision.get("label", decision.get("id")) if decision else "HONEST DEADLOCK"
    parties = " · ".join(p["owner"] for p in data["parties"])
    title = f'{data["title"]} · {LANGS[lang]["title"]}'
    situation = (data.get("presentation") or {}).get("situation")
    description = situation or (
        f'{len(data["parties"])} rival parties ({parties}) reached "{dec_label}" by max-min '
        f'consensus. Every private red line held; the receipt is verifiable.')
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    url = f"{SITE}{path}" if path else None
    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{t}</title>',
        f'<meta name="description" content="{d}">',
    ]
    if url:
        tags.append(f'<link rel="canonical" href="{url}">')
    tags.append('<meta property="og:type" content="website">')
    if url:
        tags.append(f'<meta property="og:url" content="{url}">')
    tags += [
        '<meta property="og:site_name" content="Parley">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:description" content="{d}">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
    ]
    return "\n".join(tags)


def build_card(data: dict, path: str = None) -> str:
    """Full page. `path` is the site-relative URL the card is served at (e.g. /demo/proofcard_p2p);
    it drives the canonical + og:url tags and is omitted from the head when unknown."""
    return (f'<!doctype html><html lang="en"><head>\n{_head_meta(data, path)}\n{_FONTS}'
            f'<style>{STYLE}\nbody{{background:#e7e9f0;padding:28px;display:flex;justify-content:center}}</style>'
            f'</head><body>{card_html(data)}</body></html>')


def replay_html(data: dict, path: str, recipe: str, lang: str = "en") -> str:
    """The stable, no-signup replay page: the card, the per-option verdicts, the full hash and the
    command to reproduce it. Same engine output as the card; nothing is typed in by hand."""
    T = LANGS[lang]
    rows = []
    for e in data["entries"]:
        opt = e["option"]
        label = html.escape(str(opt.get("label", opt.get("id"))))
        cells = "".join(
            f'<td class="{"y" if v["acceptable"] else "n"}">'
            f'{T["acceptable"] + " " + str(v["score"]) if v["acceptable"] else T["redline"]}</td>'
            for v in e["verdicts"])
        rows.append(f"<tr><th>{label}</th>{cells}</tr>")
    heads = "".join(f'<th>{html.escape(p["owner"])}</th>' for p in data["parties"])
    style = (STYLE + "\nbody{background:#e7e9f0;padding:28px;font-family:var(--sans);color:var(--n900)}"
             ".wrap{max-width:680px;margin:0 auto}.wrap h2{font-size:16px;margin:26px 0 8px}"
             ".wrap p,.wrap li{font-size:14px;color:var(--n600);line-height:1.5}"
             ".wrap table{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--n0)}"
             ".wrap td,.wrap th{border:1px solid var(--n200);padding:7px 9px;text-align:left}"
             ".wrap td.n{color:var(--redline-600)}.wrap td.y{color:var(--verify-600)}"
             ".wrap pre{background:var(--n900);color:#fff;padding:12px 14px;border-radius:8px;"
             "overflow-x:auto;font-size:12.5px}.wrap code.h{word-break:break-all;font-family:var(--mono)}")
    legal = f'<p class="legal"><b>{html.escape(T["legal"])}</b></p>' if T["legal"] else ""
    return (f'<!doctype html><html lang="{lang}"><head>\n{_head_meta(data, path, lang)}\n{_FONTS}'
            f'<style>{style}</style></head><body><div class="wrap">'
            f'{legal}{card_html(data, lang)}'
            f'<h2>{T["said"]}</h2>'
            f'<table><tr><th>{T["option"]}</th>{heads}</tr>{"".join(rows)}</table>'
            f'<p>{T["masked"]}</p>'
            f'<h2>{T["receipt"]}</h2><p>{T["fullhash"]}</p>'
            f'<p><code class="h">{data["hash"]}</code></p>'
            f'<p>{T["notauth"]}</p>'
            f'<h2>{T["run"]}</h2><pre>git clone https://github.com/5uper0/parley\n'
            f'cd parley &amp;&amp; pip install -e .\n'
            f'python examples/demo/proofcard.py examples/demo/{recipe} card.html</pre>'
            f'<p>{T["match"]} '
            f'<a href="https://github.com/5uper0/parley">{T["source"]}</a> · '
            f'<a href="/demo/">{T["demo"]}</a></p>'
            f'</div></body></html>')


def main():
    args = sys.argv[1:]
    recipe = args[0] if args and args[0].endswith(".json") else RECIPE
    rest = [a for a in args if not a.endswith(".json")]
    out = rest[0] if rest else os.path.join(os.path.dirname(__file__), "proofcard.html")
    data = run_recipe(recipe)
    # Cards are served extensionless under /demo/ (see scripts/build-static-demo.py).
    slug = os.path.splitext(os.path.basename(out))[0]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_card(data, path=f"/demo/{slug}"))
    print(f"wrote proof-card: {out}  (decision={data['decision']['id']}, verified={all(data['non_betrayal'].values())})")


if __name__ == "__main__":
    main()
