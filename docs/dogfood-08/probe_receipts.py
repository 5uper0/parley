"""Tamper probe for parley_verify_receipt: what a dishonest record-keeper can and cannot get past the check."""
import copy
import json

from parley import mcp

spec = json.load(open("examples/demo/recipe_committee.json"))
out = mcp.tool_decide({"spec": spec})
T, H = out["transcript"], out["transcript_sha256"]
winner = out["decision"]["id"]
print("honest decision:", winner)


def check(name, t, sha, owners=None):
    args = {"transcript": t, "sha256": sha}
    if owners:
        args["expected_owners"] = owners
    try:
        r = mcp.tool_verify_receipt(args)
        print(f"{name:52} match={r['match']} max_min={r['max_min_verified']}")
    except Exception as e:
        print(f"{name:52} EXC {type(e).__name__}: {str(e)[:70]}")


def rehash(t):
    return mcp.tool_verify_receipt({"transcript": t, "sha256": "0" * 64})["recomputed_sha256"]


def entry(t, oid):
    return next(e for e in t["entries"] if e["option"]["id"] == oid)


check("untouched", T, H)

t = copy.deepcopy(T); entry(t, winner)["verdicts"][0]["score"] = 0.01
check("a score edited, old hash", t, H)
check("a score edited, hash recomputed by the editor", t, rehash(t))

t = copy.deepcopy(T); entry(t, winner)["verdicts"][1]["acceptable"] = False
check("winner vetoed on the record, hash recomputed", t, rehash(t))

alt = next(e["option"]["id"] for e in T["entries"] if e["option"]["id"] not in (winner, "rubber-stamp"))
t = copy.deepcopy(T); t["result"]["decision"] = entry(t, alt)["option"]
check("winner swapped to a feasible non-max-min option, old hash", t, H)
check("winner swapped, hash recomputed", t, rehash(t))

t = copy.deepcopy(T)
for e in t["entries"]:
    e["verdicts"] = [v for v in e["verdicts"] if v["owner"] != "Impact"]
check("party Impact removed from every verdict, hash recomputed", t, rehash(t))
check("same, caller pins expected_owners", t, rehash(t), owners=["Impact", "Budget", "Novelty"])

t = copy.deepcopy(T)
rs = entry(t, "rubber-stamp")
rs["verdicts"] = [dict(v, acceptable=True, reason="ok", score=1.0) for v in rs["verdicts"]]
t["result"]["decision"] = rs["option"]
check("red-lined option forged acceptable and crowned, rehashed", t, rehash(t))
