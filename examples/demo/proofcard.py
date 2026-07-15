"""Render a screenshot-native "proof card" from a real Parley run — the shareable viral unit.

    python examples/demo/proofcard.py [recipe.json] [out.html]     # defaults to the KYC recipe

The Moltbook lesson: the thing people screenshot and post is one self-explanatory card. Ours is the
same shape — but *true*: agents of rival owners reached a max-min decision, one tried to cheat and was
BLOCKED by a red line, and the receipt is verifiable. Zero-dependency (stdlib only). Also the README
demo asset. `card_html()`/`STYLE` are reused by the niche gallery.
"""
import os
import sys

from server import RECIPE, run_recipe  # same dir

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


def _blocked_and_decision(data):
    decision = data.get("decision")
    blocked = [e for e in data["entries"] if not e["feasible"]]
    blocked = sorted(blocked, key=lambda e: e["option"].get("revenue", 0), reverse=True)
    return (blocked[0]["option"] if blocked else None), decision


def card_html(data: dict) -> str:
    """The card fragment (a single <div class="card">), reusable in a page or gallery."""
    blocked, decision = _blocked_and_decision(data)
    parties = " · ".join(p["owner"] for p in data["parties"])
    short_hash = data["hash"][:12] + "…"
    dec_label = decision.get("label", decision.get("id")) if decision else "HONEST DEADLOCK"
    block_html = ""
    if blocked:
        rev = blocked.get("revenue")
        rev_txt = f" (revenue {rev})" if rev is not None else ""
        block_html = (
            f'<div class="row block"><span class="mark">✕</span><div>'
            f'<b>One agent pushed "{blocked.get("label", blocked.get("id"))}"{rev_txt}</b><br>'
            f'<span class="sub">BLOCKED by a red line — rejected in code, not negotiated away.</span></div></div>')
    verified = all(data["non_betrayal"].values())
    ok_txt = "✓ verified · tamper-evident · every red line held" if verified else "unverified"
    return f"""<div class="card">
  <div class="top"><span class="logo">parley<span class="d">.</span></span><span class="hook">AI that can't lie — and you can check</span></div>
  <hr class="rule">
  <div class="scn">{data["title"]}</div>
  <div class="parties">{len(data["parties"])} rival parties: {parties} — each with private red lines</div>
  {block_html}
  <div class="row ok"><span class="mark">✓</span><div>
    <b>Agreed: "{dec_label}"</b><br>
    <span class="sub">max-min consensus — the least-happy party lifted. No one was betrayed.</span></div></div>
  <div class="receipt"><span><span style="color:var(--n500)">sha256</span> {short_hash}</span>
    <span class="ok">{ok_txt}</span></div>
  <div class="foot">parley — provable-fairness for multi-party decisions · self-hosted · no crypto · replay it yourself</div>
</div>"""


def build_card(data: dict) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">{_FONTS}'
            f'<style>{STYLE}\nbody{{background:#e7e9f0;padding:28px;display:flex;justify-content:center}}</style>'
            f'</head><body>{card_html(data)}</body></html>')


def main():
    args = sys.argv[1:]
    recipe = args[0] if args and args[0].endswith(".json") else RECIPE
    rest = [a for a in args if not a.endswith(".json")]
    out = rest[0] if rest else os.path.join(os.path.dirname(__file__), "proofcard.html")
    data = run_recipe(recipe)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_card(data))
    print(f"wrote proof-card: {out}  (decision={data['decision']['id']}, verified={all(data['non_betrayal'].values())})")


if __name__ == "__main__":
    main()
