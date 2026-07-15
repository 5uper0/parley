"""A bot: an Agent wrapped in a hardened HTTP server.

  GET  /card      -> {"owner","pubkey_hex","protocol"}      (discovery; no sheet)
  POST /consider  -> {"owner","acceptable","score","reason","sig","pubkey_hex"}

Hardening (Exp 0): Ed25519-signed verdicts (coordinator can't forge), optional bearer
auth, per-client rate limiting, body-size cap, and input validation — closing the
preference-extraction and DoS holes. The private sheet never crosses the wire.

Run standalone:  PARLEY_TOKEN=$(openssl rand -hex 16) python -m parley.net.bot --profile ana --port 8101
"""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from parley.agent import Agent, Verdict
from parley.net.identity import Identity
from parley.net.profiles import PROFILES

MAX_BODY = 4096  # bytes; a legitimate /consider body is ~100 bytes


class _RateLimiter:
    """Fixed-window per-client counter. None disables it."""
    def __init__(self, spec):
        self.max, self.window = (spec or (0, 0))
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, client):
        if not self.max:
            return True
        now = time.monotonic()
        with self._lock:
            count, start = self._hits.get(client, (0, now))
            if now - start >= self.window:
                count, start = 0, now
            count += 1
            self._hits[client] = (count, start)
            return count <= self.max


def _make_handler(agent, identity, auth_token, limiter):
    class Handler(BaseHTTPRequestHandler):
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
            return got == f"Bearer {auth_token}"

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
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > MAX_BODY:
                self._send(413, {"error": "payload too large"})
                return
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                option = data["option"]
                if not isinstance(option, dict):
                    raise ValueError("option must be an object")
                v = agent.consider(option)  # predicates may raise on malformed options
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
    httpd = serve(sheet.owner, sheet, args.host, args.port, auth_token=token)
    auth = "auth ON" if token else "auth off (dev)"
    print(f"[bot:{sheet.owner}] listening on {args.host}:{args.port} — signed, {auth}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
