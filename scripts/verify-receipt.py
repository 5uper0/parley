#!/usr/bin/env python3
"""Check a receipt written by `examples/real_decision.py` without having been in the room.

A receipt only means something if a third party can re-derive its claims from what it contains.
This script does exactly that, from public data alone — no preference sheet is needed or read:

- rebuilds the transcript (`Transcript.from_dict`) and re-hashes it against the hash the
  receipt claims, so any edit to the record after the receipt was written shows up;
- recomputes the max-min outcome from the recorded verdicts (`consensus.verify_outcome`);
- checks every acceptance through `ratify.agreement`'s rules: bound to exactly this hash and
  this decision, by an owner who appears in the record; and, where an acceptance carries a
  signature, validates it (`net.identity.verify_acceptance`, needs the `crypto` extra).

It also prints what it does NOT prove. Per SECURITY.md the public key in a signed acceptance
or verdict is self-attested by the record that carries it, so a holder of any key can sign
under another owner's name; unsigned acceptances authenticate nobody; and verdict payloads
carry no replay binding. None of that is hidden behind a green tick.

Exit 0 only when every check passes; 1 when any check fails or a present signature could not
be checked; 2 when the file cannot be read as a receipt.

Usage:  scripts/verify-receipt.py receipt.json
"""
import argparse
import importlib
import json
import os
import sys
from dataclasses import fields
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from parley.consensus import verify_outcome  # noqa: E402
from parley.ratify import Acceptance, agreement  # noqa: E402
from parley.transcript import Transcript  # noqa: E402

REQUIRED = frozenset({"title", "status", "decision", "transcript_hash", "max_min_verified",
                      "unanimous_acceptance", "acceptances", "participants", "transcript"})
ACCEPTANCE_KEYS = frozenset(f.name for f in fields(Acceptance))
INSTALL_HINT = "install the crypto extra to check it: pip install 'parley[crypto]'"


def _crypto():
    """The optional Ed25519 layer, or None when pynacl is not installed."""
    try:
        return importlib.import_module("parley.net.identity")
    except ImportError:
        return None


def _acceptance(raw: Any, index: int) -> Acceptance:
    if not isinstance(raw, dict):
        raise ValueError(f"acceptance {index} is not an object")
    missing = sorted({"owner", "decision", "transcript_hash", "accepted"} - set(raw))
    unknown = sorted(set(raw) - ACCEPTANCE_KEYS)
    if missing or unknown:
        raise ValueError(f"acceptance {index}: missing {missing}, unknown {unknown}")
    return Acceptance(**{k: raw.get(k) for k in ACCEPTANCE_KEYS})


