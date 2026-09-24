"""Net-layer hardening: the edges of auth, rate limiting, body parsing, signatures, and the
client's trust in what a bot sends back.

The bot must answer every malformed request with a 4xx and never a verdict, a dropped
connection, or a leaked constraint name. The client must refuse a reply that is not exactly
the masked verdict shape, because run_consensus reads `acceptable` by truthiness and `score`
by ordering. Everything runs on ephemeral ports, headless.
"""
import json
import importlib.util
import os
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytest.importorskip("nacl")

from parley.consensus import run_consensus
from parley.net import bot as bot_mod
from parley.net.bot import MAX_BODY, _RateLimiter, serve
from parley.net.client import RemoteAgent
from parley.net.identity import AgentCard, Identity, verdict_payload, verify_transcript
from parley.net.profiles import OPTIONS, PROFILES

CONSTRAINT_NAMES = ("no-mornings", "no-fridays", "kids-pickup", "no-mondays", "afternoons-only")
TOKEN = "s3cret-token"


@pytest.fixture
def launch():
    servers = []

    def start(profile="ana", **kw):
        sheet = PROFILES[profile]()
        httpd = serve(sheet.owner, sheet, port=0, **kw)
        servers.append(httpd)
        threading.Thread(target=httpd.serve_forever, args=(0.05,), daemon=True).start()
        return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"

    yield start
    for s in servers:
        s.shutdown()
        s.server_close()


