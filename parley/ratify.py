"""Ratification — an owner's explicit accept of a finished parley, given on the owner's side.

`verify_non_betrayal` proves a red line held; it records nothing about whether the owner *agreed*.
The Exp 1 gate says "each ratified": every real participant replays the final decision against
their OWN private sheet, locally, and leaves an explicit accept bound to the exact record they saw.
This module is that step, kept out of the coordinator by construction:

- The sheet is an input and never part of the output. An `Acceptance` carries owner, decision,
  transcript hash and a boolean — nothing about which limits exist or why they held.
- You cannot accept what the sheet you submitted rejects: `ratify(accept=True)` replays the
  submitted sheet first and refuses when it rejects the decision. The guarantee is exactly that
  wide — the caller chooses the sheet, so a stale or emptied sheet gets a stale or empty check.
- Every acceptance binds the transcript hash and the decision, so a later edit to the record or
  a swapped decision orphans every acceptance already given.
- `agreement()` is unanimous: one accepted acceptance per owner who took part, all bound to the
  same hash. Silence is never acceptance — a missing owner fails.

Optional signing rides the same way `Verdict` does: plain `Optional[str]` fields filled by an
injected signer, checked by an injected verifier. The core imports no crypto; `net.identity`
supplies both. Every `Acceptance` field is public, so the unsigned tier authenticates nothing —
it is tamper-evidence only (a hash/decision mismatch is caught, a fabricated record is not).
"""
import json
from dataclasses import dataclass, replace
from typing import Any, Callable, Optional, Sequence, Set, Tuple

from .preferences import PreferenceSheet
from .transcript import Transcript

Signer = Callable[[bytes], Tuple[str, str]]  # canonical payload -> (sig_hex, pubkey_hex)
Verifier = Callable[["Acceptance"], bool]


class RatifyError(ValueError):
    pass


@dataclass(frozen=True)
class Acceptance:
    owner: str
    decision: Any
    transcript_hash: str
    accepted: bool
    sig: Optional[str] = None
    pubkey_hex: Optional[str] = None

    def to_dict(self) -> dict:
        return {"owner": self.owner, "decision": self.decision,
                "transcript_hash": self.transcript_hash, "accepted": self.accepted,
                "sig": self.sig, "pubkey_hex": self.pubkey_hex}


def acceptance_payload(owner: str, decision: Any, transcript_hash: str, accepted: bool) -> bytes:
    """Canonical bytes an owner signs — binds who, what, which record, and the answer.

    `type` separates this domain from verdict signatures, so a key that signs both can never
    have one signature re-read as the other."""
    return json.dumps(
        {"type": "acceptance/0.1", "owner": owner, "decision": decision,
         "transcript_hash": transcript_hash, "accepted": accepted},
        sort_keys=True, ensure_ascii=False, default=str,
    ).encode("utf-8")


def ratify(sheet: PreferenceSheet, transcript: Transcript, accept: bool,
           signer: Optional[Signer] = None) -> Acceptance:
    """Replay the submitted sheet against the finalized record, then record an explicit answer.

    `accept=True` is refused when the submitted sheet rejects the decision; rejecting never
    needs a reason. A deadlock can be acknowledged (it forces nothing on anyone) but is never
    an agreement. An "agreed" record with no decision is refused outright: the replay would
    short-circuit on the null decision, so nothing would actually be checked.
    """
    if transcript.result is None:
        raise RatifyError("nothing to ratify: the parley has not been finalized")
    status, decision = transcript.result.get("status"), transcript.result.get("decision")
    if status == "agreed" and decision is None:
        raise RatifyError("refusing to ratify: an agreed record carries no decision to replay")
    if accept and not transcript.verify_non_betrayal(sheet, decision):
        raise RatifyError("refusing to accept: the decision crosses one of this owner's red lines")
    acceptance = Acceptance(owner=sheet.owner, decision=decision,
                            transcript_hash=transcript.hash(), accepted=accept)
    if signer is not None:
        sig, pubkey_hex = signer(acceptance_payload(
            acceptance.owner, acceptance.decision, acceptance.transcript_hash,
            acceptance.accepted))
        acceptance = replace(acceptance, sig=sig, pubkey_hex=pubkey_hex)
    return acceptance


def agreement(transcript: Transcript, acceptances: Sequence[Acceptance],
              verifier: Optional[Verifier] = None,
              participants: Optional[Set[str]] = None) -> bool:
    """Unanimous over one exact record: every owner in the transcript accepted this hash and
    this decision, and nobody who is not in the transcript was counted. Fails closed on any
    mismatch — a stale hash, a swapped decision, a rejection, a stranger, a missing owner, or
    an "agreed" record with no decision.

    The participant set is derived from the transcript, which the coordinator authors: a
    coordinator that drops an owner from the record shrinks the set. Pass `participants` (the
    set the owners themselves know took part) and it must equal the derived set exactly.

    Without `verifier`, nothing here authenticates an acceptance — every field is public, so
    anyone holding the transcript can fabricate the whole set. With `verifier`
    (`net.identity.verify_acceptance`), every acceptance must verify or the answer is False.
    That catches the keyless forger and the post-hoc tamperer, not the impersonator:
    `verify_acceptance` checks a key the acceptance attests to itself, so a forger holding any
    single keypair can still sign the whole set under the owners' names. Only the v0.2
    owner -> key roster pin closes that (see SECURITY.md).

    This proves everyone accepted this record; it does not prove the record's decision is the
    max-min one — the coordinator authors the transcript and can finalize any feasible option.
    Call `consensus.verify_outcome(transcript)` for that.
    """
    result = transcript.result
    if not result or result.get("status") != "agreed":
        return False
    expected_hash, decision = transcript.hash(), result.get("decision")
    if decision is None:
        return False
    owners = {v["owner"] for e in transcript.entries for v in e["verdicts"]}
    if not owners:
        return False
    if participants is not None and set(participants) != owners:
        return False
    seen = set()
    for a in acceptances:
        if (a.owner not in owners or not a.accepted
                or a.transcript_hash != expected_hash or a.decision != decision):
            return False
        if verifier is not None and not verifier(a):
            return False
        seen.add(a.owner)
    return seen == owners
