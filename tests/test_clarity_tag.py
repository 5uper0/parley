"""Clarity is installed cookieless, consent denied, on the production host only, and the privacy page says so."""
import pathlib

LANDING = pathlib.Path(__file__).resolve().parent.parent / "landing" / "src"


def test_layout_loads_clarity_with_consent_denied_on_prod_host_only():
    src = (LANDING / "layouts" / "Layout.astro").read_text()
    assert 'location.hostname === "parleyprotocol.com"' in src
    assert "z2wyz4offm" in src
    assert 'consentv2' in src and 'ad_Storage: "denied"' in src and 'analytics_Storage: "denied"' in src
    assert 'analytics_Storage: "granted"' not in src
    assert src.index('"clarity","script"') < src.index("consentv2") < src.index("</script>", src.index("consentv2"))
    assert src.rindex("if (location.hostname", 0, src.index("consentv2")) < src.index("consentv2")


def test_privacy_page_discloses_clarity():
    src = (LANDING / "pages" / "privacy.astro").read_text()
    assert "Microsoft Clarity" in src and "cookies switched off" in src and "strict masking" in src
    assert "GA4) and Microsoft Clarity" in src
