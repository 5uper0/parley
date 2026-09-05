"""Generate landing/src/data/tape.ts from a real parley run.

The Receipt Tape on the landing page must not show invented digests: the site's
whole pitch is "provable, not hoped". So the tape is produced by running the real
engine (`run_consensus`) over a fixed five-owner scenario and reading every
number off the real `Transcript`. Each `sha256` line is `Transcript.hash()`
taken right after that round's `record()`; the closing one is the hash after
`finalize()`. Re-running this script reproduces the file byte for byte.

    .venv/bin/python landing/scripts/gen-tape.py            # rewrite tape.ts, print final sha256
    .venv/bin/python landing/scripts/gen-tape.py --digests  # also print every per-round digest
    .venv/bin/python landing/scripts/gen-tape.py --check    # exit 1 if tape.ts is stale
"""
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from parley.agent import Agent  # noqa: E402
from parley.consensus import run_consensus, verify_outcome  # noqa: E402
from parley.preferences import HardConstraint, PreferenceSheet  # noqa: E402
from parley.transcript import Transcript  # noqa: E402

OUT = REPO_ROOT / "landing" / "src" / "data" / "tape.ts"
REGEN = ".venv/bin/python landing/scripts/gen-tape.py"

# The public agenda: five colleagues picking a recurring sync slot. Letters are
# the labels the tape prints; the slot is what the sheets actually evaluate.
AGENDA: List[Tuple[str, str, int]] = [
    ("A", "mon", 9),
    ("B", "tue", 14),
    ("C", "wed", 11),
    ("D", "thu", 15),
    ("E", "fri", 15),
    ("F", "tue", 17),
    ("G", "wed", 14),
    ("H", "thu", 13),
    ("I", "mon", 15),
    ("J", "tue", 15),
    ("K", "wed", 16),
    ("L", "thu", 10),
    ("M", "wed", 15),
    ("N", "tue", 13),
    ("O", "fri", 14),
    ("P", "thu", 14),
]
OPTIONS: List[Dict[str, Any]] = [{"id": i, "day": d, "hour": h} for i, d, h in AGENDA]


def clamp2(x: float) -> float:
    return round(max(0.0, min(1.0, x)), 2)


def day_pref(table: Dict[str, float], default: float):
    return lambda o: table.get(o["day"], default)


# Private sheets. Red lines are code predicates; soft utility only ranks what
# already clears every red line. Scores are rounded to two decimals so the
# transcript (and therefore its hash) has no float-repr noise.
def build_agents() -> List[Agent]:
    ana_day = day_pref({"tue": 1.0, "thu": 0.8}, 0.6)
    cara_day = day_pref({"wed": 1.0, "tue": 0.8}, 0.7)
    eve_day = day_pref({"thu": 1.0, "wed": 0.75}, 0.6)
    sheets = [
        PreferenceSheet(
            "ana",
            hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 11)],
            utility=lambda o: clamp2(ana_day(o) - 0.05 * abs(o["hour"] - 14)),
        ),
        PreferenceSheet(
            "bob",
            hard=[HardConstraint("no-fridays", lambda o: o["day"] != "fri")],
            utility=lambda o: clamp2(1.0 - 0.1 * abs(o["hour"] - 15) - (0.1 if o["day"] == "mon" else 0.0)),
        ),
        PreferenceSheet(
            "cara",
            hard=[HardConstraint("kids-pickup", lambda o: o["hour"] <= 16)],
            utility=lambda o: clamp2(cara_day(o) - (0.2 if o["hour"] == 16 else 0.0)),
        ),
        PreferenceSheet(
            "dan",
            hard=[HardConstraint("no-mondays", lambda o: o["day"] != "mon")],
            utility=lambda o: clamp2(1.0 - 0.15 * abs(o["hour"] - 14)),
        ),
        PreferenceSheet(
            "eve",
            hard=[HardConstraint("afternoons-only", lambda o: o["hour"] >= 13)],
            utility=lambda o: clamp2(eve_day(o) - 0.05 * abs(o["hour"] - 15)),
        ),
    ]
    return [Agent(s.owner, s) for s in sheets]


def short(digest: str) -> str:
    return f"{digest[:8]}…{digest[-8:]}"


def leader_so_far(entries) -> Any:
    """Same selection rule as run_consensus/verify_outcome, over the rounds recorded so far."""
    feasible = []
    for e in entries:
        vs = e["verdicts"]
        if vs and all(v["acceptable"] for v in vs):
            feasible.append((e["option"], min(v["score"] for v in vs), sum(v["score"] for v in vs)))
    if not feasible:
        return None
    return max(feasible, key=lambda x: (x[1], x[2]))[0]


