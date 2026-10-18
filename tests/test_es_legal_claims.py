"""The Spanish and Ukrainian pages about Spanish law may cite only the legal provisions that were checked against the BOE.

A prose rule ("only cite verified law") did not stop overclaims on earlier pages; this makes the
list mechanical. Adding a new provision means verifying it first, then extending ALLOWED_*.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "landing" / "src" / "pages"
ES_PAGES = (
    sorted((PAGES_DIR / "es").glob("*.astro"))
    + sorted((PAGES_DIR / "uk").glob("*.astro"))
    + sorted(PAGES_DIR.glob("spain-*.astro"))
)

ALLOWED_ARTICLES = {"400", "404", "5.1", "5.2", "5.3"}
ALLOWED_LAWS = {"1/2025"}

_NUM = r"\d+(?:\.\d+)?"
_ARTICLE_LIST = re.compile(
    r"(?<!\w)(?:art[íi]culos?|articles?|arts?\.?|стат\w*|ст\.?|арт\w*\.?)\s*(?:№\s*)?"
    rf"({_NUM}(?:\s*(?:,|y|e|o|і|та|и|and|or|to|–|-|al|a|до)\s*{_NUM})*)",
    re.IGNORECASE,
)
_RANGE_SEP = re.compile(r"\s*(?:–|-|al|a|to|до)\s*", re.IGNORECASE)
_LAW = re.compile(rf"(?<![\d/])\d{{1,3}}/\d{{4}}\b")


def cited_articles(text: str) -> set[str]:
    found: set[str] = set()
    for m in _ARTICLE_LIST.finditer(text):
        chunk = m.group(1)
        found.update(re.findall(_NUM, chunk))
        for lo, hi in re.findall(rf"(\d+){_RANGE_SEP.pattern}(\d+)(?!\.\d)", chunk):
            found.update(str(n) for n in range(int(lo), int(hi) + 1))
    return found


def cited_laws(text: str) -> set[str]:
    return set(_LAW.findall(text))


def test_extractor_catches_an_unverified_article():
    text = "Según el artículo 400 y el art. 1062 del Código Civil, y la Ley 5/2012."
    assert cited_articles(text) == {"400", "1062"}
    assert cited_laws(text) == {"5/2012"}


def test_extractor_reads_article_lists():
    assert cited_articles("Los artículos 5.2 y 5.3 enumeran excepciones") == {"5.2", "5.3"}


def test_extractor_reads_ukrainian_citations():
    text = "Згідно зі статтею 400 і статтею 1062, статті 5.2 і 5.3, закон 5/2012."
    assert cited_articles(text) == {"400", "1062", "5.2", "5.3"}
    assert cited_laws(text) == {"5/2012"}


def test_extractor_reads_compact_declined_and_range_forms():
    assert cited_articles("ст.1062") == {"1062"}
    assert cited_articles("art.1062 y arts. 400") == {"1062", "400"}
    assert cited_articles("статтями 400 і 404, статей 1062") == {"400", "404", "1062"}
    assert cited_articles("artículos 400 al 404") == {"400", "401", "402", "403", "404"}
    assert cited_articles("статті 400–402") == {"400", "401", "402"}


def test_extractor_reads_english_forms():
    assert cited_articles("article 400 and article 1062, articles 5.2 and 5.3") == {"400", "1062", "5.2", "5.3"}
    assert cited_articles("articles 400 to 402") == {"400", "401", "402"}


def test_law_extractor_ignores_dates():
    assert cited_laws("el 03/04/2025 y la LO 1/2025") == {"1/2025"}


def test_spanish_pages_exist():
    assert ES_PAGES, "no Spanish or Ukrainian pages found under landing/src/pages"


def test_spanish_pages_cite_only_verified_provisions():
    problems = []
    for page in ES_PAGES:
        text = page.read_text(encoding="utf-8")
        for art in sorted(cited_articles(text) - ALLOWED_ARTICLES):
            problems.append(f"{page.name}: article {art} is not on the verified list")
        for law in sorted(cited_laws(text) - ALLOWED_LAWS):
            problems.append(f"{page.name}: law {law} is not on the verified list")
    assert not problems, "\n".join(problems)
