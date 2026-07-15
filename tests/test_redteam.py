"""Red team: the attacks that MUST fail after Exp 0 hardening.

Baseline (before hardening) reconstructed a bot's private red line with 60 unauthenticated
probes. These tests pin that hole shut: no token -> 401, brute-force -> 429, oversized or
malformed bodies -> 4xx (never a 500 / crash / unbounded read).
"""
import json
import threading
import urllib.error
import urllib.request

import pytest

pytest.importorskip("nacl")

from parley.net.bot import serve
from parley.net.profiles import PROFILES


def _start(**kw):
    sheet = PROFILES["ana"]()
    httpd = serve(sheet.owner, sheet, port=0, **kw)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}"


def _post(url, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url + "/consider", data=json.dumps(body).encode(), headers=headers)
    return urllib.request.urlopen(req, timeout=5)


def test_extraction_blocked_without_token():
    httpd, url = _start(auth_token="s3cret")
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url, {"option": {"day": "mon", "hour": 9}})  # attacker has no token
        assert e.value.code == 401
    finally:
        httpd.shutdown()


def test_rate_limit_throttles_brute_force_probing():
    httpd, url = _start(auth_token="s3cret", rate_limit=(5, 60))
    try:
        codes = []
        for _ in range(12):
            try:
                codes.append(_post(url, {"option": {"day": "mon", "hour": 15}}, token="s3cret").status)
            except urllib.error.HTTPError as e:
                codes.append(e.code)
        assert 429 in codes  # enumeration gets cut off
    finally:
        httpd.shutdown()


def test_oversized_body_rejected():
    httpd, url = _start(auth_token="s3cret")
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url, {"option": {"day": "mon", "hour": 15, "junk": "x" * 9000}}, token="s3cret")
        assert e.value.code == 413
    finally:
        httpd.shutdown()


def test_malformed_option_is_client_error_not_crash():
    httpd, url = _start(auth_token="s3cret")
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url, {"option": {"foo": "bar"}}, token="s3cret")  # predicate needs 'hour'
        assert e.value.code == 400
    finally:
        httpd.shutdown()