def run():
    agents = build_agents()
    result = run_consensus(agents, OPTIONS)
    assert result.status == "agreed", result.status
    assert verify_outcome(result.transcript)

    # Replay the same run round by round through a fresh Transcript so the
    # running hash after each record() is observable; then prove it converges
    # on exactly the engine's own transcript.
    replay = Transcript()
    rounds = []
    for option in OPTIONS:
        verdicts = [a.consider(option) for a in agents]
        replay.record(option, verdicts)
        entries = replay.entries
        feasible = all(v.acceptable for v in verdicts)
        held = sum(replay.verify_non_betrayal(a.sheet, option) for a in agents) if feasible else 0
        rounds.append({
            "option": option,
            "verdicts": [(v.owner, v.reason) for v in verdicts],
            "feasible": feasible,
            "leader": leader_so_far(entries)["id"] if feasible else None,
            "held": held,
            "digest": replay.hash(),
        })
    replay.finalize(result.status, result.decision)
    assert replay.entries == result.transcript.entries
    final_digest = replay.hash()
    assert final_digest == result.transcript.hash()
    final_held = sum(result.transcript.verify_non_betrayal(a.sheet, result.decision) for a in agents)
    assert final_held == len(agents)
    return rounds, result, final_digest, final_held, agents


def tape_lines(rounds, result, final_digest, final_held, n_owners):
    lines = []
    for i, r in enumerate(rounds, start=1):
        lines.append((f"round {i} · option {r['option']['id']} proposed", "dim"))
        for owner, reason in r["verdicts"]:
            lines.append((f"{owner} → verdict: {reason}", "muted" if reason == "ok" else "redline"))
        if r["feasible"]:
            lines.append((f"max-min so far → option {r['leader']}", "indigo"))
            lines.append((f"sha256 {short(r['digest'])}", "dim"))
            lines.append((f"✓ red lines hold for {r['held']}/{n_owners} owners", "verify"))
        else:
            lines.append((f"option {r['option']['id']} infeasible", "dim"))
    lines.append((f"max-min → option {result.decision['id']} · {result.status}", "indigo"))
    lines.append((f"sha256 {short(final_digest)}", "dim"))
    lines.append((f"✓ verified by {final_held}/{n_owners} owners", "verify"))
    # The tape loops; it wraps into the replay's first round mid-flight. Only
    # verdicts the run actually produced are shown — the rest are "awaiting".
    first = rounds[0]
    lines.append((f"round 1 · option {first['option']['id']} proposed", "dim"))
    for owner, reason in first["verdicts"][:2]:
        lines.append((f"{owner} → verdict: {reason}", "muted" if reason == "ok" else "redline"))
    pending = ", ".join(o for o, _ in first["verdicts"][2:])
    lines.append((f"awaiting {pending}…", "masked"))
    return lines


def tape_snippet(rounds, n_owners):
    """One line of every color, all lifted from the real rounds."""
    blocked = next((i, r) for i, r in enumerate(rounds, start=1) if not r["feasible"])
    passed = next((i, r) for i, r in enumerate(rounds, start=1) if r["feasible"])
    bi, br = blocked
    pi, pr = passed
    first_ok = next(i for i, (_, reason) in enumerate(br["verdicts"]) if reason == "ok")
    first_red = next(i for i, (_, reason) in enumerate(br["verdicts"]) if reason != "ok")
    ok_in_passed = pr["verdicts"][1][0]
    following = rounds[pi]  # the round after `passed`, shown still in flight
    fi = pi + 1
    blocked_lines = [
        (f"{br['verdicts'][i][0]} → verdict: {br['verdicts'][i][1]}", "muted" if br["verdicts"][i][1] == "ok" else "redline")
        for i in sorted((first_ok, first_red))
    ]
    return [
        (f"round {bi} · option {br['option']['id']} proposed", "dim"),
        *blocked_lines,
        (f"option {br['option']['id']} infeasible", "dim"),
        (f"round {pi} · option {pr['option']['id']} proposed", "dim"),
        (f"{ok_in_passed} → verdict: ok", "muted"),
        (f"max-min so far → option {pr['leader']}", "indigo"),
        (f"sha256 {short(pr['digest'])}", "dim"),
        (f"✓ red lines hold for {pr['held']}/{n_owners} owners", "verify"),
        (f"round {fi} · option {following['option']['id']} proposed", "dim"),
        (f"awaiting {', '.join(o for o, _ in following['verdicts'][1:3])}…", "masked"),
    ]


