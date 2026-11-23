"""Analytics (GA4 and Clarity) load only after an explicit accept, on the production host only,
and the privacy page says so."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANDING = ROOT / "landing" / "src"
CONSENT = (ROOT / "landing" / "public" / "consent.js").read_text()


def test_layout_loads_no_analytics_itself():
    src = (LANDING / "layouts" / "Layout.astro").read_text()
    assert "clarity.ms" not in src and "googletagmanager" not in src
    assert 'src="/consent.js"' in src and "z2wyz4offm" in src and "data-ga=" in src


def test_consent_script_gates_everything_on_accept_and_prod_host():
    assert 'location.hostname === "parleyprotocol.com"' in CONSENT
    assert "if (!PROD || granted) return;" in CONSENT
    # the only callers of load() are the stored-accept path and the accept button
    assert len(re.findall(r"(?<![.\w])load\(\);", CONSENT)) == 2 and 'if (v === "accepted") load();' in CONSENT
    assert 'ad_Storage: "denied"' in CONSENT
    assert CONSENT.index("function load") < CONSENT.index("clarity.ms") < CONSENT.index("function clearCookies")


def test_banner_buttons_are_symmetric_and_labelled_in_all_site_languages():
    assert CONSENT.count("<button") >= 1 and 'data-v="rejected"' in CONSENT and 'data-v="accepted"' in CONSENT
    for lang in ("en:", "es:", "uk:"):
        assert lang in CONSENT
    assert "min-height:44px" in CONSENT


def test_privacy_page_discloses_both_tools_and_the_consent_gate():
    src = (LANDING / "pages" / "privacy.astro").read_text()
    assert "Microsoft Clarity" in src and "GA4) and Microsoft Clarity" in src
    assert "Only after you accept" in src and "no request to Google or" in src
    assert "_ga" in src and "_clck" in src and "data-consent-open" in src
    assert "cookies switched off" not in src


def test_reject_and_accept_share_one_style_rule():
    css = CONSENT[CONSENT.index("#parley-consent{"):CONSENT.index("document.head.appendChild(css)")]
    assert css.count("#parley-consent button{") == 1
    for sel in ("[data-v", ":first-child", ":last-child", ":nth-", "button.", "button:not"):
        assert sel not in css
    assert "min-height:44px" in css and "opacity" not in css
    assert 'data-v="rejected"></button><button type="button" data-v="accepted"></button>' in CONSENT


def test_gtag_pushes_nothing_before_consent():
    assert "if (granted && GA) (window.dataLayer = window.dataLayer || []).push(arguments);" in CONSENT
    assert CONSENT.count("dataLayer") == 2
    assert "var granted = false;" in CONSENT


def test_banner_names_only_what_the_page_loads():
    assert "if (!CL) {" in CONSENT and '.replace(" and Microsoft Clarity", "")' in CONSENT
