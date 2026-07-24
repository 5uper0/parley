"""Self-hosted money-shot demo — the real engine behind a single web page.

    python examples/demo/server.py            # then open http://127.0.0.1:8080

Zero-dependency (stdlib only). Loads a declarative recipe, runs the REAL consensus, and serves the
result to the page: per-party masked verdicts, the max-min decision, the deterministically-blocked
option, the SHA-256 transcript, and a non-betrayal replay ("verify"). A scenario picker chooses which
whitelisted recipe to run; each recipe carries an optional plain-language `presentation` block so the
page can speak human. No signing here (that's the optional pynacl layer) — the receipt is
tamper-evidence + local replay.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse, parse_qs

from parley.spec import DecisionSpec

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")

# Whitelist of demo recipes (key -> filename); key order = the scenario-picker order. This is also the
# SECURITY boundary: the ?recipe= key is looked up here, never joined into a path, so no traversal is
# possible. `p2p` is the default — the flagship everyday scenario.
RECIPES = {
    "p2p":         "recipe_p2p_dispute.json",
    "estate":      "recipe_estate.json",
    "contract":    "recipe_contract_terms.json",
    "kyc":         "recipe_kyc.json",
    "partnership": "recipe_partnership_buyout.json",
    "dao":         "recipe_dao_treasury.json",
}
DEFAULT_RECIPE = "p2p"
# Back-compat: proofcard.py + docs import RECIPE as the default recipe path.
RECIPE = os.path.join(HERE, RECIPES[DEFAULT_RECIPE])


def _recipe_path(key: str):
    """Whitelisted key -> absolute path, or None if the key is unknown (fails closed, no traversal)."""
    fn = RECIPES.get(key)
    return os.path.join(HERE, fn) if fn else None


# The recipe set is a fixed whitelist of static files, so every /api response is deterministic.
# Memoise them: the public demo then serves cached JSON instead of re-running consensus per request,
# which removes the anonymous CPU-flood vector (a bare `while true: curl /api/run` can't burn the box).
_RUN_CACHE: dict = {}
_RECIPES_CACHE: Optional[str] = None


def run_recipe(path: str) -> dict:
    """Run the recipe through the real engine and shape a JSON-friendly result for the page."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    spec = DecisionSpec.from_dict(raw)
    result = spec.run()
    entries = []
    for e in result.transcript.entries:
        verdicts = [{"owner": v["owner"], "acceptable": v["acceptable"],
                     "score": round(v["score"], 3), "reason": v["reason"]}
                    for v in e["verdicts"]]
        feasible = all(v["acceptable"] for v in verdicts)
        floor = min((v["score"] for v in verdicts), default=0.0) if feasible else None
        entries.append({"option": e["option"], "verdicts": verdicts,
                        "feasible": feasible, "floor": floor})
    # non-betrayal: replay each party's OWN sheet against the final decision
    non_betrayal = {p.owner: result.transcript.verify_non_betrayal(p.to_sheet(), result.decision)
                    for p in spec.parties}
    return {
        "title": spec.title,
        # each party carries its raw red lines (the technical view) alongside the name
        "parties": [{"owner": p.owner, "redlines": [c.describe() for c in p.hard]} for p in spec.parties],
        "entries": entries,
        "decision": result.decision,
        "status": result.status,
        "hash": result.transcript.hash(),
        "non_betrayal": non_betrayal,
        # optional plain-language layer (data only; ignored by the core spec)
        "presentation": raw.get("presentation"),
        # optional provenance: the real dispute this scenario is grounded in (data only)
        "source": raw.get("source"),
    }


def list_recipes() -> list:
    """The scenario-picker list: [{key, title, situation}] in whitelist order."""
    out = []
    for key, fn in RECIPES.items():
        with open(os.path.join(HERE, fn), encoding="utf-8") as fh:
            raw = json.load(fh)
        pres = raw.get("presentation") or {}
        out.append({"key": key, "title": raw.get("title", key), "situation": pres.get("situation", "")})
    return out


def _cached_run(path: str) -> str:
    if path not in _RUN_CACHE:
        _RUN_CACHE[path] = json.dumps(run_recipe(path))
    return _RUN_CACHE[path]


def _cached_recipes() -> str:
    global _RECIPES_CACHE
    if _RECIPES_CACHE is None:
        _RECIPES_CACHE = json.dumps(list_recipes())
    return _RECIPES_CACHE


class _Handler(BaseHTTPRequestHandler):
    # Bound the per-connection socket so a slow client (slowloris) can't pin a worker thread forever
    # on the public demo. A legitimate request completes in well under a second.
    timeout = 10

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            with open(INDEX, encoding="utf-8") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif path == "/api/recipes":
            self._send(200, _cached_recipes(), "application/json")
        elif path == "/api/run":
            key = parse_qs(parsed.query).get("recipe", [DEFAULT_RECIPE])[0]
            rp = _recipe_path(key)
            if rp is None:
                self._send(404, json.dumps({"error": "unknown recipe"}), "application/json")
            else:
                self._send(200, _cached_run(rp), "application/json")
        else:
            self._send(404, json.dumps({"error": "not found"}), "application/json")


def serve(host="127.0.0.1", port=8080):
    httpd = ThreadingHTTPServer((host, port), _Handler)
    print(f"[parley demo] http://{host}:{port}  (Ctrl-C to stop)", flush=True)
    return httpd


def bind_from_env(env=None):
    """(host, port) from PARLEY_HOST/PARLEY_PORT — lets `docker run` bind 0.0.0.0 without code edits.

    Falls back to the platform-injected ``PORT`` (Render/Heroku/Cloud Run set it dynamically) when
    ``PARLEY_PORT`` is unset, so a hosted deploy binds the assigned port with no config edit and the
    health check passes on the first try."""
    env = os.environ if env is None else env
    host = env.get("PARLEY_HOST", "127.0.0.1")
    port = env.get("PARLEY_PORT") or env.get("PORT") or "8080"
    return host, int(port)


if __name__ == "__main__":
    serve(*bind_from_env()).serve_forever()
