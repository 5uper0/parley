/* The Receipt Tape dataset — a synthetic but structurally faithful parley
 * transcript. Color semantics map 1:1 to the product: redline = deterministic
 * BLOCK, muted = ok, indigo = max-min pick, dim = bookkeeping, verify = the
 * owners' ✓, masked = a round still in progress (not yet resolved).
 *
 * NOTE: `Verdict.reason` on the wire is only ever "ok" | "red-line"
 * (parley/agent.py) — "masked" describes the PROPERTY that a reason never
 * names the constraint, it is never itself a verdict value. Don't add a
 * third literal verdict here; that would misrepresent the real product on
 * the one page whose whole pitch is "provable, not hoped". */

export type TapeColor = "dim" | "muted" | "redline" | "indigo" | "verify" | "masked";

export interface TapeLine {
  text: string;
  color: TapeColor;
}

/** Tape color → Tailwind text utility (semantic tokens from global.css).
 * All tape text is <18px, so every color here must clear WCAG AA's 4.5:1
 * for small text — redline/indigo use the lightened -text variants
 * (redline-300/indigo-300 primitives) since the base brand tones are
 * 4.33:1/4.47:1 on the tape's surface bg, just under the bar. `dim` uses
 * `muted` rather than `subtle` for the same reason (subtle is 3.90:1 here). */
export const tapeColorClass: Record<TapeColor, string> = {
  dim: "text-muted",
  muted: "text-muted",
  redline: "text-redline-text",
  masked: "text-masked",
  indigo: "text-indigo-text",
  verify: "text-verify",
};

type Verdict = "ok" | "red-line";

interface Round {
  option: string;
  verdicts: [owner: string, verdict: Verdict][];
  /** Present when the option is feasible for everyone and wins the max-min pick. */
  hash?: string;
}

const ok = (...owners: string[]): [string, Verdict][] =>
  owners.map((o) => [o, "ok"] as [string, Verdict]);

const H = [
  "c77b01aa…12ef98c4",
  "0d84fe23…a9b160cc",
  "7e3a99d0…4c218fb7",
  "41c9e2f7…88ab10d3",
  "9f02ac11…b3d47e90",
  "f16d20b8…903aa7e1",
];

const rounds: Round[] = [
  { option: "A", verdicts: [...ok("ana", "bob"), ["cara", "red-line"], ...ok("dan")] },
  { option: "B", verdicts: ok("ana", "bob", "cara", "dan", "eve"), hash: H[0] },
  { option: "C", verdicts: ok("ana", "bob", "cara"), hash: H[1] },
  { option: "D", verdicts: ok("ana", "bob", "cara", "dan"), hash: H[2] },
  { option: "E", verdicts: [...ok("ana"), ["bob", "red-line"], ...ok("cara", "dan", "eve")] },
  { option: "F", verdicts: ok("ana", "bob", "cara"), hash: H[3] },
  { option: "G", verdicts: ok("ana", "bob", "cara", "dan"), hash: H[4] },
  { option: "H", verdicts: ok("ana", "bob", "cara", "dan", "eve"), hash: H[0] },
  { option: "I", verdicts: [...ok("ana"), ["bob", "red-line"], ...ok("cara")] },
  { option: "J", verdicts: ok("ana", "bob", "cara", "dan"), hash: H[2] },
  { option: "K", verdicts: ok("ana", "bob", "cara", "dan", "eve"), hash: H[5] },
  { option: "L", verdicts: ok("ana", "bob", "cara"), hash: H[3] },
  { option: "M", verdicts: [...ok("ana", "bob"), ["cara", "red-line"], ...ok("dan")] },
  { option: "N", verdicts: ok("ana", "bob", "cara", "dan", "eve"), hash: H[0] },
  { option: "O", verdicts: ok("ana", "bob", "cara"), hash: H[1] },
  { option: "P", verdicts: ok("ana", "bob", "cara", "dan"), hash: H[2] },
];

const verdictColor: Record<Verdict, TapeColor> = {
  ok: "muted",
  "red-line": "redline",
};

function expand(round: Round, index: number): TapeLine[] {
  const lines: TapeLine[] = [
    { text: `round ${index + 1} · option ${round.option} proposed`, color: "dim" },
    ...round.verdicts.map(
      ([owner, verdict]): TapeLine => ({
        text: `${owner} → verdict: ${verdict}`,
        color: verdictColor[verdict],
      }),
    ),
  ];
  if (round.hash) {
    const n = round.verdicts.length;
    lines.push(
      { text: `max-min → option ${round.option}`, color: "indigo" },
      { text: `sha256 ${round.hash}`, color: "dim" },
      { text: `✓ verified by ${n}/${n} owners`, color: "verify" },
    );
  } else {
    lines.push({ text: `option ${round.option} infeasible`, color: "dim" });
  }
  return lines;
}

export const tapeLines: TapeLine[] = [
  ...rounds.flatMap(expand),
  { text: "round 17 · option Q proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "awaiting cara, dan…", color: "masked" },
];

/** Compact excerpt for the mobile Proof card — one line of every color. */
export const tapeSnippet: TapeLine[] = [
  { text: "round 1 · option A proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "cara → verdict: red-line", color: "redline" },
  { text: "option A infeasible", color: "dim" },
  { text: "round 2 · option B proposed", color: "dim" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "max-min → option B", color: "indigo" },
  { text: `sha256 ${H[0]}`, color: "dim" },
  { text: "✓ verified by 3/3 owners", color: "verify" },
  { text: "round 3 · option C proposed", color: "dim" },
  { text: "awaiting bob, cara…", color: "masked" },
];
