"""Named bot profiles (private preference sheets) + the shared meeting agenda.

Each profile lives inside its own bot process; the sheet is never sent on the wire.
The agenda (OPTIONS) is public — it's the thing everyone is trying to agree on.
"""
from parley.preferences import PreferenceSheet, HardConstraint

OPTIONS = [
    {"day": "mon", "hour": 9},
    {"day": "mon", "hour": 15},
    {"day": "tue", "hour": 11},
    {"day": "tue", "hour": 14},
    {"day": "wed", "hour": 14},
    {"day": "thu", "hour": 15},
    {"day": "fri", "hour": 15},
    {"day": "tue", "hour": 17},
]

PROFILES = {
    "ana": lambda: PreferenceSheet(
        "Ana",
        hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 11)],
        utility=lambda o: 1.0 if o["day"] == "tue" else 0.5,
    ),
    "bob": lambda: PreferenceSheet(
        "Bob",
        hard=[HardConstraint("no-fridays", lambda o: o["day"] != "fri")],
        utility=lambda o: 1.0 if o["hour"] == 15 else 0.5,
    ),
    "cara": lambda: PreferenceSheet(
        "Cara",
        hard=[HardConstraint("kids-pickup", lambda o: o["hour"] <= 16)],
        utility=lambda o: 1.0 if o["day"] == "wed" else 0.5,
    ),
    "dan": lambda: PreferenceSheet(
        "Dan",
        hard=[HardConstraint("no-mondays", lambda o: o["day"] != "mon")],
        utility=lambda o: 1.0 if o["hour"] == 14 else 0.5,
    ),
    "eve": lambda: PreferenceSheet(
        "Eve",
        hard=[HardConstraint("afternoons-only", lambda o: o["hour"] >= 13)],
        utility=lambda o: 1.0 if o["day"] == "thu" else 0.5,
    ),
}
