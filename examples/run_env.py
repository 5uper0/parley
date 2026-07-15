"""Spin up a real environment: each bot is its OWN OS process serving HTTP.

The coordinator discovers them over the wire, runs a parley, and each owner verifies
non-betrayal with their own local sheet. Bots never send their private constraints.

    python examples/run_env.py ana bob
    python examples/run_env.py ana bob cara dan eve
    python examples/run_env.py            # runs the 2-bot then 5-bot scenario
"""
import os
import subprocess
import sys
import time
import urllib.request

from parley.consensus import run_consensus
from parley.net.client import discover
from parley.net.profiles import PROFILES, OPTIONS


def _wait_up(url, tries=60):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url + "/card", timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def _label(o):
    return f'{o["day"].capitalize()} {o["hour"]:02d}:00'


def run_scenario(profiles, base_port=8101):
    print("\n" + "=" * 62)
    print(f"  ENVIRONMENT: {len(profiles)} bots as separate processes over HTTP")
    print("=" * 62)
    env = dict(os.environ, PYTHONPATH=os.getcwd())
    procs, urls = [], []
    for i, p in enumerate(profiles):
        port = base_port + i
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "parley.net.bot", "--profile", p, "--port", str(port)],
            env=env,
        ))
        urls.append(f"http://127.0.0.1:{port}")
    try:
        for u in urls:
            if not _wait_up(u):
                raise RuntimeError(f"bot at {u} did not come up")
        agents = discover(urls)  # fetch Agent Cards over the wire
        print(f"\n  Discovered {len(agents)} bots: {', '.join(a.owner for a in agents)}")
        print("  Coordinator asks each bot to /consider every option (HTTP)…\n")

        r = run_consensus(agents, OPTIONS)
        for e in r.transcript.entries:
            marks = "  ".join(
                f'{v["owner"]}{"✓" if v["acceptable"] else "✗"}' for v in e["verdicts"]
            )
            print(f'    {_label(e["option"]):>12}   {marks}')
        print()
        if r.status == "agreed":
            print(f"  ✅ Consensus over the network: {_label(r.decision)}")
        else:
            print("  ⛔ Honest deadlock — no slot clears everyone's red lines.")
        print(f"  transcript sha256: {r.transcript.hash()[:16]}…")

        print("\n  Each owner verifies non-betrayal with their OWN local sheet:")
        for p in profiles:
            ok = r.transcript.verify_non_betrayal(PROFILES[p](), r.decision)
            print(f'    {PROFILES[p]().owner:>5}: red lines held? {"yes ✓" if ok else "NO ✗"}')
    finally:
        for pr in procs:
            pr.terminate()
        for pr in procs:
            pr.wait(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_scenario(sys.argv[1:])
    else:
        run_scenario(["ana", "bob"], base_port=8101)
        run_scenario(["ana", "bob", "cara", "dan", "eve"], base_port=8201)
