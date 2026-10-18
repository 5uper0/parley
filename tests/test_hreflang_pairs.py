"""hreflang alternates must be reciprocal and include the page itself.

Search engines ignore an alternate that the other page does not confirm, so a one-way
declaration silently does nothing. Reads the page sources; no build needed.
"""
import pathlib
import re

PAGES = pathlib.Path(__file__).resolve().parent.parent / "landing" / "src" / "pages"
_PATH = re.compile(r'^\s*path="([^"]+)"', re.MULTILINE)
_ALT_BLOCK = re.compile(r"alternates=\{\[(.*?)\]\}", re.DOTALL)
_ALT = re.compile(r'\{\s*lang:\s*"([^"]+)",\s*path:\s*"([^"]+)"\s*\}')


def _file_for(path: str) -> pathlib.Path:
    return PAGES / (path.strip("/") + ".astro")


def _declared() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for page in PAGES.rglob("*.astro"):
        text = page.read_text(encoding="utf-8")
        block = _ALT_BLOCK.search(text)
        if not block:
            continue
        own = _PATH.search(text)
        assert own, f"{page.name}: alternates without a path"
        out[own.group(1)] = {lang: p for lang, p in _ALT.findall(block.group(1))}
    return out


def test_some_page_declares_alternates():
    assert _declared(), "no page declares hreflang alternates"


def test_alternates_include_self_and_are_reciprocal():
    declared = _declared()
    problems = []
    for path, alts in declared.items():
        if path not in alts.values():
            problems.append(f"{path}: missing its own entry")
        for lang, target in alts.items():
            if not _file_for(target).exists():
                problems.append(f"{path}: alternate {target} has no page")
            elif path not in declared.get(target, {}).values():
                problems.append(f"{path}: {target} does not list it back")
    assert not problems, "\n".join(problems)
