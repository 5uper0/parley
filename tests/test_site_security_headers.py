"""landing/public/_headers ships the security headers Cloudflare Pages serves for every path."""
from pathlib import Path

HEADERS = (Path(__file__).resolve().parents[1] / "landing" / "public" / "_headers").read_text()


def _value(name):
    for line in HEADERS.splitlines():
        if line.strip().startswith(name + ":"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"{name} missing from _headers")


def test_required_headers_present():
    for name in ("Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
                 "Permissions-Policy", "X-Content-Type-Options", "Referrer-Policy"):
        _value(name)


def test_csp_forbids_framing_and_plugins():
    csp = _value("Content-Security-Policy")
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp


def test_csp_allows_the_analytics_the_layout_loads():
    csp = _value("Content-Security-Policy")
    for origin in ("https://www.googletagmanager.com", "https://www.clarity.ms",
                   "https://*.google-analytics.com", "https://fonts.googleapis.com",
                   "https://fonts.gstatic.com"):
        assert origin in csp
