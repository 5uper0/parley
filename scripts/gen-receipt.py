"""Generate landing/src/data/receipt-dinner.ts from a real run of the dinner sample.

The homepage shows a receipt next to the dinner scene. Its lines and its sha256 must be what
the engine prints, not text someone typed, so this script takes the exact code the page shows
(`codeSample.code` in landing/src/data/film-copy.ts), runs it against this tree's `parley`
package and reads the decision, each owner's replay and `Transcript.hash()` off the result.
The hero draws the option cards and a yes/no grid, so the options and each transcript verdict
are written too. A verdict is owner, option and `acceptable` only: scores and reasons stay out
of the file. The hero also says why garden beats diner (they tie for the least-happy owner, garden
has the higher total); `pick_facts` reads that off the transcript and refuses to write the file
when it stops being true. The page promises the same output for any Bob limit from 600 to 899; both ends are run and a
difference is an error, so that promise is checked too.

    .venv/bin/python scripts/gen-receipt.py           # rewrite receipt-dinner.ts, print the sha256
    .venv/bin/python scripts/gen-receipt.py --check   # exit 1 if the file or the page is stale
"""
import argparse
import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

COPY = REPO_ROOT / "landing" / "src" / "data" / "film-copy.ts"
OUT = REPO_ROOT / "landing" / "src" / "data" / "receipt-dinner.ts"
PAGE = REPO_ROOT / "landing" / "src" / "components" / "home" / "Receipt.astro"
REGEN = ".venv/bin/python scripts/gen-receipt.py"
LIMITS = (600, 899)
OWNERS = ("ana", "bob", "cara")

Rows = List[Dict[str, object]]
Run = Tuple[List[str], str, Rows, Rows, Dict[str, object]]


def sample_code(copy_path: Path = COPY) -> str:
    """The dinner program exactly as the page prints it."""
    text = copy_path.read_text(encoding="utf-8")
    block = re.search(r"export const codeSample\b.*?\n};", text, re.DOTALL)
    match = block and re.search(r"\n  code: `(.*?)`,\n", block.group(0), re.DOTALL)
    if not match:
        raise SystemExit(f"no codeSample.code template literal in {copy_path}")
    code = match.group(1)
    if "\\" in code or "${" in code:
        raise SystemExit("codeSample.code uses an escape or interpolation; it no longer runs as printed")
    return code


def run_sample(code: str, limit: int) -> Run:
    """Run the program with Bob's limit in bob_limit.txt.

    Returns (printed lines, transcript sha256, options as recorded, every verdict as option,
    owner, acceptable, and the pick facts).
    """
    scope: dict = {"__name__": "__dinner__"}
    stdout = io.StringIO()
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "bob_limit.txt").write_text(str(limit), encoding="utf-8")
        os.chdir(tmp)
        try:
            with contextlib.redirect_stdout(stdout):
                exec(compile(code, "dinner.py", "exec"), scope)
        finally:
            os.chdir(cwd)
    result = scope["result"]
    lines = stdout.getvalue().splitlines()
    for name in OWNERS:
        sheet = scope[name]
        held = result.transcript.verify_non_betrayal(sheet, result.decision)
        lines.append(f"{sheet.owner} not betrayed: {held}")
    verdicts = [
        {"option": entry["option"]["venue"], "owner": v["owner"], "acceptable": v["acceptable"]}
        for entry in result.transcript.entries
        for v in entry["verdicts"]
    ]
    options = [dict(entry["option"]) for entry in result.transcript.entries]
    return lines, result.transcript.hash(), options, verdicts, pick_facts(result.transcript.entries, result.decision)