def verify(receipt: Any) -> dict:
    """Re-derive every checkable claim in a receipt. Returns a report; `report["ok"]` is the
    single answer, `report["errors"]` says why when it is False."""
    errors: list = []
    report: dict = {"ok": False, "errors": errors, "title": None, "status": None,
                    "decision": None, "hash": None, "result": None, "max_min": None,
                    "roster": None, "verdict_signatures": None, "acceptances": [],
                    "unanimous": None, "crypto": _crypto() is not None}
    if not isinstance(receipt, dict):
        errors.append("receipt is not a JSON object")
        return report
    missing = sorted(REQUIRED - set(receipt))
    if missing:
        errors.append(f"receipt is missing required field(s): {', '.join(missing)}")
        return report
    report["title"], report["status"] = receipt["title"], receipt["status"]
    report["decision"] = receipt["decision"]

    try:
        transcript = Transcript.from_dict(receipt["transcript"])
    except ValueError as exc:
        errors.append(f"transcript cannot be rebuilt: {exc}")
        return report

    recomputed, claimed = transcript.hash(), receipt["transcript_hash"]
    hash_ok = recomputed == claimed
    report["hash"] = {"claimed": claimed, "recomputed": recomputed, "ok": hash_ok}
    if not hash_ok:
        errors.append("transcript hash mismatch: the record was edited after the receipt was written")

    result = transcript.result
    status = result.get("status") if result else None
    decision = result.get("decision") if result else None
    result_ok = (result is not None and status in ("agreed", "deadlock")
                 and (status == "deadlock") == (decision is None)
                 and receipt["status"] == status and receipt["decision"] == decision)
    report["result"] = {"ok": result_ok, "status": status, "decision": decision}
    if not result_ok:
        errors.append("receipt status/decision do not match the finalized record")

    max_min = verify_outcome(transcript)
    max_min_ok = max_min and receipt["max_min_verified"] is True
    report["max_min"] = {"recomputed": max_min, "claimed": receipt["max_min_verified"],
                         "ok": max_min_ok}
    if not max_min:
        errors.append("the announced decision is not the max-min option over the recorded verdicts")
    elif receipt["max_min_verified"] is not True:
        errors.append("receipt claims max_min_verified is not true, but the recomputation says it is")

    owners = {v["owner"] for e in transcript.entries for v in e["verdicts"]}
    participants = receipt["participants"]
    roster_ok = (isinstance(participants, list) and bool(participants)
                 and all(isinstance(p, str) for p in participants)
                 and len(set(participants)) == len(participants)
                 and set(participants) == owners)
    report["roster"] = {"participants": participants, "transcript_owners": sorted(owners),
                        "ok": roster_ok}
    if not roster_ok:
        errors.append("participants listed in the receipt do not match the owners in the record")

    crypto = _crypto()
    signed_verdicts = [v for e in transcript.entries for v in e["verdicts"]
                       if v.get("sig") or v.get("pubkey_hex")]
    all_verdicts_signed = bool(signed_verdicts) and len(signed_verdicts) == sum(
        len(e["verdicts"]) for e in transcript.entries)
    if not signed_verdicts:
        verdict_sigs = "none"
    elif crypto is None:
        verdict_sigs = "unchecked"
        errors.append(f"verdicts carry signatures that were not checked: {INSTALL_HINT}")
    elif crypto.verify_transcript(transcript, require_signed=all_verdicts_signed):
        verdict_sigs = "verified"
    else:
        verdict_sigs = "FAILED"
        errors.append("a signed verdict does not validate against the key it carries")
    report["verdict_signatures"] = verdict_sigs

    accs: list = []
    seen: set = set()
    acc_ok = True
    for i, raw in enumerate(receipt["acceptances"] if isinstance(receipt["acceptances"], list)
                            else []):
        try:
            acc = _acceptance(raw, i)
        except ValueError as exc:
            errors.append(str(exc))
            acc_ok = False
            continue
        accs.append(acc)
        bound = (acc.owner in owners and acc.transcript_hash == recomputed
                 and acc.decision == decision)
        if acc.sig or acc.pubkey_hex:
            if crypto is None:
                signature = "unchecked"
            else:
                signature = "verified" if crypto.verify_acceptance(acc) else "FAILED"
        else:
            signature = "unsigned"
        duplicate = acc.owner in seen
        seen.add(acc.owner)
        ok = bound and signature in ("verified", "unsigned") and not duplicate
        report["acceptances"].append({"owner": acc.owner, "accepted": acc.accepted,
                                      "bound": bound, "signature": signature, "ok": ok})
        if not bound:
            errors.append(f"{acc.owner}: acceptance is not bound to this record and decision")
        if signature == "FAILED":
            errors.append(f"{acc.owner}: signature does not match the acceptance it is attached to")
        if signature == "unchecked":
            errors.append(f"{acc.owner}: acceptance is signed but unchecked; {INSTALL_HINT}")
        if duplicate:
            errors.append(f"{acc.owner}: more than one acceptance under this name")
        acc_ok = acc_ok and ok
    if not isinstance(receipt["acceptances"], list):
        errors.append("acceptances must be a list")
        acc_ok = False

    all_signed = bool(accs) and all(a.sig and a.pubkey_hex for a in accs)
    verifier = crypto.verify_acceptance if (crypto is not None and all_signed) else None
    unanimous = agreement(transcript, accs, verifier=verifier,
                          participants=set(participants) if roster_ok else None)
    unanimous_ok = unanimous == receipt["unanimous_acceptance"]
    report["unanimous"] = {"recomputed": unanimous, "claimed": receipt["unanimous_acceptance"],
                           "with_signatures": verifier is not None, "ok": unanimous_ok}
    if not unanimous_ok:
        errors.append("receipt's unanimous_acceptance claim does not match the recomputation")

    report["ok"] = (hash_ok and result_ok and max_min_ok and roster_ok and acc_ok
                    and unanimous_ok and verdict_sigs in ("none", "verified"))
    return report


