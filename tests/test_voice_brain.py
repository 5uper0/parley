"""The OpenRouter brain speaks, but the code decides — assert the invariant holds offline.

A scripted transport stands in for the HTTP call, so these tests need no key and no network.
What they pin: the private sheet is NEVER placed in the prompt, `consider_option` is resolved by
`sheet.evaluate` in code, and the result handed back to the model is MASKED (`{"acceptable": bool}`
only — no reason, no score, no constraint). That's non-betrayal on the conversational path.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # repo root, so `voice` imports

from voice import brain
from parley.spec import DecisionSpec

RECIPE = "examples/demo/recipe_estate.json"
OWNER = "Heir 2"  # private red line: heir2 >= 30


def _sheet_and_options():
    spec = DecisionSpec.load(RECIPE)
    sheet = next(p for p in spec.parties if p.owner == OWNER).to_sheet()
    return sheet, spec.options


class _Transport:
    """Returns OpenAI-shaped responses in order; records the payload sent each round."""

    def __init__(self, script):
        self._script = script
        self.sent = []

    def __call__(self, payload):
        self.sent.append(payload)
        return self._script[len(self.sent) - 1]


def _tool_call(option, cid="call_1"):
    return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
        {"id": cid, "type": "function", "function": {
            "name": "consider_option", "arguments": json.dumps({"option": option})}}]}}]}


def _final(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def test_brain_never_receives_the_sheet_and_gets_a_masked_result():
    sheet, options = _sheet_and_options()
    # the counterparty proposes heir2=10, which crosses the private red line (heir2 >= 30)
    t = _Transport([
        _tool_call({"heir1": 90, "heir2": 10, "legal_ok": True}),
        _final("That isn't acceptable to me. Please propose a different option."),
    ])
    reply = brain.respond(
        [{"role": "user", "content": "you take 90, I take 10"}],
        sheet, options_hint=options, transport=t,
    )
    assert reply == "That isn't acceptable to me. Please propose a different option."

    # the tool result fed back to the model is masked — acceptable only, nothing else
    second_msgs = t.sent[1]["messages"]
    tool_msgs = [m for m in second_msgs if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert json.loads(tool_msgs[0]["content"]) == {"acceptable": False}  # crossed → false, NOTHING else

    # across every request, the private red line, its score, and the violated-constraint name never
    # reach the model (options_hint carries only public option values, which is fine)
    everything = json.dumps(t.sent)
    assert "heir2 >= 30" not in everything   # the red-line predicate never leaks
    assert "violated" not in everything       # no violated-constraint list
    assert "score" not in everything          # no soft score


def test_brain_accepts_only_after_a_feasible_consider_result():
    sheet, options = _sheet_and_options()
    t = _Transport([
        _tool_call({"heir1": 50, "heir2": 50, "legal_ok": True}),  # clears the red line
        _final("That works for me — I accept."),
    ])
    reply = brain.respond(
        [{"role": "user", "content": "let's split it evenly"}],
        sheet, options_hint=options, transport=t,
    )
    assert reply == "That works for me — I accept."
    tool_msgs = [m for m in t.sent[1]["messages"] if m.get("role") == "tool"]
    assert json.loads(tool_msgs[0]["content"]) == {"acceptable": True}


def test_brain_loop_is_bounded_when_the_model_keeps_calling_the_tool():
    sheet, options = _sheet_and_options()
    stuck = [_tool_call({"heir2": 40}) for _ in range(brain.MAX_TOOL_ROUNDS + 2)]
    t = _Transport(stuck)
    reply = brain.respond([{"role": "user", "content": "hmm"}], sheet, options_hint=options, transport=t)
    assert reply == "I need a moment — could you restate your proposal?"
    assert len(t.sent) == brain.MAX_TOOL_ROUNDS  # stopped at the bound