def _request(url, path="/consider", body=None, raw=None, headers=None, method=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(url + path, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _raw(port, payload, timeout=5, half_close=False):
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as c:
        c.sendall(payload)
        if half_close:
            c.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = c.recv(4096)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)


def _bearer(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


GOOD = {"option": {"day": "tue", "hour": 14}}


# --- auth -----------------------------------------------------------------------------------

@pytest.mark.parametrize("header", [
    None,
    "Bearer wrong",
    "Bearer ",
    "Bearer",
    TOKEN,                          # no scheme
    f"bearer {TOKEN}",              # scheme is matched exactly
    f"Bearer {TOKEN}x",             # suffix
    f"Bearer {TOKEN[:-1]}",         # prefix
    f"Bearer  {TOKEN}",             # extra space
    f"Basic {TOKEN}",
])
def test_every_near_miss_token_is_rejected_without_a_verdict(launch, header):
    _, url = launch(auth_token=TOKEN)
    code, body = _request(url, body=GOOD, headers={"Authorization": header} if header else {})
    assert code == 401
    assert json.loads(body) == {"error": "unauthorized"}


def test_correct_token_gets_a_verdict(launch):
    _, url = launch(auth_token=TOKEN)
    code, body = _request(url, body=GOOD, headers=_bearer())
    assert code == 200 and json.loads(body)["acceptable"] is True


def test_auth_is_checked_before_the_body_is_parsed(launch):
    _, url = launch(auth_token=TOKEN)
    code, _ = _request(url, raw=b"not json at all")
    assert code == 401  # an unauthenticated caller learns nothing about parsing either


# --- rate limiting --------------------------------------------------------------------------

def test_rate_limit_window_resets_and_is_per_client(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(bot_mod.time, "monotonic", lambda: now[0])
    rl = _RateLimiter((2, 60))
    assert [rl.allow("a") for _ in range(3)] == [True, True, False]
    assert rl.allow("b") is True            # another client has its own budget
    now[0] += 59.9
    assert rl.allow("a") is False           # still inside the window
    now[0] += 0.1
    assert rl.allow("a") is True            # window elapsed
    assert _RateLimiter(None).allow("a") is True


def test_throttled_request_gets_no_verdict(launch):
    _, url = launch(auth_token=TOKEN, rate_limit=(1, 60))
    assert _request(url, body=GOOD, headers=_bearer())[0] == 200
    code, body = _request(url, body=GOOD, headers=_bearer())
    assert code == 429 and json.loads(body) == {"error": "rate limited"}


# --- input validation -----------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    b"",                                   # empty body
    b"{not json",
    b"\xff\xfe\x00",                       # not UTF-8
    b"[]",                                 # JSON, but not an object
    b'"option"',
    b"{}",                                 # no option
    b'{"option": [1, 2]}',                 # option not an object
    b'{"option": "tue"}',
    b'{"option": null}',
    b'{"option": {"day": "tue"}}',         # predicate needs "hour"
    b'{"option": {"day": "tue", "hour": "14"}}',  # wrong type for the predicate
    b'{"option": {"day": "tue", "hour": null}}',
])
def test_malformed_body_is_a_400_that_names_no_constraint(launch, raw):
    _, url = launch()
    code, body = _request(url, raw=raw, headers={"Content-Type": "application/json"})
    assert code == 400
    assert json.loads(body) == {"error": "invalid option"}


def test_body_one_byte_over_the_cap_is_rejected_and_at_the_cap_is_read(launch):
    _, url = launch()
    pad = MAX_BODY - len(json.dumps({"option": {"day": "tue", "hour": 14, "p": ""}}))
    at_cap = json.dumps({"option": {"day": "tue", "hour": 14, "p": "x" * pad}}).encode()
    assert len(at_cap) == MAX_BODY
    assert _request(url, raw=at_cap)[0] == 200
    assert _request(url, raw=at_cap + b" ")[0] == 413


def test_negative_content_length_cannot_bypass_the_body_cap(launch):
    # rfile.read(-1) reads to EOF: before the fix this streamed an unbounded body and answered 200
    httpd, _ = launch()
    body = json.dumps({"option": {"day": "tue", "hour": 14, "j": "x" * (4 * MAX_BODY)}}).encode()
    resp = _raw(httpd.server_address[1],
                b"POST /consider HTTP/1.1\r\nHost: x\r\nContent-Length: -1\r\n\r\n" + body,
                half_close=True)
    assert resp.startswith(b"HTTP/1.0 400")
    assert b'"acceptable"' not in resp


def test_non_numeric_content_length_is_a_400_not_a_dropped_connection(launch):
    httpd, _ = launch()
    resp = _raw(httpd.server_address[1],
                b"POST /consider HTTP/1.1\r\nHost: x\r\nContent-Length: abc\r\n\r\n{}")
    assert resp.startswith(b"HTTP/1.0 400")


def test_stalled_client_is_disconnected_instead_of_pinning_a_thread(launch, capfd):
    httpd, url = launch()
    httpd.RequestHandlerClass.timeout = 0.3  # production value is REQUEST_TIMEOUT
    assert bot_mod.REQUEST_TIMEOUT > 0
    # promises 100 bytes, sends 1, then goes silent: the server must hang up, not wait forever
    resp = _raw(httpd.server_address[1],
                b"POST /consider HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n\r\n{", timeout=5)
    assert b'"acceptable"' not in resp
    assert _request(url, path="/card")[0] == 200  # and the server still serves everyone else
    assert capfd.readouterr().err == ""  # a stall is dropped quietly, not a traceback per client


def test_unknown_paths_are_404(launch):
    _, url = launch(auth_token=TOKEN)
    assert _request(url, path="/sheet")[0] == 404
    assert _request(url, path="/card/../sheet")[0] == 404
    assert _request(url, path="/card", body=GOOD, headers=_bearer())[0] == 404  # POST /card
    assert _request(url, path="/consider", headers=_bearer())[0] == 404         # GET /consider


# --- what crosses the wire ------------------------------------------------------------------

def test_card_is_public_and_carries_no_sheet(launch):
    _, url = launch(auth_token=TOKEN)
    code, body = _request(url, path="/card")  # discovery needs no token
    card = json.loads(body)
    assert code == 200 and set(card) == {"owner", "protocol", "pubkey_hex"}


def test_red_line_verdict_on_the_wire_is_masked(launch):
    _, url = launch()
    for opt in OPTIONS:
        raw = _request(url, body={"option": opt})[1].decode()
        assert not any(name in raw for name in CONSTRAINT_NAMES)
    d = json.loads(_request(url, body={"option": {"day": "mon", "hour": 9}})[1])
    assert d["acceptable"] is False and d["reason"] == "red-line"


def test_unsigned_bot_sends_no_signature_fields(launch):
    _, url = launch(identity=None)
    assert "pubkey_hex" not in json.loads(_request(url, path="/card")[1])
    d = json.loads(_request(url, body=GOOD)[1])
    assert "sig" not in d and "pubkey_hex" not in d


def test_wire_signature_binds_the_exact_option_and_card_key(launch):
    _, url = launch()
    card = json.loads(_request(url, path="/card")[1])
    d = json.loads(_request(url, body=GOOD)[1])
    assert d["pubkey_hex"] == card["pubkey_hex"]
    ac = AgentCard(card["owner"], card["pubkey_hex"])
    args = (d["owner"], d["acceptable"], d["score"], d["reason"])
    assert ac.verify(verdict_payload(GOOD["option"], *args), d["sig"]) is True
    assert ac.verify(verdict_payload({"day": "tue", "hour": 11}, *args), d["sig"]) is False


# --- forged and replayed verdicts in a transcript -------------------------------------------

@pytest.fixture
def signed_run(launch):
    urls = [launch(p)[1] for p in ("ana", "bob")]
    r = run_consensus([RemoteAgent(u) for u in urls], OPTIONS)
    assert verify_transcript(r.transcript, require_signed=True) is True
    return r.transcript


def test_verdict_replayed_onto_another_option_fails(signed_run):
    a, b = signed_run.entries[0], signed_run.entries[1]
    b["verdicts"][0] = dict(a["verdicts"][0])
    assert verify_transcript(signed_run) is False


def test_verdict_relabelled_to_another_owner_fails(signed_run):
    signed_run.entries[0]["verdicts"][0]["owner"] = "Bob"
    assert verify_transcript(signed_run) is False


def test_score_nudged_after_signing_fails(signed_run):
    v = signed_run.entries[0]["verdicts"][0]
    v["score"] = v["score"] + 1e-9
    assert verify_transcript(signed_run) is False


@pytest.mark.parametrize("field,value", [
    ("sig", "zz"), ("sig", "00" * 64), ("sig", "00" * 10), ("sig", 123), ("sig", ["ab"]),
    ("pubkey_hex", "zz"), ("pubkey_hex", "00" * 16), ("pubkey_hex", 5),
])
def test_garbage_signature_material_verifies_false_not_raises(signed_run, field, value):
    signed_run.entries[0]["verdicts"][0][field] = value
    assert verify_transcript(signed_run) is False


# --- the client against a hostile or broken bot ---------------------------------------------

class _FakeBot:
    """A bot that answers /card normally and /consider with whatever the test says."""

    def __init__(self, consider_body, card=None, stall=None):
        fake = self
        self.consider_body = consider_body
        self.card = card if card is not None else {"owner": "Ana", "protocol": "parley/0.1"}
        self.stall = stall

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _reply(self, payload):
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._reply(fake.card)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if fake.stall is not None:
                    fake.stall.wait(5)
                self._reply(fake.consider_body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        if self.stall is not None:
            self.stall.set()
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def fake_bot():
    made = []

    def make(*a, **kw):
        fb = _FakeBot(*a, **kw)
        made.append(fb)
        return fb

    yield make
    for fb in made:
        fb.close()


OK_VERDICT = {"owner": "Ana", "acceptable": True, "score": 0.5, "reason": "ok"}


def _with(**kw):
    return {**OK_VERDICT, **kw}


def test_well_formed_reply_is_accepted(fake_bot):
    v = RemoteAgent(fake_bot(OK_VERDICT).url).consider({"day": "tue"})
    assert (v.owner, v.acceptable, v.score, v.reason, v.sig) == ("Ana", True, 0.5, "ok", None)


@pytest.mark.parametrize("reply", [
    b"<html>502 Bad Gateway</html>",
    b"",
    b"[]",
    b'"ok"',
    {"owner": "Ana"},                           # missing fields
    _with(acceptable="false"),                  # truthy string would read as acceptable
    _with(acceptable=1),
    _with(acceptable=None),
    _with(score="0.9"),
    _with(score=True),
    _with(score=float("nan")),
    _with(score=float("inf")),
    _with(score=1.5),
    _with(score=-0.1),
    _with(owner="Bob"),                         # speaks for someone other than its card
    _with(reason="no-mornings"),                # unmasked reason
    _with(reason="red-line"),                   # reason contradicts acceptable
    _with(acceptable=False, reason="ok"),
    _with(sig=123),
    _with(pubkey_hex={"k": 1}),
])
def test_malformed_reply_is_refused_not_turned_into_a_verdict(fake_bot, reply):
    agent = RemoteAgent(fake_bot(reply).url)
    with pytest.raises(ValueError):
        agent.consider({"day": "tue"})


def test_a_bot_lying_about_acceptable_cannot_carry_a_consensus(fake_bot, launch):
    liar = RemoteAgent(fake_bot(_with(acceptable="false", reason="red-line")).url)
    honest = RemoteAgent(launch("bob")[1])
    with pytest.raises(ValueError):
        run_consensus([honest, liar], OPTIONS)


@pytest.mark.parametrize("card", [{}, {"owner": ""}, {"owner": 7}, ["Ana"]])
def test_malformed_card_is_refused_at_discovery(fake_bot, card):
    with pytest.raises(ValueError):
        RemoteAgent(fake_bot(OK_VERDICT, card=card).url)


def test_bot_that_hangs_times_out_instead_of_blocking_the_parley(fake_bot):
    agent = RemoteAgent(fake_bot(OK_VERDICT, stall=threading.Event()).url, timeout=0.3)
    with pytest.raises(OSError):  # socket timeout or URLError, both OSError
        agent.consider({"day": "tue"})


def test_client_sends_bearer_token_and_surfaces_401(launch):
    _, url = launch(auth_token=TOKEN)
    assert RemoteAgent(url, token=TOKEN).consider({"day": "tue", "hour": 14}).acceptable is True
    with pytest.raises(urllib.error.HTTPError) as e:
        RemoteAgent(url, token="wrong").consider({"day": "tue", "hour": 14})
    assert e.value.code == 401


# --- the reply must be signed by the key the card advertised -----------------------------

CARD_ID = Identity.generate("Ana")
MITM_ID = Identity.generate("Ana")
CARD_KEY = CARD_ID.card().pubkey_hex
SIGNED_CARD = {"owner": "Ana", "protocol": "parley/0.1", "pubkey_hex": CARD_KEY}
OPTION = {"day": "tue"}


def _signed_by(identity, **kw):
    v = _with(**kw)
    sig = identity.sign(verdict_payload(OPTION, v["owner"], v["acceptable"], v["score"],
                                        v["reason"]))
    return {**v, "sig": sig, "pubkey_hex": identity.card().pubkey_hex}


def test_a_reply_signed_by_the_card_key_is_accepted(fake_bot):
    v = RemoteAgent(fake_bot(_signed_by(CARD_ID), card=SIGNED_CARD).url).consider(OPTION)
    assert v.pubkey_hex == CARD_KEY and v.sig


def test_a_reply_signed_by_another_key_is_refused(fake_bot):
    # a man in the middle signs a valid verdict with its own key; verify_transcript alone would
    # accept it later, because it checks each signature against the key embedded beside it
    agent = RemoteAgent(fake_bot(_signed_by(MITM_ID), card=SIGNED_CARD).url)
    with pytest.raises(ValueError):
        agent.consider(OPTION)


@pytest.mark.parametrize("reply", [
    OK_VERDICT,                                     # signature and key both stripped
    _with(pubkey_hex=CARD_KEY),                     # key, no sig
    _with(pubkey_hex=CARD_KEY, sig=""),             # key, empty sig
    {**_signed_by(CARD_ID), "pubkey_hex": None},    # sig, key dropped
])
def test_a_reply_missing_its_signature_is_refused_when_the_card_has_a_key(fake_bot, reply):
    agent = RemoteAgent(fake_bot(reply, card=SIGNED_CARD).url)
    with pytest.raises(ValueError):
        agent.consider(OPTION)


def test_an_unsigned_bot_still_works_end_to_end(launch):
    agents = [RemoteAgent(launch(p, identity=None)[1]) for p in ("ana", "bob")]
    assert all(a.pubkey_hex is None for a in agents)
    r = run_consensus(agents, OPTIONS)
    assert r.status == "agreed"
    assert all(v["sig"] is None for e in r.transcript.entries for v in e["verdicts"])


def test_a_signed_run_over_http_carries_the_card_keys_and_verifies(launch):
    agents = [RemoteAgent(launch(p)[1]) for p in ("ana", "bob")]
    r = run_consensus(agents, OPTIONS)
    keys = {a.owner: a.pubkey_hex for a in agents}
    assert all(v["pubkey_hex"] == keys[v["owner"]]
               for e in r.transcript.entries for v in e["verdicts"])
    assert verify_transcript(r.transcript, require_signed=True) is True


# --- examples/run_env.py checks what the client does not ------------------------------------

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_spec = importlib.util.spec_from_file_location("run_env", os.path.join(ROOT, "examples", "run_env.py"))
run_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_env)


def test_a_garbage_signature_under_the_card_key_passes_the_client_but_stops_run_env(fake_bot):
    # the client only checks that a signature is present under the card's key
    forged = RemoteAgent(fake_bot(_with(pubkey_hex=CARD_KEY, sig="00" * 64), card=SIGNED_CARD).url)
    r = run_consensus([forged], [OPTION])
    assert r.status == "agreed"
    with pytest.raises(SystemExit) as e:
        run_env.check_signatures(r.transcript)
    assert e.value.code not in (0, None) and "signature check FAILED" in str(e.value.code)


def test_run_env_accepts_a_genuinely_signed_run(signed_run):
    run_env.check_signatures(signed_run)


def test_run_env_stops_the_scenario_when_signatures_do_not_verify(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(run_env, "verify_transcript", lambda *a, **kw: False)
    with pytest.raises(SystemExit) as e:
        run_env.run_scenario(["ana", "bob"], base_port=8401)
    assert "signature check FAILED" in str(e.value.code)


# --- follow-ups from the 2026-09-24 audits --------------------------------------------------

def test_an_owners_own_nan_utility_is_a_500_not_a_400_blaming_the_coordinator(launch):
    from parley.preferences import PreferenceSheet
    httpd = serve("Nan", PreferenceSheet("Nan", utility=lambda o: float("nan")), port=0)
    threading.Thread(target=httpd.serve_forever, args=(0.05,), daemon=True).start()
    try:
        code, body = _request(f"http://127.0.0.1:{httpd.server_address[1]}", body=GOOD)
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert code == 500 and json.loads(body) == {"error": "internal error"}


@pytest.mark.parametrize("key", [123, {"k": 1}, ["ab"], "", "not-hex", "abc"])
def test_a_card_with_a_key_that_is_not_hex_is_refused_at_discovery(fake_bot, key):
    with pytest.raises(ValueError):
        RemoteAgent(fake_bot(OK_VERDICT, card={"owner": "Ana", "pubkey_hex": key}).url)


def test_the_rate_limiter_forgets_clients_whose_window_has_elapsed(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(bot_mod.time, "monotonic", lambda: now[0])
    rl = _RateLimiter((5, 60))
    for i in range(200):
        rl.allow(f"10.0.0.{i}")
    assert len(rl._hits) == 200
    now[0] += 61
    rl.allow("late")
    assert len(rl._hits) == 1


def test_an_empty_token_refuses_to_start_instead_of_silently_disabling_auth(monkeypatch):
    sheet = PROFILES["ana"]()
    with pytest.raises(ValueError):
        serve(sheet.owner, sheet, port=0, auth_token="")
    monkeypatch.setenv("PARLEY_TOKEN", "")
    monkeypatch.setattr("sys.argv", ["bot", "--profile", "ana", "--port", "0"])
    with pytest.raises(SystemExit):
        bot_mod.main()
