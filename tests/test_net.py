"""Consensus over a real HTTP transport: bots are separate servers, the coordinator
talks to them over the wire and never sees their sheets. Covers 2-bot and 5-bot.
"""
import threading

import pytest

from parley.consensus import run_consensus
from parley.net.bot import serve
from parley.net.client import RemoteAgent
from parley.net.profiles import PROFILES, OPTIONS


def _start(profile):
    sheet = PROFILES[profile]()
    httpd = serve(sheet.owner, sheet, port=0)  # ephemeral port
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}"


@pytest.fixture
def bots():
    servers = []

    def launch(profiles):
        urls = []
        for p in profiles:
            httpd, url = _start(p)
            servers.append(httpd)
            urls.append(url)
        return urls

    yield launch
    for s in servers:
        s.shutdown()


def test_two_bots_reach_consensus_over_http(bots):
    urls = bots(["ana", "bob"])
    agents = [RemoteAgent(u) for u in urls]           # discovery over the wire
    assert [a.owner for a in agents] == ["Ana", "Bob"]

    r = run_consensus(agents, OPTIONS)
    assert r.status == "agreed"
    # each owner verifies non-betrayal with THEIR OWN local sheet
    assert r.transcript.verify_non_betrayal(PROFILES["ana"](), r.decision)
    assert r.transcript.verify_non_betrayal(PROFILES["bob"](), r.decision)


def test_five_bots_reach_consensus_over_http(bots):
    profiles = ["ana", "bob", "cara", "dan", "eve"]
    urls = bots(profiles)
    agents = [RemoteAgent(u) for u in urls]
    assert len(agents) == 5

    r = run_consensus(agents, OPTIONS)
    assert r.status == "agreed"
    # feasible-for-all-5 = {tue14, wed14, thu15}; whatever wins holds every red line
    for p in profiles:
        assert r.transcript.verify_non_betrayal(PROFILES[p](), r.decision) is True


def test_wire_never_carries_the_private_sheet(bots):
    urls = bots(["ana", "bob", "cara", "dan", "eve"])
    agents = [RemoteAgent(u) for u in urls]
    r = run_consensus(agents, OPTIONS)
    dump = str(r.transcript.to_dict())
    for leak in ("no-mornings", "no-fridays", "kids-pickup", "no-mondays", "afternoons-only"):
        assert leak not in dump


def test_signed_transcript_detects_coordinator_forgery(bots):
    from parley.net.identity import verify_transcript

    urls = bots(["ana", "bob"])
    agents = [RemoteAgent(u) for u in urls]
    r = run_consensus(agents, OPTIONS)
    assert verify_transcript(r.transcript) is True  # every verdict validly signed

    # a dishonest coordinator flips a recorded verdict -> signature no longer matches
    r.transcript.entries[0]["verdicts"][0]["acceptable"] = (
        not r.transcript.entries[0]["verdicts"][0]["acceptable"]
    )
    assert verify_transcript(r.transcript) is False


def test_stripping_a_signature_fails_closed_when_signatures_are_required(bots):
    from parley.net.identity import verify_transcript

    urls = bots(["ana", "bob"])
    agents = [RemoteAgent(u) for u in urls]
    r = run_consensus(agents, OPTIONS)

    # a coordinator strips a verdict's signature to dodge the check (downgrade attack)
    r.transcript.entries[0]["verdicts"][0]["sig"] = None
    r.transcript.entries[0]["verdicts"][0]["pubkey_hex"] = None

    assert verify_transcript(r.transcript) is True             # default skips unsigned (fail-open)
    assert verify_transcript(r.transcript, require_signed=True) is False  # fails closed
