#!/usr/bin/env python3
"""WCAG contrast of the landing's text tokens on its backgrounds, read from global.css.
Body text needs 4.5:1 (anti-slop gate item 25). Exit 1 if any text pair is below it."""
import re, sys, pathlib

css = pathlib.Path(__file__).resolve().parent.parent / "landing/src/styles/global.css"
text = css.read_text()

def block(selector):
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", text, re.S)
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)))

def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

bad = 0
for name, sel in (("dark", ":root"), ("light", ':root[data-theme="light"]')):
    t = block(sel)
    for fg in ("ink", "muted", "subtle", "indigo-text", "redline-text", "verify"):
        if fg not in t:
            continue
        for bg in ("bg", "surface"):
            r = ratio(t[fg], t[bg])
            ok = r >= 4.5
            bad += not ok
            print(f"{name:5} {fg:13} on {bg:8} {t[fg]} {t[bg]} {r:5.2f}:1 {'PASS' if ok else 'FAIL'}")

demo = (css.parent.parent.parent.parent / "examples/demo/index.html").read_text()
for name, sel in (("dark", ":root{"), ("light", ':root[data-theme="light"]{')):
    i = demo.index(sel)
    t = {k.lower(): v.upper() for k, v in re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", demo[i:demo.index("}", i)])}
    if name == "light":
        t = {**dark_demo, **t}
    else:
        dark_demo = t
    for fg in ("ink", "muted", "dim"):
        for bg in ("bg", "surface"):
            r = ratio(t[fg], t[bg])
            ok = r >= 4.5
            bad += not ok
            print(f"demo {name:5} {fg:13} on {bg:8} {t[fg]} {t[bg]} {r:5.2f}:1 {'PASS' if ok else 'FAIL'}")
sys.exit(1 if bad else 0)
