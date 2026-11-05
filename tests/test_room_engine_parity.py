"""The browser engine (`room/engine.mjs`) must give byte-identical verdicts and the same transcript
hash as the Python engine, on frozen golden vectors. Also keeps the vectors honest."""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def test_golden_vectors_are_current():
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen-golden-vectors.py"), "--check"],
                          capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_engine_matches_python_on_every_golden_vector():
    proc = subprocess.run(["node", "--test", os.path.join(ROOT, "room", "test", "parity.test.mjs")],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
