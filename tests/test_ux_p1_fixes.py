"""Held at source level: the UX pilot P1 fixes (design-dept audits/ux-pilot-parley, WI-261116-217).

ux-parley-1: /demo/ speaks the 2026-11-17 identity and does not contradict the home page.
ux-parley-2: a primary-action fill behind white text clears 4.5:1 in both themes.
Home acceptance items: "recorded sample run" wording, closing CTA, FAQ summary height.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "landing" / "src"
DEMO = (ROOT / "examples" / "demo" / "index.html").read_text(encoding="utf-8")
HOME = (SRC / "pages" / "index.astro").read_text(encoding="utf-8")
CSS = (SRC / "styles" / "global.css").read_text(encoding="utf-8")


def _ratio(fg: str, bg: str) -> float:
    def lum(h):
        h = h.lstrip("#")
        c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _version() -> str:
    return re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)


def _demo_visible_source() -> str:
    return "\n".join(line for line in DEMO.splitlines() if not line.startswith("const FALLBACK"))


def test_ux1_demo_has_no_old_identity_claims():
    text = _demo_visible_source()
    for phrase in ("can't lie", "Your AI speaks for you", "no one was cheated", "KYC", "AML", "DORA", "audit-ready", "Provable"):
        assert phrase not in text, phrase


def test_ux1_demo_states_the_one_liner_scope_and_install():
    assert "Agents that act for different people can agree without anyone handing over their limit." in DEMO
    assert f"Early, version {_version()}, no outside users yet." in DEMO
    assert "pip install parley-consensus" in DEMO
    assert "scripted sample runs" in DEMO


def test_ux1_demo_has_no_uppercase_or_wide_tracked_labels_and_no_green():
    css = DEMO[DEMO.index("<style>") : DEMO.index("</style>")]
    assert "text-transform:uppercase" not in css
    assert "--verify" not in css


def test_ux2_primary_fill_behind_white_clears_aa_in_both_themes():
    solids = re.findall(r"--indigo-solid:\s*(#[0-9a-fA-F]{6})", CSS)
    assert len(solids) == 2
    assert all(_ratio("#ffffff", s) >= 7.0 for s in solids)
    demo_solids = re.findall(r"--indigo-solid:(#[0-9A-Fa-f]{6})", DEMO)
    assert len(demo_solids) == 2 and all(_ratio("#ffffff", s) >= 7.0 for s in demo_solids)


def test_ux2_no_white_label_sits_on_the_raw_indigo_token():
    for path in SRC.rglob("*.astro"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"bg-indigo(?![-\w])", text), path


def test_home_uses_recorded_sample_run_wording():
    assert "real run" not in HOME.lower() and "real transcript" not in HOME.lower()
    assert "recorded transcript" in HOME
    assert "See a recorded run" in HOME and "Put your next decision" not in HOME


def test_home_faq_summaries_are_at_least_44px_tall():
    summary = re.search(r'<summary class="([^"]+)"', HOME).group(1)
    assert "py-2.5" in summary and "-my-2" in summary  # 24px line + 20px padding