def _mark(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def render(report: dict) -> str:
    """Plain text: what was checked, the answer, and what the answer does not cover."""
    lines = [f"Parley receipt check: {report['title']}"]
    if report["hash"] is None:
        lines += ["", "Result: FAILED", *(f"  - {e}" for e in report["errors"])]
        return "\n".join(lines) + "\n"
    decision = json.dumps(report["decision"], sort_keys=True, ensure_ascii=False)
    lines += [f"  status {report['status']}   decision {decision}", "", "Record"]
    h = report["hash"]
    lines += [f"  transcript hash   claimed    {h['claimed']}",
              f"                    recomputed {h['recomputed']}   {_mark(h['ok'])}",
              f"  status/decision   match the finalized record   {_mark(report['result']['ok'])}",
              f"  max-min honest    {'yes' if report['max_min']['recomputed'] else 'NO'}"
              f" (recomputed from the recorded verdicts)   {_mark(report['max_min']['ok'])}",
              f"  roster            {', '.join(map(str, report['roster']['participants']))}"
              f" (record: {', '.join(report['roster']['transcript_owners'])})"
              f"   {_mark(report['roster']['ok'])}",
              f"  verdict sigs      {report['verdict_signatures']}", "", "Acceptances"]
    for a in report["acceptances"]:
        lines.append(f"  {a['owner']:<16} {'accepted' if a['accepted'] else 'declined':<9}"
                     f" {'bound to this record' if a['bound'] else 'NOT bound to this record':<25}"
                     f" signature {a['signature']:<10} {_mark(a['ok'])}")
    if not report["acceptances"]:
        lines.append("  (none recorded)")
    u = report["unanimous"]
    if u["with_signatures"]:
        tier = "checked with signatures"
    elif any(a["signature"] != "unsigned" for a in report["acceptances"]):
        tier = "tamper-evidence only: signatures present but not all checked"
    else:
        tier = "tamper-evidence only: unsigned"
    lines.append(f"  unanimous         {'yes' if u['recomputed'] else 'no'}"
                 f" (receipt says {'yes' if u['claimed'] else 'no'}; {tier})   {_mark(u['ok'])}")
    lines.append("")
    if report["ok"]:
        lines.append("Result: VERIFIED. Every claim in this receipt re-derives from its own record.")
    else:
        lines += ["Result: FAILED", *(f"  - {e}" for e in report["errors"])]
    lines += [
        "",
        "What this checked",
        "  - the transcript in the receipt hashes to the hash the receipt claims, so the record",
        "    was not edited after the receipt was written",
        "  - the announced decision is the max-min option over the recorded verdicts (or the",
        "    deadlock is honest: no option cleared everyone's red lines)",
        "  - every acceptance is bound to exactly this hash and this decision, by an owner who",
        "    appears in the record, and the unanimity claim matches those acceptances",
        "  - a signed acceptance or verdict validates against the public key it carries",
        "",
        "What this does NOT prove",
        "  - who signed: each public key is self-attested by the record that carries it, so",
        "    anyone holding a key (the coordinator included) can sign an acceptance or a",
        "    verdict under another owner's name. There is no owner -> key roster yet (SECURITY.md).",
        "  - unsigned acceptances authenticate nobody: that tier is tamper-evidence only",
        "  - that this is the record the participants saw: the transcript is coordinator-",
        "    authored. Each participant must compare the hash they were shown at ratification",
        "    with the recomputed one above.",
        "  - that nobody's red line was crossed: no private sheet is in the receipt or read here.",
        "    Each owner replays their own sheet locally (Transcript.verify_non_betrayal).",
        "  - freshness: verdict payloads carry no session id or nonce, so a genuine signed",
        "    verdict can be replayed into another parley over the same option",
    ]
    if not report["crypto"]:
        lines += ["", f"Note: pynacl is not installed; signatures cannot be checked here ({INSTALL_HINT})."]
    return "\n".join(lines) + "\n"


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Check a receipt from examples/real_decision.py.")
    parser.add_argument("receipt", help="path to the receipt JSON")
    args = parser.parse_args(argv)
    try:
        with open(args.receipt, encoding="utf-8") as fh:
            receipt = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"cannot read receipt: {exc}", file=sys.stderr)
        return 2
    report = verify(receipt)
    sys.stdout.write(render(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
