"""Five-minute outside run: decide, verify the receipt, show that an edit is caught.

Run it after `pip install parley-consensus`:

    python five_minute_run.py

It runs the three-party dinner from the README, writes the record to `receipt.json`, re-checks
that record with the same function the `parley_verify_receipt` MCP tool uses, then edits one
verdict and checks again. The last block is plain text to paste into
https://github.com/5uper0/parley/discussions/92. Nothing is sent anywhere.

Exit 0 when the receipt verifies and the edited copy is rejected, 1 otherwise.
"""
import json
import platform
import sys
from importlib import metadata

from parley.agent import Agent
from parley.consensus import run_consensus
from parley.mcp import tool_verify_receipt
from parley.preferences import HardConstraint, PreferenceSheet

OPTIONS = [
    {"venue": "rooftop", "cost": 900},
    {"venue": "garden", "cost": 600},
    {"venue": "diner", "cost": 300},
]


def main() -> int:
    ana = PreferenceSheet("Ana", utility=lambda o: 1.0 if o["venue"] == "rooftop" else 0.4)
    bob = PreferenceSheet(
        "Bob",
        hard=[HardConstraint("budget", lambda o: o["cost"] <= 700)],
        utility=lambda o: 1 - o["cost"] / 1000)
    cara = PreferenceSheet("Cara", utility=lambda o: 0.9 if o["venue"] == "garden" else 0.5)
    sheets = (ana, bob, cara)

    result = run_consensus([Agent(s.owner, s) for s in sheets], OPTIONS)
    record = result.transcript.to_dict()
    claimed = result.transcript.hash()
    with open("receipt.json", "w") as fh:
        json.dump({"transcript": record, "sha256": claimed}, fh, indent=2)

    print("1. decide:", result.status, result.decision)
    print("   receipt sha256:", claimed)
    print("   written to receipt.json (public masked verdicts only, no limit values)")

    own = [result.transcript.verify_non_betrayal(s, result.decision) for s in sheets]
    for s, ok in zip(sheets, own):
        print(f"2. {s.owner} replays their own sheet locally, not betrayed: {ok}")

    check = tool_verify_receipt({"transcript": record, "sha256": claimed,
                                 "expected_owners": [s.owner for s in sheets]})
    print("3. verify receipt: hash match =", check["match"],
          "| max-min recomputed from verdicts =", check["max_min_verified"],
          "| owners =", check["owners_found"])

    # Flip the first recorded red-line verdict to acceptable. Any edit must break the hash.
    forged = json.loads(json.dumps(record))
    flipped = False
    for entry in forged["entries"]:
        for verdict in entry["verdicts"]:
            if not flipped and verdict.get("acceptable") is False:
                verdict["acceptable"] = True
                flipped = True
    bad = tool_verify_receipt({"transcript": forged, "sha256": claimed,
                               "expected_owners": [s.owner for s in sheets]})
    print("4. same receipt with one verdict edited: hash match =", bad["match"],
          "(expected False)")

    passed = (result.status == "agreed" and all(own) and check["match"]
              and check["max_min_verified"] and flipped and not bad["match"])
    print()
    print("Paste this into https://github.com/5uper0/parley/discussions/92 :")
    print("---")
    try:
        version = metadata.version("parley-consensus")
    except metadata.PackageNotFoundError:
        version = "(run from a source checkout)"
    print("parley-consensus", version,
          "| Python", platform.python_version(), "|", platform.system(), platform.machine())
    print("script: five_minute_run.py |", "PASS" if passed else "FAIL")
    print("receipt sha256:", claimed)
    print("verify: match =", check["match"], ", max_min_verified =", check["max_min_verified"],
          ", edited copy rejected =", not bad["match"])
    print("what broke: (nothing, or paste the error)")
    print("---")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
