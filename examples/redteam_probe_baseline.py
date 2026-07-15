"""Red-team BASELINE (the "before"): reconstruct a bot's PRIVATE red line by probing /consider.

Demonstrates that "the sheet never crosses the wire" does NOT mean the preferences are
private: an unauthenticated attacker who can reach the port recovers them by enumeration.

NOTE — this attack SUCCEEDS on purpose: it runs an *unhardened* bot to motivate the fix.
It is NOT a vulnerability in the shipped server. The hardening (auth → 401, rate-limit →
429, body-cap → 413) lives in `parley/net/bot.py` and is proven by `tests/test_redteam.py`
(and a hardened bot blocks all 60 probes). Seeing the reconstruction here is expected.
"""
import threading
import itertools
from parley.net.bot import serve
from parley.net.client import RemoteAgent
from parley.net.profiles import PROFILES

# stand up Ana's bot (attacker does NOT see this sheet)
sheet = PROFILES["ana"]()
httpd = serve(sheet.owner, sheet, port=0)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

attacker = RemoteAgent(f"http://127.0.0.1:{port}")  # only knows the URL
print(f"Attacker target: {attacker.owner} @ 127.0.0.1:{port} (no sheet, no auth)\n")

days = ["mon", "tue", "wed", "thu", "fri"]
hours = list(range(8, 20))
accepted, rejected = [], []
for d, h in itertools.product(days, hours):
    v = attacker.consider({"day": d, "hour": h})
    (accepted if v.acceptable else rejected).append((d, h))

# infer the red line from the accept/reject boundary
rej_hours = sorted({h for _, h in rejected})
acc_hours = sorted({h for _, h in accepted})
print(f"probes: {len(accepted)+len(rejected)}  accepted={len(accepted)}  rejected={len(rejected)}")
print(f"rejected hours: {rej_hours}")
print(f"accepted hours: {acc_hours}")
if acc_hours:
    print(f"\n>>> RECONSTRUCTED red line: hour >= {min(acc_hours)}  (Ana's real one is 'no-mornings: hour>=11')")
print(">>> Also leaked: soft scores per option reveal her ranking (tue preferred).")
httpd.shutdown()
