// Homepage hero, explainer stage and receipt copy. Each line is owner-approved through copy
// change requests; new text needs one too. Costs, each yes or no, the names in the tie clause and
// in the screen-reader summary, and the parley version in the status line are not typed here: they come from
// receipt-dinner.ts, which scripts/gen-receipt.py writes from a real run.

export const hero = {
  headline: "Pick together without saying your limit out loud.",
  sub: "Parley lets each person's agent, software acting for them, say yes or no. Options over anyone's limit cannot win.",
  useCase: "For developers building agents that act for different people.",
  primary: "Try the demo",
  secondary: "See how it works",
  installLabel: "For developers",
  installAria: "Install command",
  install: "pip install parley-consensus",
  status: (version: string) => `v${version}, early. Open source, Apache-2.0. Not for adversarial use yet.`,
} as const;

export const explainer = {
  beat1: { num: "1", step: "Tell", line: "Each person's agent holds a private sheet of wishes and limits, sealed." },
  beat2: { num: "2", step: "Yes or no", line: "Each agent says yes or no to every option." },
  beat3: { num: "3", step: "Check" },
  envelope: (owner: string) => `${owner}'s sheet`,
  agent: (owner: string) => `${owner}'s agent`,
  cost: (cost: number) => `costs ${cost}`,
  stamp: "Bob said no",
  tags: {
    blocked: "Cannot win",
    picked: "Picked",
    feasible: "Not picked",
  },
  yes: "yes",
  no: "no",
  plain: "Rooftop costs 900. Bob's agent says no, so it cannot win.",
  rule: "Rule: the option best for the least-happy owner wins.",
  tie: (picked: string, other: string) =>
    `${picked} and ${other} suit that owner equally, so the higher total wins: ${picked}.`,
  reveal: "The group sees yes or no and a score, never the limit itself. Many yeses and noes can still narrow it down.",
  engine: "The pick is plain code, not a language model.",
  receipt: {
    header: "Receipt: every yes and no",
    line: "Each owner checks the pick against their own sheet, on their own computer. Compare the sha256 to confirm it is the same receipt.",
  },
  sampleLabel: "Illustration of a recorded sample run.",
  stageAria: (owners: string, plain: string, picked: string) =>
    `Sample run: ${owners}'s agents pick a dinner. Each sheet stays sealed. ${plain} ${picked} is picked. Each owner checks the pick against their own sheet.`,
  replay: "Play again",
} as const;

export const receipt = {
  fold: "Each owner checks the pick against their own sheet, on their own computer.",
  title: "Check it yourself",
  body: "Compare the sha256 to confirm it is the same receipt.",
  label: "Recorded sample run. Not a live result, not real people.",
  caption:
    "This is what the dinner code prints. Rooftop was Ana's favorite and lost: Bob's agent said no. Each owner checks the pick against their own sheet, on their own computer. Run it yourself and you get the same lines.",
} as const;
