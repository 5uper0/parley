"""R2 (security review 2026-11-05): a signed verdict is bound to one run (session id) and one
asking (nonce), so a genuine verdict from run A cannot be replayed into run B."""
import threading

import pytest

pytest.importorskip("nacl")

from parley.agent import Agent, Verdict  # noqa: E402
from parley.consensus import run_consensus  # noqa: E402
from parley.net.bot import serve  # noqa: E402
from parley.net.client import RemoteAgent  # noqa: E402
from parley.net.identity import Identity, verdict_payload, verify_transcript  # noqa: E402
from parley.net.profiles import OPTIONS, PROFILES  # noqa: E402
from parley.transcript import Transcript  # noqa: E402


@pytest.fixture
def bots():
    servers = []

    def launch(profiles):
        agents = []
        for p in profiles:
            sheet = PROFILES[p]()
            httpd = serve(sheet.owner, sheet, port=0)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            servers.append(httpd)
            agents.append(RemoteAgent(f"http://127.0.0.1:{httpd.server_address[1]}"))
        return agents

    yield launch
    for s in servers:
        s.shutdown()


def _run(agents, session):
    for a in agents:
        a.bind(session)
    return run_consensus(agents, OPTIONS)


def test_payload_with_session_and_nonce_differs_from_legacy():
    legacy = verdict_payload({"x": 1}, "A", True, 0.5, "ok")
    bound = verdict_payload({"x": 1}, "A", True, 0.5, "ok", session="S1", nonce="N1")
    other = verdict_payload({"x": 1}, "A", True, 0.5, "ok", session="S2", nonce="N1")
    assert legacy != bound != other


def test_run_records_session_and_unique_nonces(bots):
    result = _run(bots(["ana", "bob"]), "room-1")
    verdicts = [v for e in result.transcript.entries for v in e["verdicts"]]
    assert {v["session"] for v in verdicts} == {"room-1"}
    nonces = [v["nonce"] for v in verdicts]
    assert len(set(nonces)) == len(nonces)
    assert verify_transcript(result.transcript, require_signed=True, expected_session="room-1")


def test_verdict_from_run_a_fails_in_run_b(bots):
    agents = bots(["ana", "bob"])
    run_a = _run(agents, "room-A")
    assert not verify_transcript(run_a.transcript, require_signed=True, expected_session="room-B")


def test_replayed_nonce_inside_one_run_fails(bots):
    result = _run(bots(["ana", "bob"]), "room-1")
    forged = Transcript.from_dict(result.transcript.to_dict())
    first = forged.entries[0]["verdicts"][0]
    forged.entries[1]["verdicts"][0] = dict(first)  # same signed verdict reused
    assert not verify_transcript(forged, require_signed=True, expected_session="room-1")


def test_stripping_the_session_fails_when_a_session_is_expected(bots):
    result = _run(bots(["ana", "bob"]), "room-1")
    stripped = Transcript.from_dict(result.transcript.to_dict())
    for e in stripped.entries:
        for v in e["verdicts"]:
            v.pop("session"), v.pop("nonce")
    assert not verify_transcript(stripped, require_signed=True, expected_session="room-1")


def test_legacy_unbound_verdicts_still_verify_without_an_expected_session():
    ident = Identity.generate("A")
    verdict = Verdict("A", True, 0.5, "ok")
    signed = Verdict("A", True, 0.5, "ok", sig=ident.sign_verdict({"x": 1}, verdict),
                     pubkey_hex=ident.card().pubkey_hex)
    t = Transcript()
    t.record({"x": 1}, [signed])
    t.finalize("agreed", {"x": 1})
    assert verify_transcript(t, require_signed=True)
    assert "session" not in t.entries[0]["verdicts"][0]  # legacy hashes stay unchanged