def ts_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(rounds, result, final_digest, final_held, agents) -> str:
    n = len(agents)
    agenda = "\n".join(
        f" *   {i} = {d} {h:02d}:00" for i, d, h in AGENDA
    )
    owners = ", ".join(a.owner for a in agents)
    lines = tape_lines(rounds, result, final_digest, final_held, n)
    snippet = tape_snippet(rounds, n)

    def block(name: str, doc: str, items) -> str:
        body = "\n".join(f"  {{ text: {ts_string(t)}, color: {ts_string(c)} }}," for t, c in items)
        return f"{doc}export const {name}: TapeLine[] = [\n{body}\n];\n"

    header = f"""/* GENERATED FILE — do not edit by hand. Regenerate with:
 *
 *   {REGEN}
 *
 * The Receipt Tape dataset, replayed from a REAL parley run: five owners
 * (ana, bob, cara, dan, eve) with private red lines, {len(AGENDA)} proposals, decided by
 * the real engine (`parley.consensus.run_consensus`). Nothing here is typed
 * in — every verdict, every max-min pick and every digest is read off the
 * `Transcript` the engine produced.
 *
 * Each `sha256` line is `Transcript.hash()` taken right after that round's
 * `record()` (result still unset); the closing one is the hash after
 * `finalize()`. Shown as the first and last 8 hex chars of the full digest.
 *
 * Final transcript sha256 (full):
 *   {final_digest}
 * Decision: option {result.decision['id']} ({result.decision['day']} {result.decision['hour']:02d}:00), status "{result.status}",
 * red lines held for {final_held}/{n} owners on replay (`verify_non_betrayal`).
 *
 * Agenda (option → slot):
{agenda}
 *
 * Color semantics map 1:1 to the product: redline = deterministic BLOCK,
 * muted = ok, indigo = max-min pick, dim = bookkeeping, verify = the owners'
 * ✓, masked = a round still in progress (not yet resolved).
 *
 * NOTE: `Verdict.reason` on the wire is only ever "ok" | "red-line"
 * (parley/agent.py) — "masked" describes the PROPERTY that a reason never
 * names the constraint, it is never itself a verdict value. Don't add a
 * third literal verdict here; that would misrepresent the real product on
 * the one page whose whole pitch is "provable, not hoped". */

export type TapeColor = "dim" | "muted" | "redline" | "indigo" | "verify" | "masked";

export interface TapeLine {{
  text: string;
  color: TapeColor;
}}

/** Tape color → Tailwind text utility (semantic tokens from global.css).
 * All tape text is <18px, so every color here must clear WCAG AA's 4.5:1
 * for small text — redline/indigo use the lightened -text variants
 * (redline-300/indigo-300 primitives) since the base brand tones are
 * 4.33:1/4.47:1 on the tape's surface bg, just under the bar. `dim` uses
 * `muted` rather than `subtle` for the same reason (subtle is 3.90:1 here). */
export const tapeColorClass: Record<TapeColor, string> = {{
  dim: "text-muted",
  muted: "text-muted",
  redline: "text-redline-text",
  masked: "text-masked",
  indigo: "text-indigo-text",
  verify: "text-verify",
}};

"""
    owners_doc = f"/** The full run: {len(rounds)} rounds, owners {owners}, then the tape wraps. */\n"
    snippet_doc = "/** Compact excerpt for the mobile Proof card — one line of every color. */\n"
    return header + block("tapeLines", owners_doc, lines) + "\n" + block("tapeSnippet", snippet_doc, snippet)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digests", action="store_true", help="print every per-round digest")
    parser.add_argument("--check", action="store_true", help="don't write; fail if tape.ts is stale")
    args = parser.parse_args()

    rounds, result, final_digest, final_held, agents = run()
    ts = render(rounds, result, final_digest, final_held, agents)

    if args.digests:
        for i, r in enumerate(rounds, start=1):
            print(f"round {i:2d} option {r['option']['id']}  {r['digest']}")
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != ts:
            print(f"STALE: {OUT} differs from generator output", file=sys.stderr)
            return 1
        print(f"up to date: {OUT}")
    else:
        OUT.write_text(ts, encoding="utf-8")
        print(f"wrote {OUT}")
    print(f"final transcript sha256: {final_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
