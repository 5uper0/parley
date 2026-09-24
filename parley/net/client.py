"""Client side: a RemoteAgent that talks to a bot over HTTP.

Implements the same `.owner` / `.consider(option) -> Verdict` interface as a local
Agent, so `run_consensus` can't tell local from remote. Carries the bot's signature
and pubkey into the Verdict so the transcript stays verifiable.

The bot's reply is untrusted input: a verdict whose fields are not exactly the masked shape
is refused, so a string "false" can't read as acceptable and a NaN score can't poison max-min.
When the card advertised a key, a reply must carry that same key and a signature: otherwise a
man in the middle could sign with its own key, and `verify_transcript` would accept it later
because it checks each signature against the key embedded beside it. The signature itself is
checked by `verify_transcript`; the core client imports no crypto.
"""
import json
import math
import string
import urllib.request

from parley.agent import Verdict


class RemoteAgent:
    def __init__(self, url, token=None, timeout=5):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        card = self._get("/card")  # discovery
        if not isinstance(card, dict) or not isinstance(card.get("owner"), str) or not card["owner"]:
            raise ValueError(f"malformed card from {self.url}")
        self.owner = card["owner"]
        self.pubkey_hex = card.get("pubkey_hex")
        if self.pubkey_hex is not None and not _is_hex(self.pubkey_hex):
            raise ValueError(f"malformed card key from {self.url}")

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path):
        req = urllib.request.Request(self.url + path, headers=self._headers())
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def consider(self, option) -> Verdict:
        body = json.dumps({"option": option}).encode("utf-8")
        req = urllib.request.Request(self.url + "/consider", data=body, headers=self._headers())
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            d = json.loads(r.read())
        if not _well_formed(d, self.owner):
            raise ValueError(f"malformed verdict from {self.url}")
        if self.pubkey_hex is not None and (d.get("pubkey_hex") != self.pubkey_hex
                                            or not d.get("sig")):
            raise ValueError(f"verdict from {self.url} is not signed by the key its card advertised")
        return Verdict(
            owner=d["owner"], acceptable=d["acceptable"], score=d["score"],
            reason=d["reason"], sig=d.get("sig"), pubkey_hex=d.get("pubkey_hex"),
        )


def _is_hex(value) -> bool:
    """An Ed25519 public key is 32 bytes, so exactly 64 hex digits."""
    return isinstance(value, str) and len(value) == 64 and all(c in string.hexdigits for c in value)


def _well_formed(d, owner) -> bool:
    if not isinstance(d, dict):
        return False
    acceptable, score = d.get("acceptable"), d.get("score")
    return (
        d.get("owner") == owner
        and isinstance(acceptable, bool)
        and isinstance(score, (int, float)) and not isinstance(score, bool)
        and math.isfinite(score) and 0.0 <= score <= 1.0
        and d.get("reason") == ("ok" if acceptable else "red-line")
        and all(d.get(k) is None or isinstance(d[k], str) for k in ("sig", "pubkey_hex"))
    )


def discover(urls, token=None):
    """Fetch each bot's Agent Card and return connected RemoteAgents."""
    return [RemoteAgent(u, token=token) for u in urls]
