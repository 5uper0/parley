"""Demo: three people let their agents pick a meeting slot.

Each owner hands their agent PRIVATE constraints they don't want to reveal. The
agents reach a decision that respects everyone's red lines, and each owner then
proves locally that their agent never betrayed them — without exposing the sheet.

    python examples/meeting.py
"""
from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent
from parley.consensus import run_consensus


def label(o):
    return f'{o["day"].capitalize()} {o["hour"]:02d}:00'


OPTIONS = [
    {"day": "mon", "hour": 9},
    {"day": "mon", "hour": 15},
    {"day": "tue", "hour": 11},
    {"day": "tue", "hour": 17},
    {"day": "fri", "hour": 15},
    {"day": "wed", "hour": 14},
]

# --- private sheets (each owner keeps these to themselves) ---
ana = Agent("Ana", PreferenceSheet(
    "Ana",
    hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 11)],   # school run
    utility=lambda o: 1.0 if o["day"] == "tue" else 0.5,
))
bob = Agent("Bob", PreferenceSheet(
    "Bob",
    hard=[HardConstraint("no-fridays", lambda o: o["day"] != "fri")],  # travels Fri
    utility=lambda o: 1.0 if o["hour"] == 15 else 0.5,
))
cara = Agent("Cara", PreferenceSheet(
    "Cara",
    hard=[HardConstraint("kids-pickup", lambda o: o["hour"] <= 16)],   # pickup at 16:30
    utility=lambda o: 1.0 if o["day"] == "mon" else 0.5,
))

AGENTS = [ana, bob, cara]


def show(result):
    print("\n  Proposals the agents weighed (only masked verdicts are shared):")
    for e in result.transcript.entries:
        marks = "   ".join(
            f'{v["owner"]} {"✓" if v["acceptable"] else "✗ red-line"}'
            for v in e["verdicts"]
        )
        print(f'    {label(e["option"]):>12}   {marks}')
    print()
    if result.status == "agreed":
        print(f"  ✅ Consensus: {label(result.decision)}")
    else:
        print("  ⛔ Honest deadlock — no slot clears everyone's red lines. Nothing forced.")
    print(f"  transcript sha256: {result.transcript.hash()[:16]}…  (tamper-evident)")

    print("\n  Each owner privately proves their agent was not betrayed:")
    for a in AGENTS:
        ok = result.transcript.verify_non_betrayal(a.sheet, result.decision)
        print(f'    {a.owner:>5}: red lines held? {"yes ✓" if ok else "NO ✗"}')


if __name__ == "__main__":
    print("=" * 60)
    print("  PARLEY — consensus among agents with conflicting private interests")
    print("=" * 60)
    show(run_consensus(AGENTS, OPTIONS))

    print("\n" + "-" * 60)
    print("  Now add Dan, whose red line is 'Fridays only' (conflicts with Bob):")
    dan = Agent("Dan", PreferenceSheet(
        "Dan",
        hard=[HardConstraint("fridays-only", lambda o: o["day"] == "fri")],
        utility=lambda o: 1.0,
    ))
    show(run_consensus(AGENTS + [dan], OPTIONS))
