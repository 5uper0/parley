// Homepage v3 hero and receipt copy. Source: docs/_drafts/landing-v3-copy-2026-11-16.md
// (Hero Variant A, sections 2, 3.2 and 4), verbatim. New text is a copy change request.

export const hero = {
  headline: "Group choices show your limit, or ignore it.",
  sub: "With Parley, each person's agent says yes or no. The group never sees your limit. Options above it cannot win.",
  primary: "Try the demo",
  secondary: "See how it works",
  // Scene captions for beats 1 and 2: together they say what the frame shows.
  sceneAlt:
    "Ana, Bob and Cara's agents pick a dinner. Each limit stays sealed. Rooftop is over Bob's limit. It cannot win. Nobody sees his number.",
} as const;

export const receipt = {
  fold: "Everyone gets the same receipt. Each owner can check their limit held.",
  title: "Check it yourself",
  body: "The receipt is the same record of every yes and no for everyone, and you replay your own limit against it on your own computer, so nobody else has to see it.",
  label: "Recorded sample run. Not a live result, not real people.",
  caption:
    "This is what the dinner code prints. Rooftop was Ana's favorite and lost: it is over Bob's limit. Each of the three replayed their own limit against the receipt and it held. Run it yourself and you get the same lines.",
} as const;
