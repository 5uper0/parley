# Five-minute path: run Parley once and tell us what broke

Parley is an open-source Python library (Apache-2.0). It is early: version 0.2.1, no outside users yet. This page is the shortest way to run it and report back.

## Before you start

- You need Python 3.11 or newer for a tested path. Python 3.10 is the declared floor but untested ([issue 36](https://github.com/5uper0/parley/issues/36)). If you run 3.10, say so in your report.
- Install `parley-consensus`. The package called `parley` on PyPI is an unrelated project.
- The core has no dependencies. Nothing is sent anywhere by this path.

## Steps

1. Make a clean environment and install:

   ```bash
   python3 -m venv parley-try && source parley-try/bin/activate
   pip install parley-consensus
   ```

2. Download and run the demo script:

   ```bash
   curl -O https://raw.githubusercontent.com/5uper0/parley/main/examples/five_minute_run.py
   python five_minute_run.py
   ```

   It decides a three-person dinner, writes `receipt.json`, re-checks the record with the same function the `parley_verify_receipt` MCP tool uses, then edits one verdict and checks again. It should end with `PASS` and exit code 0.

3. Check the receipt yourself. `receipt.json` holds the transcript and the hash. In the same environment:

   ```bash
   python - <<'PY'
   import json
   from parley.mcp import tool_verify_receipt
   r = json.load(open("receipt.json"))
   print(tool_verify_receipt({"transcript": r["transcript"], "sha256": r["sha256"]}))
   PY
   ```

   `match` and `max_min_verified` should both be `True`. Change any character in `receipt.json` and run it again: `match` becomes `False`.

4. Paste the block the script prints, or any error, into [Discussion 92](https://github.com/5uper0/parley/discussions/92). Include your Python version and operating system. If something broke, the error text is the most useful thing you can send.

If you use an MCP host (Claude, Cursor), the same two calls are the `parley_decide` and `parley_verify_receipt` tools. The README shows the arguments.

## What this proves, and what it does not

- The receipt is tamper-evident: an edited record no longer matches its hash, and the decision can be recomputed from the recorded verdicts.
- The record holds masked verdicts only (`ok` or `red-line`, plus a score). It does not name which limit was crossed.
- It does not prove the participants are who the record says, and it does not stop an owner who tries to cheat. Scores and accept or reject answers still show some of each person's range. See [SECURITY.md](../SECURITY.md).
- The script runs all three agents in one process, so that process sees every sheet. Privacy holds when each owner's agent runs as its own process (`examples/run_env.py`).
