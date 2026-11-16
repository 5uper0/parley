"""One identity across the README and the site, held at source level.

The spec (design-dept specs/2026-11-17-parley-identity-unification.md) fixes one sentence for the
README subtitle and the home H1, one term ("agents") and a list of words the copy may not use,
because each of them claims more than the code does: the transcript publishes scores and
accept or reject flags, so the copy says "handing over" and never "prove" or "secure". A negated
limit sentence or a quote of real program output may keep a listed word only when its exact line
is in specs/parley-banned-allowlist.txt. Each test carries the acceptance criterion it implements;
AC2 and AC3 need a browser and are not here.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SRC = ROOT / "landing" / "src"
ALLOWLIST = ROOT / "specs" / "parley-banned-allowlist.txt"
HOME = SRC / "pages" / "index.astro"

S = "Agents that act for different people can agree without anyone handing over their limit."
SUB = (
    "Parley is an open-source Python library. Each person's hard limits run as code: an option over "
    "anyone's limit cannot win, nobody hands over their limit sheet, and every result leaves a record "
    "anyone can check."
)
CAPTION = (
    "Early, version {version}, no outside users yet. Scores and accept or reject answers still show "
    "some of each person's range. It picks from a given list of options and is not built for owners "
    "who try to cheat."
)
INSTALL = "pip install parley-consensus"
SAMPLE_LABEL = "Illustration of a recorded sample run."

BANNED = re.compile(
    r"\b(secure|securely|trustless|proves?|proving|proven|guarantees?|trust layer|agent economy|"
    r"kyc|aml|sanctions?|real decision)\b",
    re.IGNORECASE,
)
ASSISTANT = re.compile(r"\bassistants?\b", re.IGNORECASE)
TEXT_SUFFIXES = {".astro", ".ts", ".tsx", ".js", ".mjs", ".md", ".json", ".html"}
# The home page is rewritten by its own change; until it lands, its checks are expected to fail.
# Remove this marker with that change.
HOME_PENDING = pytest.mark.xfail(reason="home hero rewrite (index.astro) has not landed yet", strict=False)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _site_files():
    files = []
    for folder in ("pages", "components", "data", "layouts"):
        files += [p for p in sorted((SRC / folder).rglob("*")) if p.is_file() and p.suffix in TEXT_SUFFIXES]
    return files


def _allowlist():
    entries = set()
    for raw in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([^:]+):(\d+): (.+)", line)
        assert match, f"allowlist entry is not 'file:line: text': {line!r}"
        entries.add((match.group(1), int(match.group(2)), match.group(3)))
    return entries


def _hits(paths, pattern):
    found = set()
    for path in paths:
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(text):
                found.add((_rel(path), number, text.strip()))
    return found


def _first_line(text: str, needle: str) -> int:
    lines = [n for n, line in enumerate(text.splitlines(), 1) if needle in line]
    assert lines, f"{needle!r} is not on any single line"
    return lines[0]


def _version() -> str:
    return re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE).group(1)


def test_ac1_readme_opens_with_the_one_liner_the_sub_line_and_the_install_command():
    text = README.read_text(encoding="utf-8")
    one_liner, sub, install = (_first_line(text, needle) for needle in (S, SUB, INSTALL))
    assert one_liner <= 20 and install <= 20
    assert one_liner < sub < install


def test_ac1_readme_scope_caption_states_the_version_in_pyproject():
    text = README.read_text(encoding="utf-8")
    assert _first_line(text, CAPTION.format(version=_version())) <= 20


def test_ac1_readme_names_no_regulated_first_users():
    text = README.read_text(encoding="utf-8")
    assert "People building agents that act for different people" in text
    assert "regulated" not in text.lower()


def test_ac1_banned_words_appear_only_on_allowlisted_lines():
    paths = [README] + [p for p in _site_files() if p != HOME]
    hits = _hits(paths, BANNED) | _hits(paths, ASSISTANT)
    allowed = {entry for entry in _allowlist() if entry[0] != _rel(HOME)}
    assert hits - allowed == set(), "reword these lines or list them in specs/parley-banned-allowlist.txt"
    assert allowed - hits == set(), "allowlist entries that match no banned line; remove or update them"


@HOME_PENDING
def test_ac2_home_source_has_banned_words_only_on_allowlisted_lines():
    hits = _hits([HOME], BANNED)
    allowed = {entry for entry in _allowlist() if entry[0] == _rel(HOME)}
    assert hits == allowed


def test_ac4_film_sample_label_is_the_exact_string():
    hero = (SRC / "data" / "home-hero.ts").read_text(encoding="utf-8")
    assert f'  sampleLabel: "{SAMPLE_LABEL}",\n' in hero
    stage = (SRC / "components" / "home" / "HeroExplainer.astro").read_text(encoding="utf-8")
    assert "data-sample-label>{x.sampleLabel}</p>" in stage
    film = (SRC / "pages" / "film.astro").read_text(encoding="utf-8")
    home = SRC / "components" / "home"
    assert "<HomeV3 />" in film
    assert "<Hero />" in (home / "HomeV3.astro").read_text(encoding="utf-8")
    assert "<HeroExplainer />" in (home / "Hero.astro").read_text(encoding="utf-8")


def test_ac5_no_assistant_in_readme_film_copy_labels_or_alt_text():
    paths = [README] + [p for p in _site_files() if p != HOME]
    assert _hits(paths, ASSISTANT) == set()


@HOME_PENDING
def test_ac5_no_assistant_in_home_source():
    assert _hits([HOME], ASSISTANT) == set()


def test_ac7_readme_carries_the_one_liner_once_byte_for_byte():
    assert README.read_bytes().count(S.encode("utf-8")) == 1


@HOME_PENDING
def test_ac7_home_h1_source_carries_the_same_bytes():
    assert HOME.read_bytes().count(S.encode("utf-8")) >= 1
