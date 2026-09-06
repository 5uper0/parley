# Ready-to-run decisions

Four option sets for `examples/real_decision.py`, so running a real parley needs no JSON authoring
first. Pick the one closest to a choice the people in the room are actually arguing about, or copy
one and edit the numbers.

```bash
.venv/bin/python examples/real_decision.py \
    --options examples/cases/flatshare.json \
    --participants Ana,Bob,Cara \
    --manual \
    --receipt receipt.json
```

`--manual` needs no model and no network: each person types their own red lines and preferences.
Drop it and set `PARLEY_API_KEY` to state a position in plain words instead.

| File | The argument it encodes |
|---|---|
| `flatshare.json` | Which flat to take. Rent, commute, bedrooms, outdoor space, pets. |
| `split-the-bill.json` | How to split a shared cost when people used it unevenly. |
| `who-does-what.json` | Who takes which part of the work, and who is on call. |
| `pick-a-date.json` | Which weekend to go, trading cost against days off and who misses out. |

Every one of the four was run end to end before being committed. Each produced an agreed decision
that no participant's red line rejected, with at least one option blocked outright along the way.

## Why these shapes

Options are flat objects of attributes. A red line is a predicate over one attribute, so an
attribute is only useful if someone might refuse over it: a number with a real threshold
(`rent_per_person <= 700`), a boolean someone insists on (`pets_allowed == true`), or a category
someone rules out (`weather_risk != high`). Attributes nobody would refuse over belong in the
preferences, not the red lines.

The sets are deliberately small. Five options is enough for the max-min pick to be non-obvious and
few enough that three people can hold all of them in their heads while stating a position.

## What "good" looks like when you run it

At least one option should be blocked by somebody's red line, and the winner should not be anyone's
first choice. If everyone's favourite wins, the group did not actually disagree and the run proves
nothing. Change the constraints until someone has to give something up.
