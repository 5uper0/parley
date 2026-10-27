"""Concurrency probe: parallel tool_decide calls must give the same result as sequential ones (no shared state)."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor

from parley import mcp

base = json.load(open("examples/demo/recipe_committee.json"))


def variant(i):
    s = copy.deepcopy(base)
    for o in s["options"]:
        o["impact"] = (o["impact"] + i) % 10
    return s


specs = [variant(i) for i in range(40)]
seq = [mcp.tool_decide({"spec": s}) for s in specs]
with ThreadPoolExecutor(16) as ex:
    par = list(ex.map(lambda s: mcp.tool_decide({"spec": s}), specs))
bad = [i for i, (a, b) in enumerate(zip(seq, par)) if a["transcript_sha256"] != b["transcript_sha256"] or a["decision"] != b["decision"]]
print("calls:", len(specs), "| mismatches between sequential and 16-thread runs:", bad)
print("distinct decisions:", sorted({(r['decision'] or {}).get('id') for r in seq}))
