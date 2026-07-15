"""What the voice agent is ALLOWED to say — the speech-side of non-betrayal.

The consensus core already masks *why* an option is rejected (`Verdict.reason == "red-line"`,
never the constraint name). Voice reopens that leak: a chatty LLM, asked to sound natural, will
volunteer "I can't do Friday because my owner…". So the agent never generates its own commitments
in words — it may only speak lines drawn from here, chosen by the code from an `Evaluation`.

Three outcomes, nothing else leaves the agent's mouth:
- feasible  -> ACCEPT  (a commitment — only ever reached through the sheet, never persuasion)
- red-line  -> REFUSE  (masked: no reason, no constraint, no score)
- unparsed  -> CLARIFY (fail-closed: when the proposal couldn't be pinned to a concrete option)
"""
from parley.preferences import Evaluation

# Whitelisted lines. Deliberately reason-free: none of these may name a constraint, an
# attribute, or a score. Keep them interchangeable so the code — not the LLM — picks.
ACCEPT = "That works for me — I accept."
REFUSE = "That isn't acceptable to me. Please propose a different option."
CLARIFY = "I didn't catch a concrete proposal — could you state it precisely?"


def reply_for(ev: Evaluation | None) -> str:
    """Map a code-produced Evaluation to a masked, speakable line. `None` == nothing to evaluate."""
    if ev is None:
        return CLARIFY
    return ACCEPT if ev.feasible else REFUSE
