// Homepage hero, explainer stage and receipt copy. Source: docs/_drafts/hero-2d-spec-2026-11-16.md
// (sections 2 and 3, Concept A) and landing-v3-copy-2026-11-16.md (section 2), verbatim.
// New text is a copy change request. Numbers and each yes or no are not here: they come from
// receipt-dinner.ts, which scripts/gen-receipt.py writes from a real run.

export const hero = {
  headline: "Pick together without saying your limit out loud.",
  sub: "Parley lets each person's agent, an AI assistant acting for them, say yes or no. Options over anyone's limit cannot win.",
  primary: "Try the demo",
  secondary: "See how it works",
  installLabel: "For developers",
  installAria: "Install command",
  install: "pip install parley-consensus",
  status: "v0.2.1, early. Open source, Apache-2.0. Not for adversarial use yet.",
} as const;

export const explainer = {
  beat1: { num: "1", step: "Tell", line: "Each person's agent holds their limit, sealed." },
  beat2: { num: "2", step: "Yes or no", line: "Each agent says yes or no to every option." },
  beat3: { num: "3", step: "Check" },
  envelope: (owner: string) => `${owner}'s limit`,
  agent: (owner: string) => `${owner}'s agent`,
  cost: (cost: number) => `costs ${cost}`,
  stamp: "Over Bob's limit",
  tags: {
    blocked: "Cannot win",
    picked: "Picked. Everyone said yes.",
    feasible: "Everyone said yes.",
  },
  yes: "yes",
  no: "no",
  plain: "Rooftop costs 900. That is over Bob's limit, so it cannot win.",
  engine: "The pick is plain code, not a language model.",
  receipt: {
    header: "Receipt: every yes and no",
    line: "Same receipt for all three. Each replays it against their own limit, on their own computer.",
  },
  sampleLabel: "Illustration of a recorded sample run.",
  stageAria:
    "Sample run: Ana, Bob and Cara's agents pick a dinner. Each limit stays sealed. Rooftop costs 900, over Bob's limit, so it cannot win. Garden is picked. All three get the same receipt.",
  replay: "Play again",
} as const;

export const receipt = {
  fold: "Everyone gets the same receipt. Each owner can check their limit held.",
  title: "Check it yourself",
  body: "The receipt is the same record of every yes and no for everyone, and you replay your own limit against it on your own computer, so nobody else has to see it.",
  label: "Recorded sample run. Not a live result, not real people.",
  caption:
    "This is what the dinner code prints. Rooftop was Ana's favorite and lost: it is over Bob's limit. Each of the three replayed their own limit against the receipt and it held. Run it yourself and you get the same lines.",
} as const;
