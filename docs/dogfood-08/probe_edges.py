"""Probe: feed 19 malformed or extreme specs to parley.mcp.tool_decide and print what each does. Read-only; run from the repo root with PYTHONPATH=."""
import copy
import json
from parley import mcp
base = json.load(open("examples/demo/recipe_committee.json"))
def run(name, spec):
    try:
        out = mcp.tool_decide({"spec": spec})
        d = out.get("decision")
        print(f"{name:34} ok  decision={d and d.get('id')} keys={sorted(out)[:3]}")
    except Exception as e:
        print(f"{name:34} EXC {type(e).__name__}: {str(e)[:90]}")
s = copy.deepcopy(base); run("baseline", s)
s = copy.deepcopy(base); s["parties"] = s["parties"] + [s["parties"][0]]; run("duplicate owner", s)
s = copy.deepcopy(base); s["options"] = []; run("no options", s)
s = copy.deepcopy(base); s["parties"] = []; run("no parties", s)
s = copy.deepcopy(base); s["options"] = [{"id": "a"}, {"id": "a"}]; run("duplicate option id", s)
s = copy.deepcopy(base); [o.pop("impact") for o in s["options"]]; run("missing attr everywhere", s)
s = copy.deepcopy(base); s["parties"][0]["hard"] = [{"attr": "impact", "op": ">=", "value": 99}]; run("all options infeasible", s)
s = copy.deepcopy(base); s["parties"][0]["hard"] = [{"attr": "impact", "op": "~", "value": 1}]; run("unknown operator", s)
s = copy.deepcopy(base); s["parties"][0]["utility"] = [{"attr": "impact", "direction": "higher", "lo": 5, "hi": 5}]; run("lo == hi utility", s)
s = copy.deepcopy(base); s["options"][0]["impact"] = "high"; run("string where number", s)
s = copy.deepcopy(base); s["options"][0]["impact"] = float("nan"); run("NaN attribute", s)
s = copy.deepcopy(base); s["options"][0]["impact"] = True; run("bool as number", s)
s = copy.deepcopy(base)
s["parties"] = [{"owner": f"P{i}", "hard": [], "utility": [{"attr": "impact", "direction": "higher", "lo": 0, "hi": 9}]} for i in range(60)]; run("60 parties", s)
s = copy.deepcopy(base); s["options"] = [{"id": f"o{i}", "impact": i % 10, "cost": i, "novelty": 1, "reviewed": True} for i in range(500)]; run("500 options", s)
s = copy.deepcopy(base); s["options"] = [{"id": f"o{i}", "impact": 1, "cost": 1, "novelty": 1, "reviewed": True} for i in range(5)]; run("5 identical options (tie)", s)
s = copy.deepcopy(base); s["parties"][0]["owner"] = ""; run("empty owner name", s)
s = copy.deepcopy(base); s["title"] = None; run("title null", s)
s = copy.deepcopy(base); s["options"][0]["id"] = 7; run("int option id", s)
s = copy.deepcopy(base); s["parties"][0]["hard"] = [{"attr": "impact", "op": "in", "value": "abc"}]; run("'in' with string value", s)
