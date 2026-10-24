"""The Spanish pages carry a neutral send-to-co-heir block with no case data in the link."""
import pathlib

LANDING = pathlib.Path(__file__).resolve().parent.parent / "landing" / "src"
PAGES = [
    "reparto-de-herencia-entre-hermanos.astro",
    "unanimidad-vender-piso-heredado.astro",
]


def test_both_spanish_pages_include_the_block():
    for name in PAGES:
        src = (LANDING / "pages" / "es" / name).read_text()
        assert "<SendToCoheir" in src, name


def test_block_has_three_routes_and_both_events():
    src = (LANDING / "components" / "SendToCoheir.astro").read_text()
    for needle in ("wa.me", "mailto:", "data-coheir-copy", "send_to_coheir_click", "share_click"):
        assert needle in src, needle


def test_block_link_carries_only_a_page_path_and_utm():
    src = (LANDING / "components" / "SendToCoheir.astro").read_text()
    assert "utm_source=coheir-share" in src
    assert "location" not in src
