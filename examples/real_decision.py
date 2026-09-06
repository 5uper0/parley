"""Run a real decision, end to end, with real people at one keyboard.

This is the Exp 1 flow: several people with genuinely conflicting interests each state their
own position privately, the engine picks an option, and each person then verifies *for
themselves* that no red line of theirs was crossed before accepting. Nothing here is a
simulation — the sheets are the participants' own, and the receipt at the end is the real
record.

Why it is shaped this way:

- **Options are agreed in public, positions in private.** The option set is the one thing
  everyone must see identically, so it is loaded from a file that all parties look at
  together. Preferences never leave their owner.
- **Pass-the-keyboard, one person at a time.** Between participants the screen is cleared and
  the next person is prompted by name. A participant's answers, their draft sheet and their
  red lines are never printed while somebody else is at the keyboard. This is the whole point:
  if the tool leaked positions, the guarantee it claims would be theatre.
- **Nothing is inferred.** Natural-language answers go through `parley.elicit`, which can only
  *propose* declarative items; every hard constraint has to be confirmed by the participant,
  by id, against the exact sheet version. An extractor that misreads someone produces a
  question, never a silent red line.
- **Ratification is local and refusable.** After the engine decides, each participant replays
  the decision against their own sheet (`parley.ratify`) and answers accept or decline. The
  code refuses an accept that the person's own sheet rejects, so "I agreed" can never mean
  "I did not look".
- **The receipt proves two different things.** `agreement()` proves everyone accepted this
  exact record; `verify_outcome()` proves the coordinator actually ran max-min rather than
  finalizing some other feasible option. Neither implies the other, so both are printed.
- **The receipt is checkable by someone who was not in the room.** It carries the full
  masked transcript, the participant list and every acceptance, so `scripts/verify-receipt.py`
  can re-derive the hash, the max-min outcome and each acceptance's binding from the file
  alone. When the `crypto` extra is installed each acceptance is also signed with a fresh
  Ed25519 key generated for that participant at the keyboard; the public key is shown to
  them so they can recognise it later. Those keys are ephemeral and self-attested, so a
  signature proves the acceptance was not altered after it was given, not who gave it
  (SECURITY.md). Without the extra the flow runs unchanged and acceptances are unsigned.

Usage:

    .venv/bin/python examples/real_decision.py --options examples/demo/recipe_committee.json
    .venv/bin/python examples/real_decision.py --options my_case.json --receipt receipt.json
    .venv/bin/python scripts/verify-receipt.py receipt.json

Elicitation needs a model. Set `PARLEY_API_KEY` (OpenRouter, per `parley.elicit.http_elicitor`)
to answer in your own words. Without a key the script runs in `--manual` mode, where each
person types their constraints directly in a small structured form. Manual mode is the honest
fallback: rather than have a keyword heuristic guess what someone meant, it makes them say it.

Zero-dependency: stdlib only, like the rest of the core.
"""
import argparse
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from parley.consensus import verify_outcome  # noqa: E402
from parley.elicit import PROMPTS, Elicitation, ElicitError, http_elicitor  # noqa: E402
from parley.ratify import agreement, ratify  # noqa: E402
from parley.spec import Constraint, DecisionSpec, PartySpec, UtilityTerm  # noqa: E402

CLEAR = "\n" * 40  # crude on purpose: works over ssh and in a scrollback-free terminal

# Mirrors Constraint.check exactly. Kept here so a typo is caught while the person is still
# at the keyboard, instead of raising from inside the parley.
_OPS = ("==", "!=", "<", "<=", ">", ">=", "in", "not_in")


def _default_io():
    def ask(prompt: str) -> str:
        return input(prompt)

    def say(text: str = "") -> None:
        print(text)

    return ask, say


