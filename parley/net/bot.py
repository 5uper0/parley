"""A bot: an Agent wrapped in a hardened HTTP server.

  GET  /card      -> {"owner","pubkey_hex","protocol"}      (discovery; no sheet)
  POST /consider  -> {"owner","acceptable","score","reason","sig","pubkey_hex"}

Hardening (Exp 0): Ed25519-signed verdicts (coordinator can't alter a bot's signed verdict), optional bearer
auth, per-client rate limiting, body-size cap, and input validation — closing the
preference-extraction and DoS holes. The private sheet never crosses the wire.

Run standalone:  PARLEY_TOKEN=$(openssl rand -hex 16) python -m parley.net.bot --profile ana --port 8101
"""
import argparse
import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from parley.agent import Agent, Verdict
from parley.net.identity import Identity
from parley.net.profiles import PROFILES
from parley.preferences import UtilityError

MAX_BODY = 4096  # bytes; a legitimate /consider body is ~100 bytes
# Per-read idle timeout (seconds): a client that goes silent is dropped. It is NOT a total
# deadline — each socket read gets its own 10s, so a client trickling one byte per read can hold
# a thread for up to ~MAX_BODY reads. A stall is closed quietly by BaseHTTPRequestHandler.
REQUEST_TIMEOUT = 10


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name}")


class _RateLimiter:
    """Fixed-window per-client counter. None disables it."""
    def __init__(self, spec):
        self.max, self.window = (spec or (0, 0))
        self._hits = {}
        self._lock = threading.Lock()
        self._next_sweep = 0.0

    def allow(self, client):
        if not self.max:
            return True
        now = time.monotonic()
        with self._lock:
            if now >= self._next_sweep:  # drop clients whose window has elapsed, or the map only grows
                self._hits = {c: h for c, h in self._hits.items() if now - h[1] < self.window}
                self._next_sweep = now + self.window
            count, start = self._hits.get(client, (0, now))
            if now - start >= self.window:
                count, start = 0, now
            count += 1
            self._hits[client] = (count, start)
            return count <= self.max


def _make_handler(agent, identity, auth_token, limiter):
    class Handler(BaseHTTPRequestHandler):
        timeout = REQUEST_TIMEOUT

        def log_message(self, *args):
            pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authed(self):
            if not auth_token:
                return True
            got = self.headers.get("Authorization", "")
            return hmac.compare_digest(got.encode("utf-8"), f"Bearer {auth_token}".encode("utf-8"))

        def do_GET(self):
            if self.path == "/card":
                card = {"owner": agent.owner, "protocol": "parley/0.1"}
                if identity:
                    card["pubkey_hex"] = identity.card().pubkey_hex
                self._send(200, card)
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/consider":
                self._send(404, {"error": "not found"})
                return
            if not self._authed():
                self._send(401, {"error": "unauthorized"})
                return
            if not limiter.allow(self.client_address[0]):
                self._send(429, {"error": "rate limited"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                length = -1
            if length < 0:  # rfile.read(-1) reads to EOF, bypassing MAX_BODY
                self._send(400, {"error": "invalid content-length"})
                return
            if length > MAX_BODY:
                self._send(413, {"error": "payload too large"})
                return
            try:
                data = json.loads(self.rfile.read(length) or b"{}", parse_constant=_reject_constant)
                option = data["option"]
                if not isinstance(option, dict):
                    raise ValueError("option must be an object")
                v = agent.consider(option)  # predicates may raise on malformed options
            except UtilityError:  # NaN can only come from the sheet: the body parser refuses NaN/Infinity
                self._send(500, {"error": "internal error"})
                return
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                self._send(400, {"error": "invalid option"})
                return
            out = {"owner": v.owner, "acceptable": v.acceptable,
                   "score": v.score, "reason": v.reason}
            if identity:
                out["sig"] = identity.sign_verdict(option, v)
                out["pubkey_hex"] = identity.card().pubkey_hex
            self._send(200, out)

    return Handler


def serve(owner, sheet, host="127.0.0.1", port=0, identity="auto",
          auth_token=None, rate_limit=None):
    """Build (don't run) a bot server. `identity='auto'` generates a signing key."""
    if auth_token == "":  # "" is falsy, so it would silently turn auth off
        raise ValueError("auth_token is empty; pass None to run without auth")
    agent = Agent(owner, sheet)
    if identity == "auto":
        identity = Identity.generate(owner)
    limiter = _RateLimiter(rate_limit)
    httpd = ThreadingHTTPServer((host, port), _make_handler(agent, identity, auth_token, limiter))
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    sheet = PROFILES[args.profile]()
    token = os.environ.get("PARLEY_TOKEN")  # auth on if set
    if token == "":
        raise SystemExit("PARLEY_TOKEN is set but empty; unset it to run without auth")
    httpd = serve(sheet.owner, sheet, args.host, args.port, auth_token=token)
    auth = "auth ON" if token else "auth off (dev)"
    print(f"[bot:{sheet.owner}] listening on {args.host}:{args.port} — signed, {auth}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
