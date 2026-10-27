"""parley_check_party probe: the owner's local replay against right and wrong decisions and sheets."""
import copy
import json

from parley import mcp

spec = json.load(open("examples/demo/recipe_committee.json"))
budget = next(p for p in spec["parties"] if p["owner"] == "Budget")
opt = {o["id"]: o for o in spec["options"]}


def run(name, party, decision):
    try:
        r = mcp.tool_check_party({"party": party, "decision": decision})
        print(f"{name:52} holds={r.get('holds')}")
    except Exception as e:
        print(f"{name:52} EXC {type(e).__name__}: {str(e)[:70]}")


run("honest winner", budget, opt["fund-biotech"])
run("red-lined option (reviewed=false)", budget, opt["rubber-stamp"])
run("deadlock (decision null)", budget, None)
d = copy.deepcopy(opt["rubber-stamp"]); d.pop("reviewed")
run("red-line attribute missing from the decision", budget, d)
d = copy.deepcopy(opt["fund-biotech"]); d["reviewed"] = "true"
run("red-line attribute is the string 'true'", budget, d)
d = copy.deepcopy(opt["rubber-stamp"]); d["reviewed"] = 1
run("red-line attribute is 1 (== True in Python)", budget, d)
other = copy.deepcopy(budget); other["owner"] = "Someone"
run("sheet of a party that was never in the run", other, opt["fund-biotech"])
empty = {"owner": "Nobody", "hard": [], "utility": []}
run("sheet with no red lines at all", empty, opt["rubber-stamp"])