def load_options(path: str) -> tuple:
    """Read the shared option set. Accepts a bare list or a recipe with 'title'/'options'."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return "Untitled decision", data
    if not isinstance(data, dict):
        raise ValueError("options file must be a JSON list or object")
    options = data.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError("options file has no non-empty 'options' list")
    if not all(isinstance(o, dict) for o in options):
        raise ValueError("every option must be a JSON object of attributes")
    return str(data.get("title") or "Untitled decision"), options


def show_options(say, title: str, options: list) -> None:
    say(f"Decision: {title}")
    say("Everyone is choosing between exactly these options:")
    for i, option in enumerate(options, 1):
        attrs = ", ".join(f"{k}={v!r}" for k, v in sorted(option.items()))
        say(f"  {i}. {attrs}")
    say()


def _attr_names(options: list) -> list:
    names = set()
    for option in options:
        names.update(option.keys())
    return sorted(names)


def manual_position(ask, say, owner: str, options: list) -> PartySpec:
    """Structured entry: the participant states constraints directly, nothing is interpreted."""
    attrs = _attr_names(options)
    say(f"Attributes you can talk about: {', '.join(attrs)}")
    say("Operators: == != < <= > >= in not_in")
    say()
    hard, utility = [], []

    say("RED LINES. Options that break one of these can never win, for anyone.")
    say("Enter one per line as: attribute operator value   (blank line to finish)")
    while True:
        raw = ask("  red line > ").strip()
        if not raw:
            break
        parts = raw.split(None, 2)
        if len(parts) != 3:
            say("  need three parts, for example: price <= 500")
            continue
        attr, op, value = parts
        if op not in _OPS:
            # Constraint defers operator validation to check time, which would surface as a
            # crash mid-parley rather than here, where the person can retype it.
            say(f"  unknown operator {op!r}; use one of {' '.join(sorted(_OPS))}")
            continue
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        hard.append(Constraint(attr=attr, op=op, value=parsed))

    say()
    say("PREFERENCES. These only rank the options that already clear everyone's red lines.")
    say("Enter one per line as: attribute value weight   (blank line to finish)")
    while True:
        raw = ask("  prefer > ").strip()
        if not raw:
            break
        parts = raw.split()
        if len(parts) != 3:
            say("  need three parts, for example: day Tuesday 2")
            continue
        attr, want, weight = parts
        try:
            value = json.loads(want)
        except json.JSONDecodeError:
            value = want
        try:
            utility.append(UtilityTerm(attr=attr, weight=float(weight), prefer=value))
        except Exception as exc:
            say(f"  rejected: {exc}")

    return PartySpec(owner=owner, hard=hard, utility=utility)


def elicited_position(ask, say, service: Elicitation, case_id: str, owner: str) -> PartySpec:
    """Natural-language entry through parley.elicit, with explicit per-item confirmation."""
    interview = service.start_interview(case_id, owner)
    say("Answer in your own words. Press enter to skip a question.")
    say()
    for prompt_id, question in PROMPTS:
        answer = ask(f"  {question}\n  > ").strip()
        if answer:
            service.answer(interview.interview_id, prompt_id, answer)
        say()

    draft = service.draft_sheet(interview.interview_id)
    while draft.needs_clarification:
        say("Some answers were not clear enough to become a rule. Please answer these:")
        for question in draft.needs_clarification:
            reply = ask(f"  {question.question}\n  > ").strip()
            if reply:
                service.answer(interview.interview_id, question.source_prompt_id
                               or PROMPTS[0][0], reply)
        draft = service.draft_sheet(interview.interview_id)

    say()
    say(draft.review())
    say()
    say("Nothing becomes binding until you confirm every red line above, by id.")
    ids = [item.item_id for item in draft.hard]
    if ids:
        say(f"Type 'yes' to confirm all of {', '.join(ids)}, anything else to start over.")
        if ask("  > ").strip().lower() not in ("y", "yes"):
            raise ElicitError("participant declined the draft")
    sheet = service.confirm_sheet(draft.draft_id, {
        "participant_id": owner,
        "token": draft.token,
        "confirm_hard": ids,
        "confirm_version": draft.version,
    })
    return sheet.to_party_spec()


def collect_positions(ask, say, names: list, options: list, service, case_id: str,
                      manual: bool) -> list:
    parties = []
    for owner in names:
        say(CLEAR)
        say(f"--- {owner}, it is your turn. Nobody else should be looking. ---")
        say()
        show_options(say, "The options on the table", options)
        if manual:
            parties.append(manual_position(ask, say, owner, options))
        else:
            parties.append(elicited_position(ask, say, service, case_id, owner))
        say()
        say(f"Recorded. {owner}, hand the keyboard on. Your position stays private.")
        ask("  press enter ")
    say(CLEAR)
    return parties


def default_signers(names: list) -> dict:
    """One fresh Ed25519 signer per participant when the `crypto` extra is installed.

    Off by default, and the reason is worth stating. These keys are generated by the same
    process that runs the coordinator and writes the receipt, so a signature here proves the
    acceptance was not altered afterwards, and proves nothing at all about who accepted: the
    writer held every private key. A reader who sees "signature verified" will tend to read
    authentication into it. Until there is an owner-to-key roster (SECURITY.md), an unsigned
    receipt is the more honest artifact, and it is also the one that verifies on a machine
    without pynacl. `--sign` turns this on for the case where that trade is understood.

    Without pynacl this returns nothing and the unsigned flow runs unchanged: the core never
    imports crypto, so the import is attempted here, at the edge, and only by name."""
    try:
        identity = importlib.import_module("parley.net.identity")
    except ImportError:
        return {}
    return {name: identity.Identity.generate(name).sign_acceptance for name in names}


def collect_ratifications(ask, say, parties: list, result, signers: dict = None) -> list:
    """Each owner replays the decision against their own sheet, then accepts or declines."""
    acceptances = []
    signers = signers or {}
    for party in parties:
        say(CLEAR)
        say(f"--- {party.owner}, review the outcome privately. ---")
        say()
        say(f"Decision: {json.dumps(result.decision, sort_keys=True, ensure_ascii=False)}")
        say(f"Record hash: {result.transcript.hash()}")
        say()
        sheet = party.to_sheet()
        evaluation = sheet.evaluate(result.decision)
        if evaluation.feasible:
            say("Replayed against your own sheet: no red line of yours was crossed.")
        else:
            say("Replayed against your own sheet: this decision CROSSES a red line of yours.")
            say(f"  crossed: {', '.join(evaluation.violated)}")
            say("  (only you can see this line)")
        say()
        answer = ask("Do you accept this outcome? yes / no > ").strip().lower()
        accept = answer in ("y", "yes")
        signer = signers.get(party.owner)
        try:
            acceptance = ratify(sheet, result.transcript, accept=accept, signer=signer)
        except Exception as exc:
            say(f"Refused: {exc}")
            acceptance = ratify(sheet, result.transcript, accept=False, signer=signer)
        acceptances.append(acceptance)
        if acceptance.pubkey_hex:
            say(f"Your answer is signed. Public key: {acceptance.pubkey_hex}")
            say("  (keep it: this is how you recognise your own acceptance in the receipt)")
        ask("  press enter ")
    say(CLEAR)
    return acceptances


def receipt(title: str, result, acceptances: list, participants: set) -> dict:
    unanimous = agreement(result.transcript, acceptances, participants=participants)
    return {
        "title": title,
        "status": result.status,
        "decision": result.decision,
        "transcript_hash": result.transcript.hash(),
        "max_min_verified": verify_outcome(result.transcript),
        "unanimous_acceptance": unanimous,
        "participants": sorted(participants),
        "acceptances": [a.to_dict() for a in acceptances],
        "transcript": result.transcript.to_dict(),
    }


def report(say, data: dict) -> None:
    say("=" * 66)
    say(f"  {data['title']}")
    say("=" * 66)
    if data["status"] == "deadlock":
        say("DEADLOCK. No option cleared every participant's red lines.")
        say("This is an honest outcome, not a failure: forcing an agreement that crosses")
        say("somebody's red line is exactly what this tool exists to prevent.")
    else:
        say(f"Decision: {json.dumps(data['decision'], sort_keys=True, ensure_ascii=False)}")
    say()
    say(f"Record hash          {data['transcript_hash']}")
    say(f"Max-min honest       {'yes' if data['max_min_verified'] else 'NO'}"
        "   (the announced option really is the max-min one)")
    say(f"Unanimously accepted {'yes' if data['unanimous_acceptance'] else 'no'}"
        "   (every participant accepted this exact record)")
    say()
    for entry in data["acceptances"]:
        mark = "accepted" if entry["accepted"] else "declined"
        say(f"  {entry['owner']:<16} {mark}")
    say()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a real decision with real people.")
    parser.add_argument("--options", required=True,
                        help="JSON file with the shared option set (a list, or {title, options})")
    parser.add_argument("--participants", default="",
                        help="comma-separated names; asked interactively when omitted")
    parser.add_argument("--manual", action="store_true",
                        help="type constraints directly instead of answering in your own words")
    parser.add_argument("--sign", action="store_true",
                        help="sign each acceptance with a fresh per-participant key; the keys are "
                             "generated by this process, so signatures prove the file was not "
                             "altered, never who accepted, and the receipt then needs "
                             "parley[crypto] to verify")
    parser.add_argument("--receipt", default="",
                        help="write the full receipt to this path as JSON")
    args = parser.parse_args(argv)

    ask, say = _default_io()
    title, options = load_options(args.options)

    names = [n.strip() for n in args.participants.split(",") if n.strip()]
    if not names:
        say("Who is taking part? Comma-separated names, at least two.")
        names = [n.strip() for n in ask("  > ").split(",") if n.strip()]
    if len(names) < 2:
        say("A parley needs at least two parties with something to disagree about.")
        return 2
    if len(set(names)) != len(names):
        say("Names must be distinct — every acceptance is bound to one owner.")
        return 2

    manual = args.manual or not os.environ.get("PARLEY_API_KEY")
    service = None
    if not manual:
        service = Elicitation(http_elicitor())
    else:
        say("Running in manual mode: no model is involved, you state your own constraints.")
        say()

    show_options(say, title, options)
    ask("Everyone happy that these are the options? press enter ")

    parties = collect_positions(ask, say, names, options, service, title, manual)
    result = DecisionSpec(title=title, options=options, parties=parties).run()

    if result.status == "deadlock":
        data = receipt(title, result, [], set(names))
        report(say, data)
    else:
        signers = default_signers(names) if args.sign else {}
        if signers:
            say("Acceptances will be signed with a fresh key per participant.")
            say("Those keys are made here, so a signature shows the file was not altered later.")
            say("It does not show who accepted, and the receipt will need parley[crypto] to check.")
        elif args.sign:
            say("--sign asked for signatures but pynacl is missing; running unsigned.")
            say("Install parley[crypto] to sign.")
        else:
            say("Acceptances will be unsigned: tamper-evident, and checkable on any machine.")
        acceptances = collect_ratifications(ask, say, parties, result, signers=signers)
        data = receipt(title, result, acceptances, set(names))
        report(say, data)

    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True, ensure_ascii=False)
        say(f"Receipt written to {args.receipt}")
        say("Each participant can re-check it later against their own sheet.")
        say(f"Anyone can check the record itself: scripts/verify-receipt.py {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
