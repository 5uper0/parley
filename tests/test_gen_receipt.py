"""The homepage receipt is engine output, not typed text.

`scripts/gen-receipt.py` runs the dinner program and writes the lines and the transcript sha256
the page shows, plus the parley version the hero status line states. These tests hold that the
committed file is what the engine gives today, and that the check fails when the file, the hash,
the page binding or a hand-typed version or run fact in the hero copy drifts.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = os.path.join(ROOT, "scripts", "gen-receipt.py")


def _load():
    spec = importlib.util.spec_from_file_location("gen_receipt", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gr = _load()


def test_sample_agrees_on_garden_and_every_owner_replays_clean():
    lines, digest, _, _, _ = gr.generate()
    assert lines == [
        "agreed {'venue': 'garden', 'cost': 600}",
        "Ana not betrayed: True",
        "Bob not betrayed: True",
        "Cara not betrayed: True",
    ]
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_receipt_is_the_same_at_both_ends_of_bobs_stated_range():
    code = gr.sample_code()
    low, high = (gr.run_sample(code, limit) for limit in gr.LIMITS)
    assert low == high


def test_a_limit_outside_the_stated_range_is_refused():
    # At 900 rooftop is feasible too, so the hero's two-option rule line would be false.
    code = gr.sample_code()
    try:
        gr.run_sample(code, 900)
    except SystemExit as exc:
        assert "shape" in str(exc)
    else:
        raise AssertionError("a run with three feasible options was accepted")


def test_verdict_grid_is_read_off_the_transcript():
    _, _, options, verdicts, _ = gr.generate()
    assert options == [
        {"venue": "rooftop", "cost": 900},
        {"venue": "garden", "cost": 600},
        {"venue": "diner", "cost": 300},
    ]
    said_no = [(v["owner"], v["option"]) for v in verdicts if not v["acceptable"]]
    assert said_no == [("Bob", "rooftop")]
    assert len(verdicts) == 9
    assert {(v["owner"], v["option"]) for v in verdicts} == {
        (o, v) for o in ("Ana", "Bob", "Cara") for v in ("rooftop", "garden", "diner")
    }


def test_generated_file_carries_no_score_or_reason():
    text = gr.render(*gr.generate())
    assert "score" not in text and "reason" not in text and "red-line" not in text
    assert all(set(v) == {"option", "owner", "acceptable"} for v in gr.generate()[3])


def test_pick_facts_garden_ties_diner_for_least_happy_and_has_higher_total():
    assert gr.generate()[4] == {
        "picked": "garden",
        "runnerUp": "diner",
        "leastHappyTie": True,
        "pickedTotalHigher": True,
    }


def _entry(venue, scores, ok=True):
    return {
        "option": {"venue": venue},
        "verdicts": [{"owner": str(i), "acceptable": ok, "score": s} for i, s in enumerate(scores)],
    }


def _refused(entries, decision):
    try:
        gr.pick_facts(entries, decision)
    except SystemExit as exc:
        return str(exc)
    return ""


def test_pick_facts_refuse_a_run_where_the_rule_line_would_be_false():
    garden, diner = _entry("garden", [0.4, 0.4, 0.9]), _entry("diner", [0.4, 0.7, 0.5])
    assert gr.pick_facts([garden, diner], {"venue": "garden"})["picked"] == "garden"
    assert "tie" in _refused([_entry("garden", [0.5, 0.5, 0.9]), diner], {"venue": "garden"})
    assert "higher total" in _refused([_entry("garden", [0.4, 0.4, 0.8]), diner], {"venue": "garden"})
    assert "shape" in _refused([garden, diner, _entry("cafe", [0.1, 0.1, 0.1])], {"venue": "garden"})
    assert "shape" in _refused([garden, _entry("diner", [0.4, 0.7, 0.5], ok=False)], {"venue": "garden"})


def test_version_is_read_from_pyproject_and_written_to_the_file():
    version = gr.package_version()
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        assert f'version = "{version}"' in f.read()
    assert f'  version: "{version}",\n' in gr.render(*gr.generate())


def test_a_version_that_is_not_three_numbers_is_refused(tmp_path):
    for body, reason in (
        ('[project]\nversion = "0.2.1"\n', ""),
        ('[project]\nversion = "0.2"\n', "not N.N.N"),
        ('[project]\nversion = "0.2.1rc1"\n', "not N.N.N"),
        ('[project]\nname = "parley"\n\n[tool.x]\nversion = "0.2.1"\n', "no [project] version"),
    ):
        path = tmp_path / "pyproject.toml"
        path.write_text(body, encoding="utf-8")
        try:
            gr.package_version(path)
        except SystemExit as exc:
            assert reason and reason in str(exc)
        else:
            assert not reason


def _hero_tree(tmp_path):
    """A copy of the hero copy file and the files that print the version, safe to tamper with."""
    hero = tmp_path / gr.HERO_COPY.name
    shutil.copy(gr.HERO_COPY, hero)
    readers = []
    for path in gr.VERSION_READERS:
        readers.append(tmp_path / path.name)
        shutil.copy(path, readers[-1])
    return hero, tuple(readers)


def _words():
    _, _, options, verdicts, _ = gr.generate()
    return gr.run_words(options, verdicts)


def _tamper(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is no longer in {path.name}; update this test"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_hero_copy_as_committed_has_no_typed_version_or_run_fact():
    # F8: the screen-reader summary and the version strings come from the run.
    assert gr.copy_problem(_words()) == ""
    assert _words() == ["Ana", "Bob", "Cara", "rooftop", "garden", "diner", "900", "600", "300"]


def test_a_typed_version_in_the_hero_status_fails_the_check(tmp_path):
    # F8: hero.status "v0.9.9" used to pass --check.
    hero, readers = _hero_tree(tmp_path)
    _tamper(hero, "`Early, version ${version},", "`Early, version 0.9.9,")
    assert "types the version 0.9.9" in gr.copy_problem(_words(), hero, readers)


def test_a_typed_version_in_the_status_section_fails_the_check(tmp_path):
    # F8: Status.astro "version 0.7.0" used to pass --check.
    hero, readers = _hero_tree(tmp_path)
    status = next(p for p in readers if p.name == "Status.astro")
    _tamper(status, "version ${receiptDinner.version}.", "version 0.7.0.")
    assert "types the version 0.7.0" in gr.copy_problem(_words(), hero, readers)


def test_a_version_that_is_not_read_from_the_run_fails_the_check(tmp_path):
    # F8: dropping the generated version without typing a new one is still drift.
    hero, readers = _hero_tree(tmp_path)
    for path in readers:
        _tamper(path, "receiptDinner.version", "receiptDinner.sha256")
    assert "does not read receiptDinner.version" in gr.copy_problem(_words(), hero, readers)


def test_a_hand_typed_screen_reader_summary_fails_the_check(tmp_path):
    # F8: stageAria "Rooftop costs 500 ... Diner is picked" used to pass --check.
    hero, readers = _hero_tree(tmp_path)
    _tamper(hero, "${plain} ${picked} is picked.", "${plain} Diner is picked.")
    assert "types 'diner'" in gr.copy_problem(_words(), hero, readers)
    hero, readers = _hero_tree(tmp_path)
    _tamper(hero, "stageAria: (owners: string, plain: string, picked: string) =>\n    `", 'stageAria:\n    "')
    assert "not a template filled from the run" in gr.copy_problem(_words(), hero, readers)


def test_check_fails_on_tampered_hero_copy(tmp_path, monkeypatch):
    # F8, end to end: --check itself exits 1, not only the helper.
    hero, readers = _hero_tree(tmp_path)
    _tamper(hero, "`Early, version ${version},", "`Early, version 0.9.9,")
    monkeypatch.setattr(gr, "HERO_COPY", hero)
    monkeypatch.setattr(gr, "VERSION_READERS", readers)
    monkeypatch.setattr(gr.copy_problem, "__defaults__", (hero, readers))
    monkeypatch.setattr(sys, "argv", ["gen-receipt.py", "--check"])
    assert gr.main() == 1


def test_hero_copy_wording_is_the_approved_text():
    # F1 to F3, F5, F6: the truth fixes stay in the copy file.
    hero = gr.HERO_COPY.read_text(encoding="utf-8")
    for line in (
        'rule: "Rule: the option best for the least-happy owner wins.",',
        "`${picked} and ${other} suit that owner equally, so the higher total wins: ${picked}.`",
        'reveal: "The group sees yes or no and a score, never the limit itself. Many yeses and noes can still narrow it down.",',
        'sampleLabel: "Illustration of a recorded sample run.",',
        "envelope: (owner: string) => `${owner}'s sheet`,",
        "\"Each person's agent holds a private sheet of wishes and limits, sealed.\"",
        '"Each owner checks the pick against their own sheet, on their own computer. Compare the sha256 to confirm it is the same receipt."',
        '"For developers building agents that act for different people."',
        "nobody hands over their limit sheet",
    ):
        assert line in hero, line
    for gone in ("own limit", "Same receipt", "same receipt for", "AI assistant", "proves", "docs/_drafts"):
        assert gone not in hero, gone


def test_install_section_prints_no_number_for_bobs_limit():
    # F4: the page whose hero says the limit stays sealed must not print it.
    install = (gr.PAGE.parent / "Install.astro").read_text(encoding="utf-8")
    assert 'o["cost"] <= limit)' in install
    assert not re.search(r"<= *\d", install)


def test_committed_file_matches_the_generator():
    assert gr.OUT.read_text(encoding="utf-8") == gr.render(*gr.generate())


def test_check_passes_on_the_committed_tree():
    env = dict(os.environ, PYTHONPATH=ROOT)
    proc = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert "transcript sha256: " in proc.stdout


def test_check_fails_on_a_drifted_hash(tmp_path, monkeypatch):
    lines, _, options, verdicts, pick = gr.generate()
    stale = tmp_path / "receipt-dinner.ts"
    stale.write_text(gr.render(lines, "0" * 64, options, verdicts, pick), encoding="utf-8")
    monkeypatch.setattr(gr, "OUT", stale)
    monkeypatch.setattr(sys, "argv", ["gen-receipt.py", "--check"])
    assert gr.main() == 1


def test_check_fails_when_the_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "OUT", tmp_path / "absent.ts")
    monkeypatch.setattr(sys, "argv", ["gen-receipt.py", "--check"])
    assert gr.main() == 1


def test_check_fails_on_a_drifted_version(tmp_path, monkeypatch):
    stale = tmp_path / "receipt-dinner.ts"
    stale.write_text(gr.render(*gr.generate(), version="9.9.9"), encoding="utf-8")
    monkeypatch.setattr(gr, "OUT", stale)
    monkeypatch.setattr(sys, "argv", ["gen-receipt.py", "--check"])
    assert gr.main() == 1


def test_check_fails_on_a_flipped_verdict(tmp_path, monkeypatch):
    lines, digest, options, verdicts, pick = gr.generate()
    flipped = [dict(v, acceptable=True) for v in verdicts]
    stale = tmp_path / "receipt-dinner.ts"
    stale.write_text(gr.render(lines, digest, options, flipped, pick), encoding="utf-8")
    monkeypatch.setattr(gr, "OUT", stale)
    monkeypatch.setattr(sys, "argv", ["gen-receipt.py", "--check"])
    assert gr.main() == 1


def test_page_must_render_the_generated_hash(tmp_path):
    assert gr.page_problem() == ""
    assert "missing" in gr.page_problem(tmp_path / "Receipt.astro")
    unbound = tmp_path / "unbound.astro"
    unbound.write_text("<p>sha256 abc</p>", encoding="utf-8")
    assert "does not render" in gr.page_problem(unbound)
    typed = tmp_path / "typed.astro"
    typed.write_text(
        'import { receiptDinner } from "../../data/receipt-dinner";\n'
        "{receiptDinner.sha256} " + "a" * 64,
        encoding="utf-8",
    )
    assert "hardcodes" in gr.page_problem(typed)


def test_a_sample_that_no_longer_runs_as_printed_is_refused(tmp_path):
    copy = tmp_path / "film-copy.ts"
    copy.write_text("export const codeSample = {\n  code: `print(${x})`,\n};\n", encoding="utf-8")
    try:
        gr.sample_code(copy)
    except SystemExit as exc:
        assert "runs as printed" in str(exc)
    else:
        raise AssertionError("an interpolated template literal was accepted")
