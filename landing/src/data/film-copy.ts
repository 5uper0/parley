// Approved copy for /film/, verbatim. Change text only through the copy change-control process.

export const DEMO_URL = "/demo/";
export const REPO_URL = "https://github.com/5uper0/parley";
export const README_URL = "https://github.com/5uper0/parley#readme";

export interface MenuItem {
  label: string;
  href: string;
  external?: boolean;
}

export const menu: MenuItem[] = [
  { label: "Demo", href: DEMO_URL },
  { label: "How it works", href: "#how" },
  { label: "Install", href: "#install" },
  { label: "Docs", href: "#docs" },
  { label: "GitHub", href: REPO_URL, external: true },
  { label: "Status", href: "#status" },
];

export const menuButton = "Menu";

export const hero = {
  headline: "Agents decide together. No red line crossed.",
  sub: "An open-source Python library: red lines are code, the group never sees your limit, every owner checks the receipt.",
  button: "Try the demo",
  captions: [
    "Three agents. Three owners. Each has a limit it keeps private.",
    "The favorite crosses Bob's limit. It cannot win.",
    "Garden. Every owner can check the receipt.",
  ],
} as const;

export interface Step {
  id: string;
  label: string;
  body: string;
}

export const howItWorks: { title: string; steps: Step[] } = {
  title: "How it works",
  steps: [
    {
      id: "how-1",
      label: "Tell.",
      body: "Each owner gives their own agent what they like and a hard limit. Limits stay private.",
    },
    {
      id: "how-2",
      label: "Yes or no.",
      body: "Every agent answers yes or no to each option. An option that crosses a limit cannot win. The group sees the yes or no, never the limit (a soft score is shared). Among the options nobody blocks, it picks the one that helps the least-happy owner most; ties go to the higher total score. No language model decides: the check is plain code.",
    },
    {
      id: "how-3",
      label: "Check.",
      body: "The group gets one pick and a receipt. Each owner replays their own sheet against it, on their own computer.",
    },
  ],
};

export type Segment = { text: string; code?: boolean };

export const codeSample: {
  title: string;
  titleNote: string;
  intro: Segment[];
  code: string;
  readmeLabel: string;
  readmeLinkText: string;
} = {
  title: "The dinner in code",
  titleNote: "(runs as printed)",
  intro: [
    { text: "Save as " },
    { text: "dinner.py", code: true },
    { text: ". Put one number in a file named " },
    { text: "bob_limit.txt", code: true },
    { text: " (any number from 600 to 899 gives the output below). Run: " },
    { text: "python dinner.py", code: true },
  ],
  code: `from parley.agent import Agent
from parley.consensus import run_consensus
from parley.preferences import HardConstraint, PreferenceSheet

options = [{"venue": "rooftop", "cost": 900}, {"venue": "garden", "cost": 600}, {"venue": "diner", "cost": 300}]
limit = int(open("bob_limit.txt").read())  # Bob's private number, stays in his own file
ana = PreferenceSheet("Ana", utility=lambda o: 1.0 if o["venue"] == "rooftop" else 0.4)
bob = PreferenceSheet("Bob", hard=[HardConstraint("budget", lambda o: o["cost"] <= limit)],  # a red line: code, not a preference
                      utility=lambda o: 1 - o["cost"] / 1000)
cara = PreferenceSheet("Cara", utility=lambda o: 0.9 if o["venue"] == "garden" else 0.5)

result = run_consensus([Agent(s.owner, s) for s in (ana, bob, cara)], options)
print(result.status, result.decision)    # agreed {'venue': 'garden', 'cost': 600}`,
  readmeLabel: "Full README example: ",
  readmeLinkText: "github.com/5uper0/parley#readme",
};

export const receipt = {
  title: "The receipt",
  body: "Everyone gets the same receipt. Each owner checks that their own limit was respected, nothing more.",
  button: "Try the demo",
} as const;

export const install = {
  title: "Install",
  command: "pip install parley-consensus",
  rest: ". Python 3.10 or newer. The core has no dependencies. Apache-2.0.",
} as const;

export const docs = {
  title: "Docs and GitHub",
  body: "README, roadmap, changelog and security notes are in the repository: ",
  linkText: "github.com/5uper0/parley",
  tail: ".",
} as const;

export const status = {
  title: "Status",
  lines: [
    "Early stage, v0.2.1.",
    "Open source.",
    "0 outside users.",
    "Not built for owners who try to cheat.",
    "When no option fits everyone, it reports an honest deadlock, not a forced pick.",
  ],
} as const;
