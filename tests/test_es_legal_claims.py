"""The Spanish pages may cite only the legal provisions that were checked against the BOE.

A prose rule ("only cite verified law") did not stop overclaims on earlier pages; this makes the
list mechanical. Adding a new provision means verifying it first, then extending ALLOWED_*.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ES_PAGES = sorted((ROOT / "landing" / "src" / "pages" / "es").glob("*.astro"))

ALLOWED_ARTICLES = {"400", "404", "5.1", "5.2", "5.3"}
ALLOWED_LAWS = {"1/2025"}

_ARTICLE_LIST = re.compile(
    r"\b(?:art[íi]culos?|arts?\.)\s+(\d+(?:\.\d+)?(?:\s*(?:,|y|e|o)\s*\d+(?:\.\d+)?)*)",
    re.IGNORECASE,
)
_LAW = re.compile(r"\b\d{1,3}/\d{4}\b")


def cited_articles(text: str) -> set[str]:
    found: set[str] = set()
    for m in _ARTICLE_LIST.finditer(text):
        found.update(re.findall(r"\d+(?:\.\d+)?", m.group(1)))
    return found


def cited_laws(text: str) -> set[str]:
    return set(_LAW.findall(text))


def test_extractor_catches_an_unverified_article():
    text = "Según el artículo 400 y el art. 1062 del Código Civil, y la Ley 5/2012."
    assert cited_articles(text) == {"400", "1062"}
    assert cited_laws(text) == {"5/2012"}


def test_extractor_reads_article_lists():
    assert cited_articles("Los artículos 5.2 y 5.3 enumeran excepciones") == {"5.2", "5.3"}


def test_spanish_pages_exist():
    assert ES_PAGES, "no Spanish pages found under landing/src/pages/es"


def test_spanish_pages_cite_only_verified_provisions():
    problems = []
    for page in ES_PAGES:
        text = page.read_text(encoding="utf-8")
        for art in sorted(cited_articles(text) - ALLOWED_ARTICLES):
            problems.append(f"{page.name}: article {art} is not on the verified list")
        for law in sorted(cited_laws(text) - ALLOWED_LAWS):
            problems.append(f"{page.name}: law {law} is not on the verified list")
    assert not problems, "\n".join(problems)
