from parley.spec import DecisionSpec


def test_retrospective_lease_exit_finds_the_ratified_compromise():
    spec = DecisionSpec.load("examples/demo/recipe_early_lease_exit.json")

    transcript = spec.run()

    assert transcript.decision["id"] == "balanced-replacement"
    for party in spec.parties:
        assert transcript.transcript.verify_non_betrayal(party.to_sheet(), transcript.decision)
    entries = {entry["option"]["id"]: entry for entry in transcript.transcript.entries}
    assert not all(v["acceptable"] for v in entries["penalty-and-relet"]["verdicts"])
    assert not all(v["acceptable"] for v in entries["walk-away"]["verdicts"])