def pick_facts(entries: Rows, decision: Dict[str, object]) -> Dict[str, object]:
    """Why the picked option beat the other one everyone accepted, as two facts and no numbers.

    The hero prints "tie for the least-happy owner, higher total". That is only true while exactly
    two options are feasible, their lowest scores are equal and the picked one has the larger sum.
    """
    feasible = [e for e in entries if all(v["acceptable"] for v in e["verdicts"])]
    if len(feasible) != 2 or decision not in [e["option"] for e in feasible]:
        raise SystemExit("the hero explains a pick between two feasible options; the run no longer has that shape")
    won = next(e for e in feasible if e["option"] == decision)
    lost = next(e for e in feasible if e["option"] != decision)
    floor = lambda e: min(v["score"] for v in e["verdicts"])
    total = lambda e: sum(v["score"] for v in e["verdicts"])
    if floor(won) != floor(lost):
        raise SystemExit("the picked option and the runner-up no longer tie for the least-happy owner; the hero rule line is wrong")
    if not total(won) > total(lost):
        raise SystemExit("the picked option no longer has the higher total; the hero rule line is wrong")
    return {
        "picked": won["option"]["venue"],
        "runnerUp": lost["option"]["venue"],
        "leastHappyTie": True,
        "pickedTotalHigher": True,
    }


def generate(copy_path: Path = COPY) -> Run:
    code = sample_code(copy_path)
    runs = [run_sample(code, limit) for limit in LIMITS]
    if any(run != runs[0] for run in runs[1:]):
        raise SystemExit(f"the dinner sample gives different receipts for Bob limits {LIMITS}")
    return runs[0]


def ts_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(lines: List[str], digest: str, options: Rows, verdicts: Rows, pick: Dict[str, object]) -> str:
    body = "\n".join(f"    {ts_string(line)}," for line in lines)
    cards = "\n".join(
        f"    {{ venue: {ts_string(o['venue'])}, cost: {int(o['cost'])} }}," for o in options
    )
    grid = "\n".join(
        f"    {{ option: {ts_string(v['option'])}, owner: {ts_string(v['owner'])}, "
        f"acceptable: {'true' if v['acceptable'] else 'false'} }},"
        for v in verdicts
    )
    return (
        f"// GENERATED by scripts/gen-receipt.py from a real parley run. Do not edit by hand.\n"
        f"// Regenerate: {REGEN}\n"
        f"// Source program: codeSample.code in film-copy.ts, Bob limits {LIMITS[0]} and {LIMITS[1]}.\n"
        f"\n"
        f"export const receiptDinner = {{\n"
        f"  output: [\n{body}\n  ],\n"
        f"  sha256: {ts_string(digest)},\n"
        f"  options: [\n{cards}\n  ],\n"
        f"  verdicts: [\n{grid}\n  ],\n"
        f"  pick: {{ picked: {ts_string(pick['picked'])}, runnerUp: {ts_string(pick['runnerUp'])}, "
        f"leastHappyTie: {'true' if pick['leastHappyTie'] else 'false'}, "
        f"pickedTotalHigher: {'true' if pick['pickedTotalHigher'] else 'false'} }},\n"
        f"}} as const;\n"
    )


def page_problem(page_path: Path = PAGE) -> str:
    """Why the page does not show the generated receipt, or '' when it does."""
    if not page_path.exists():
        return f"{page_path} is missing, so no page shows the receipt"
    text = page_path.read_text(encoding="utf-8")
    if "receipt-dinner" not in text or "receiptDinner.sha256" not in text:
        return f"{page_path} does not render receiptDinner.sha256 from receipt-dinner.ts"
    if re.search(r"\b[0-9a-f]{64}\b", text):
        return f"{page_path} hardcodes a sha256 instead of reading receipt-dinner.ts"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="don't write; fail if the receipt is stale")
    args = parser.parse_args()

    lines, digest, options, verdicts, pick = generate()
    ts = render(lines, digest, options, verdicts, pick)

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != ts:
            print(f"STALE: {OUT} differs from generator output", file=sys.stderr)
            return 1
        problem = page_problem()
        if problem:
            print(f"STALE: {problem}", file=sys.stderr)
            return 1
        print(f"up to date: {OUT}")
    else:
        OUT.write_text(ts, encoding="utf-8")
        print(f"wrote {OUT}")
    print("\n".join(lines))
    print(f"transcript sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
