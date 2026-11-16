"""The homepage receipt is engine output, not typed text.

`scripts/gen-receipt.py` runs the dinner program the page prints and writes the lines and the
transcript sha256 the page shows, plus the parley version the hero labels the run with. These tests hold that the committed file is what the engine
gives today, and that the check fails when the file, the hash or the page binding drifts.
"""
import importlib.util
import os
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
    assert len(digest) == 64 and int(digest, 16) >= 0


def test_hash_is_the_transcript_hash_and_does_not_depend_on_bobs_number():
    code = gr.sample_code()
    low, high = (gr.run_sample(code, limit) for limit in gr.LIMITS)
    assert low == high
    assert "600" not in low[1] and "899" not in high[1]


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


def test_hero_copy_takes_names_and_version_from_the_run_not_from_typing():
    with open(os.path.join(ROOT, "landing", "src", "data", "home-hero.ts"), encoding="utf-8") as f:
        hero = f.read()
    assert 'rule: "Rule: the option best for the least-happy owner wins.",' in hero
    assert "`${picked} and ${other} suit that owner equally, so the higher total wins: ${picked}.`" in hero
    assert (
        "`The group sees yes or no and a score, never a limit. ${owner}'s no on ${option} shows it is over "
        "the limit, not by how much.`"
    ) in hero
    assert "`Illustration of a real run of the dinner example, parley ${version}.`" in hero
    explainer = hero[hero.index("export const explainer") : hero.index("export const receipt")]
    rule_to_label = explainer[explainer.index("  rule:") : explainer.index("  stageAria:")]
    assert not any(word in rule_to_label for word in ("Garden", "Diner", gr.package_version()))


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
