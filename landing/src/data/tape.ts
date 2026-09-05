/* GENERATED FILE — do not edit by hand. Regenerate with:
 *
 *   .venv/bin/python landing/scripts/gen-tape.py
 *
 * The Receipt Tape dataset, replayed from a REAL parley run: five owners
 * (ana, bob, cara, dan, eve) with private red lines, 16 proposals, decided by
 * the real engine (`parley.consensus.run_consensus`). Nothing here is typed
 * in — every verdict, every max-min pick and every digest is read off the
 * `Transcript` the engine produced.
 *
 * Each `sha256` line is `Transcript.hash()` taken right after that round's
 * `record()` (result still unset); the closing one is the hash after
 * `finalize()`. Shown as the first and last 8 hex chars of the full digest.
 *
 * Final transcript sha256 (full):
 *   af17022948781afc35c539506007b86ad7256dc05596123df6b805c4b7a84127
 * Decision: option P (thu 14:00), status "agreed",
 * red lines held for 5/5 owners on replay (`verify_non_betrayal`).
 *
 * Agenda (option → slot):
 *   A = mon 09:00
 *   B = tue 14:00
 *   C = wed 11:00
 *   D = thu 15:00
 *   E = fri 15:00
 *   F = tue 17:00
 *   G = wed 14:00
 *   H = thu 13:00
 *   I = mon 15:00
 *   J = tue 15:00
 *   K = wed 16:00
 *   L = thu 10:00
 *   M = wed 15:00
 *   N = tue 13:00
 *   O = fri 14:00
 *   P = thu 14:00
 *
 * Color semantics map 1:1 to the product: redline = deterministic BLOCK,
 * muted = ok, indigo = max-min pick, dim = bookkeeping, verify = the owners'
 * ✓, masked = a round still in progress (not yet resolved).
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

/** The full run: 16 rounds, owners ana, bob, cara, dan, eve, then the tape wraps. */
export const tapeLines: TapeLine[] = [
  { text: "round 1 · option A proposed", color: "dim" },
  { text: "ana → verdict: red-line", color: "redline" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: red-line", color: "redline" },
  { text: "eve → verdict: red-line", color: "redline" },
  { text: "option A infeasible", color: "dim" },
  { text: "round 2 · option B proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option B", color: "indigo" },
  { text: "sha256 4439886f…056819a5", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 3 · option C proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: red-line", color: "redline" },
  { text: "option C infeasible", color: "dim" },
  { text: "round 4 · option D proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 7156928e…63896afd", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 5 · option E proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: red-line", color: "redline" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "option E infeasible", color: "dim" },
  { text: "round 6 · option F proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: red-line", color: "redline" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "option F infeasible", color: "dim" },
  { text: "round 7 · option G proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 29165341…330c052a", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 8 · option H proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 c89c4405…3c2a210e", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 9 · option I proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: red-line", color: "redline" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "option I infeasible", color: "dim" },
  { text: "round 10 · option J proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 24adc5c4…feac212e", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 11 · option K proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 7676e636…d6d9b1fd", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 12 · option L proposed", color: "dim" },
  { text: "ana → verdict: red-line", color: "redline" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: red-line", color: "redline" },
  { text: "option L infeasible", color: "dim" },
  { text: "round 13 · option M proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 e5a4f15f…f0c8564e", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 14 · option N proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option D", color: "indigo" },
  { text: "sha256 9f328fa4…245d4b4b", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 15 · option O proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: red-line", color: "redline" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "option O infeasible", color: "dim" },
  { text: "round 16 · option P proposed", color: "dim" },
  { text: "ana → verdict: ok", color: "muted" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "cara → verdict: ok", color: "muted" },
  { text: "dan → verdict: ok", color: "muted" },
  { text: "eve → verdict: ok", color: "muted" },
  { text: "max-min so far → option P", color: "indigo" },
  { text: "sha256 d24a3e6a…a7c7b5fc", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "max-min → option P · agreed", color: "indigo" },
  { text: "sha256 af170229…b7a84127", color: "dim" },
  { text: "✓ verified by 5/5 owners", color: "verify" },
  { text: "round 1 · option A proposed", color: "dim" },
  { text: "ana → verdict: red-line", color: "redline" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "awaiting cara, dan, eve…", color: "masked" },
];

/** Compact excerpt for the mobile Proof card — one line of every color. */
export const tapeSnippet: TapeLine[] = [
  { text: "round 1 · option A proposed", color: "dim" },
  { text: "ana → verdict: red-line", color: "redline" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "option A infeasible", color: "dim" },
  { text: "round 2 · option B proposed", color: "dim" },
  { text: "bob → verdict: ok", color: "muted" },
  { text: "max-min so far → option B", color: "indigo" },
  { text: "sha256 4439886f…056819a5", color: "dim" },
  { text: "✓ red lines hold for 5/5 owners", color: "verify" },
  { text: "round 3 · option C proposed", color: "dim" },
  { text: "awaiting bob, cara…", color: "masked" },
];
