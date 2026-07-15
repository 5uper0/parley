"""Client side: a RemoteAgent that talks to a bot over HTTP.

Implements the same `.owner` / `.consider(option) -> Verdict` interface as a local
Agent, so `run_consensus` can't tell local from remote. Carries the bot's signature
and pubkey into the Verdict so the transcript stays verifiable.
"""
import json
import urllib.request

from parley.agent import Verdict


class RemoteAgent:
    def __init__(self, url, token=None, timeout=5):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        card = self._get("/card")  # discovery
        self.owner = card["owner"]
        self.pubkey_hex = card.get("pubkey_hex")

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
        return Verdict(
            owner=d["owner"], acceptable=d["acceptable"], score=d["score"],
            reason=d["reason"], sig=d.get("sig"), pubkey_hex=d.get("pubkey_hex"),
        )


def discover(urls, token=None):
    """Fetch each bot's Agent Card and return connected RemoteAgents."""
    return [RemoteAgent(u, token=token) for u in urls]
