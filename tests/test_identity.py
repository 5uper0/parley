"""Cryptographic identity: signed Agent Cards + signed verdicts (Ed25519).

This is what makes the transcript trustworthy: a verdict is signed by the bot's key
over the SPECIFIC option, so a malicious coordinator can neither forge a verdict nor
move a real one to a different option. Requires the `crypto` extra (pynacl).
"""
import pytest

pytest.importorskip("nacl")

from parley.net.identity import Identity, AgentCard, verdict_payload


def test_card_exposes_owner_and_pubkey_only():
    card = Identity.generate("Ana").card()
    assert card.owner == "Ana"
    assert isinstance(card.pubkey_hex, str) and len(card.pubkey_hex) == 64


def test_sign_verify_roundtrip_and_tamper():
    idn = Identity.generate("Ana")
    card = idn.card()
    sig = idn.sign(b"hello")
    assert card.verify(b"hello", sig) is True
    assert card.verify(b"tampered", sig) is False


def test_a_key_cannot_forge_for_another():
    a, b = Identity.generate("Ana"), Identity.generate("Bob")
    sig = a.sign(b"x")
    assert b.card().verify(b"x", sig) is False


def test_signed_verdict_is_bound_to_its_option_and_content():
    idn = Identity.generate("Ana")
    card = idn.card()
    option = {"day": "mon", "hour": 15}
    sig = idn.sign(verdict_payload(option, "Ana", True, 1.0, "ok"))

    assert card.verify(verdict_payload(option, "Ana", True, 1.0, "ok"), sig) is True
    # a dishonest coordinator cannot move the verdict to a different option…
    assert card.verify(verdict_payload({"day": "mon", "hour": 9}, "Ana", True, 1.0, "ok"), sig) is False
    # …nor flip acceptable/score/reason
    assert card.verify(verdict_payload(option, "Ana", False, 1.0, "ok"), sig) is False
    assert card.verify(verdict_payload(option, "Ana", True, 0.0, "ok"), sig) is False
