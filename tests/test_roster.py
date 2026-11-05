"""R1 (security review 2026-11-05): keys are pinned per owner out of band; a host that mints its
own keys cannot forge a transcript that verifies against the owners' roster."""
import pytest

pytest.importorskip("nacl")

from parley.agent import Verdict  # noqa: E402
from parley.net.identity import Identity, verify_acceptance, verify_transcript  # noqa: E402
from parley.ratify import ratify  # noqa: E402
from parley.preferences import PreferenceSheet  # noqa: E402
from parley.transcript import Transcript  # noqa: E402


def _signed(ident, owner, option, acceptable=True, score=0.5):
    v = Verdict(owner, acceptable, score, "ok" if acceptable else "red-line")
    return Verdict(owner, acceptable, score, v.reason, sig=ident.sign_verdict(option, v),
                   pubkey_hex=ident.card().pubkey_hex)


def _transcript(*pairs, option=None):
    option = option or {"id": "a"}
    t = Transcript()
    t.record(option, [_signed(i, o, option) for i, o in pairs])
    t.finalize("agreed", option)
    return t


def test_roster_accepts_the_real_keys():
    ana, bob = Identity.generate("Ana"), Identity.generate("Bob")
    t = _transcript((ana, "Ana"), (bob, "Bob"))
    roster = {"Ana": ana.card().pubkey_hex, "Bob": bob.card().pubkey_hex}
    assert verify_transcript(t, require_signed=True, roster=roster)


def test_host_minted_keys_fail_against_the_roster():
    ana, bob = Identity.generate("Ana"), Identity.generate("Bob")
    roster = {"Ana": ana.card().pubkey_hex, "Bob": bob.card().pubkey_hex}
    forged = _transcript((Identity.generate("Ana"), "Ana"), (Identity.generate("Bob"), "Bob"))
    assert verify_transcript(forged, require_signed=True)  # the old check is fooled
    assert not verify_transcript(forged, require_signed=True, roster=roster)


def test_owner_missing_from_the_roster_fails():
    ana = Identity.generate("Ana")
    t = _transcript((ana, "Ana"))
    assert not verify_transcript(t, require_signed=True, roster={"Bob": "00" * 32})


def test_one_key_for_two_owners_fails_even_without_a_roster():
    k = Identity.generate("X")
    t = _transcript((k, "Ana"), (k, "Bob"))
    assert not verify_transcript(t, require_signed=True)


def test_two_keys_for_one_owner_fails_even_without_a_roster():
    option = {"id": "a"}
    t = Transcript()
    t.record(option, [_signed(Identity.generate("Ana"), "Ana", option)])
    t.record({"id": "b"}, [_signed(Identity.generate("Ana"), "Ana", {"id": "b"})])
    t.finalize("agreed", option)
    assert not verify_transcript(t, require_signed=True)


def test_acceptance_checked_against_the_roster():
    ana = Identity.generate("Ana")
    t = _transcript((ana, "Ana"))
    sheet = PreferenceSheet("Ana")
    acc = ratify(sheet, t, accept=True, signer=ana.sign_acceptance)
    assert verify_acceptance(acc)
    assert verify_acceptance(acc, roster={"Ana": ana.card().pubkey_hex})
    assert not verify_acceptance(acc, roster={"Ana": Identity.generate("Ana").card().pubkey_hex})
    assert not verify_acceptance(acc, roster={})
