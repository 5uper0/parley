"""Ed25519 identity for bots: signed Agent Cards + signed verdicts.

Optional layer (needs the `crypto` extra / pynacl). A signed verdict binds the bot's
key to the exact (option, verdict) pair, so the coordinator that assembles the transcript
can neither fabricate a verdict nor replay a real one against a different option — the
transcript becomes an authentic, audit-grade record, not just a tamper-evident one.
"""
import json
from dataclasses import dataclass

from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def verdict_payload(option, owner, acceptable, score, reason) -> bytes:
    """Canonical bytes a bot signs for one verdict — binds owner+option+content."""
    return json.dumps(
        {"owner": owner, "option": option, "acceptable": acceptable,
         "score": score, "reason": reason},
        sort_keys=True, ensure_ascii=False, default=str,
    ).encode("utf-8")


@dataclass(frozen=True)
class AgentCard:
    owner: str
    pubkey_hex: str
    protocol: str = "parley/0.1"

    def verify(self, message: bytes, sig_hex: str) -> bool:
        try:
            VerifyKey(self.pubkey_hex, encoder=HexEncoder).verify(message, bytes.fromhex(sig_hex))
            return True
        except (BadSignatureError, ValueError):
            return False

    def to_dict(self) -> dict:
        return {"owner": self.owner, "pubkey_hex": self.pubkey_hex, "protocol": self.protocol}

    @classmethod
    def from_dict(cls, d: dict) -> "AgentCard":
        return cls(owner=d["owner"], pubkey_hex=d["pubkey_hex"],
                   protocol=d.get("protocol", "parley/0.1"))


class Identity:
    def __init__(self, owner: str, signing_key: SigningKey):
        self.owner = owner
        self._sk = signing_key

    @classmethod
    def generate(cls, owner: str) -> "Identity":
        return cls(owner, SigningKey.generate())

    def card(self) -> AgentCard:
        pub = self._sk.verify_key.encode(encoder=HexEncoder).decode()
        return AgentCard(owner=self.owner, pubkey_hex=pub)

    def sign(self, message: bytes) -> str:
        return self._sk.sign(message).signature.hex()

    def sign_verdict(self, option, verdict) -> str:
        return self.sign(verdict_payload(
            option, verdict.owner, verdict.acceptable, verdict.score, verdict.reason))


def verify_transcript(transcript, require_signed: bool = False) -> bool:
    """Every SIGNED verdict must validate against its own pubkey for its own option.

    Returns False if any signed verdict fails — i.e. the coordinator fabricated or
    altered it. This is what stops a dishonest coordinator from lying about who agreed
    to what.

    Unsigned (local) verdicts are skipped by default, so a mixed local/remote transcript
    still verifies. That default is fail-OPEN against a *downgrade* attack: a coordinator
    that strips signatures makes the check pass silently. When every participant is
    expected to sign (the audit-grade case), pass ``require_signed=True`` — then a verdict
    missing its ``sig``/``pubkey_hex`` fails closed.
    """
    for entry in transcript.entries:
        for v in entry["verdicts"]:
            if not v.get("sig") or not v.get("pubkey_hex"):
                if require_signed:
                    return False  # fail closed: an expected signature is missing (downgrade)
                continue
            card = AgentCard(owner=v["owner"], pubkey_hex=v["pubkey_hex"])
            payload = verdict_payload(
                entry["option"], v["owner"], v["acceptable"], v["score"], v["reason"])
            if not card.verify(payload, v["sig"]):
                return False
    return True
