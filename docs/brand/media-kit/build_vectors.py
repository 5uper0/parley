"""Write the Parley vector logo set (SVG) from Inter SemiBold outlines.

Run: python3 docs/brand/media-kit/build_vectors.py   (needs fonttools)
Output: docs/brand/media-kit/logo/*.svg. Geometry is in font units (UPM 2816).
"""
import pathlib

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).parent
OUT = HERE / "logo"
OUT.mkdir(exist_ok=True)
FONT = TTFont(str(HERE / "fonts" / "Inter-SemiBold.otf"))
CMAP, GS, UPM = FONT.getBestCmap(), FONT.getGlyphSet(), FONT["head"].unitsPerEm

INK, PAPER, RED = "#0A0B0D", "#F4F6F7", "#C42121"
INDIGO, GREEN, AMBER = "#4A57D6", "#14A878", "#D49A2A"
DOT_R, DOT_GAP, TRACK = 0.075 * UPM, 0.07 * UPM, -0.035 * UPM


def glyph(ch, x):
    name = CMAP[ord(ch)]
    pen = SVGPathPen(GS)
    GS[name].draw(pen)
    bp = BoundsPen(GS)
    GS[name].draw(bp)
    return pen.getCommands(), GS[name].width, bp.bounds


def path(d, x, fill):
    return f'<path transform="translate({x:.1f} 0) scale(1 -1)" d="{d}" fill="{fill}"/>'


def svg(w0, y0, w, h, body, bg=None, title="Parley"):
    rect = f'<rect x="{w0}" y="{y0}" width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{w0:.0f} {y0:.0f} {w:.0f} {h:.0f}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{rect}{body}</svg>\n')


def mark_parts(fg, dot):
    d, _, (l, b, r, t) = glyph("p", 0)
    cx = r + DOT_GAP + DOT_R
    body = path(d, 0, fg) + f'<circle cx="{cx:.1f}" cy="{-DOT_R:.1f}" r="{DOT_R:.1f}" fill="{dot}"/>'
    return body, l, r + DOT_GAP + 2 * DOT_R, -t, -b  # x0, x1, y_top, y_bottom in svg coords


def mark(fg, dot, name, bg=None, pad=0.16, rule=False, title="Parley mark"):
    body, x0, x1, ytop, ybot = mark_parts(fg, dot)
    if rule:
        ry = ybot + 195
        body += f'<rect x="{x0:.1f}" y="{ry:.1f}" width="{x1 - x0:.1f}" height="38" fill="{RED}"/>'
        ybot = ry + 38
    w, h = x1 - x0, ybot - ytop
    p = pad * max(w, h)
    (OUT / name).write_text(svg(x0 - p, ytop - p, w + 2 * p, h + 2 * p, body, bg, title))


def wordmark(fg, dot, name, bg=None):
    x, parts = 0.0, []
    for i, ch in enumerate("parley"):
        d, adv, _ = glyph(ch, x)
        parts.append(path(d, x, fg))
        x += adv + (TRACK if i < 5 else 0)
    cx = x + DOT_GAP * 0.35 + DOT_R
    parts.append(f'<circle cx="{cx:.1f}" cy="{-DOT_R:.1f}" r="{DOT_R:.1f}" fill="{dot}"/>')
viewBox="184 -2050 8335.6 2628"


def motif(name, bg=None):
    """Verdict bars on the red line, 1000 units wide."""
    bw, gap, rt = 120, 70, 12
    base = 0
    bars = [("m", 500), ("m", 340), ("f", 220), ("m", 420)]
    body, x = [], 0
    defs = (f'<defs><pattern id="h" width="22" height="22" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="22" height="22" fill="{INK}"/><rect width="7" height="22" fill="{AMBER}" opacity=".7"/></pattern></defs>')
    for kind, h in bars:
        if kind == "m":
            body.append(f'<rect x="{x}" y="{base - h}" width="{bw}" height="{h}" fill="url(#h)"/><rect x="{x}" y="{base - h}" width="{bw}" height="8" fill="{AMBER}"/>')
        else:
            body.append(f'<rect x="{x}" y="{base - h}" width="{bw}" height="{h}" fill="{INDIGO}"/>')
            tx, ty = x + bw / 2, base - h - 40
            body.append(f'<path d="M{tx - 28} {ty} l20 22 l36 -40" fill="none" stroke="{GREEN}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
        x += bw + gap
    body.append(f'<rect x="{x}" y="{base + rt}" width="{bw}" height="170" fill="none" stroke="{RED}" stroke-width="8"/>'
                f'<path d="M{x} {base + rt + 170} L{x + bw} {base + rt}" stroke="{RED}" stroke-width="8"/>')
    end = x + bw + gap
    body.append(f'<rect x="0" y="{base - rt / 2}" width="{end}" height="{rt}" fill="{RED}"/>')
    (OUT / name).write_text(svg(-60, -620, end + 120, 960, defs + "".join(body), bg, "Parley verdict bars on the red line"))


if __name__ == "__main__":
    mark(PAPER, RED, "mark-on-dark.svg")
    mark(INK, RED, "mark-on-light.svg")
    mark(PAPER, PAPER, "mark-mono-white.svg")
    mark(INK, INK, "mark-mono-ink.svg")
    mark(PAPER, RED, "mark-with-line-on-dark.svg", rule=True)
    mark(INK, RED, "mark-with-line-on-light.svg", rule=True)
    mark(PAPER, RED, "avatar-tile-dark.svg", bg=INK, pad=0.55)
    mark(INK, RED, "avatar-tile-light.svg", bg=PAPER, pad=0.55)
    wordmark(PAPER, RED, "wordmark-on-dark.svg")
    wordmark(INK, RED, "wordmark-on-light.svg")
    motif("verdict-bars-on-dark.svg")
    print(sorted(p.name for p in OUT.glob("*.svg")))
