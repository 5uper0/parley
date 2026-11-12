# DESIGN.md: Parley (landing, demo, proof cards)

Read before changing any page, component or copy. Brand rationale and canonical tokens already exist: `docs/brand/brand.md`, `docs/brand/tokens.css`, `docs/brand/calibration-linear.md`. This file adds the site-level rules and anti-slop gate; it does not replace them. Site code: `landing/src` (Astro; `styles/global.css`, `components/`, `layouts/Layout.astro`). Verified in `landing/src/styles/global.css`. Owner: design-dept; the project session merges.

## 1. Colour (semantic: colour carries product meaning)
| Token | Dark | Light | Meaning |
|---|---|---|---|
| `--bg` / `--surface` | `#0a0b0d` / `#121316` | `#f6f7fb` / `#ffffff` | page / cards |
| `--ink` | `#f4f6f7` | `#12151c` | text |
| `--muted` / `--subtle` | `#99a1b3` / `#6b7383` | `#535a68` / `#6c727f` | secondary / hints |
| `--hairline` | `rgba(255,255,255,.08)` | `#e3e6ef` | borders |
| `--indigo` (`--indigo-text` for small text) | `#6675d3` (`#8e9be1`) | `#3a45b0` | the engine, primary actions |
| `--verify` | `#14a473` | `#0d825a` | signed, proven verdict only |
| `--redline` (`--redline-text`) | `#d93a3a` (`#ec8a8a`) | `#c42121` | a deterministic BLOCK only |
| `--masked` | `#d9971c` | `#996711` | hidden, pending or masked verdict only |

Rules: red, green and amber are semantic. Use red only for a block or the red-line rule, never for decoration. No neon-violet gradient, gold, glow or glass. Small text below 18 px uses the `-text` variants on dark. Any new colour needs a 4.5:1 check.

## 2. Type
- Inter Variable for UI, headings and body. JetBrains Mono for transcripts, hashes, signatures and code only. Display weight `--font-weight-display: 560`, tight tracking on headings.
- Reason: Inter reads as neutral infrastructure; mono is the receipt voice and carries the proof artefact.
- Mono is not a style for headings or labels. No all-mono eyebrow labels, no wide-tracked uppercase section labels (audit item 3).
- Scale `--text-xs` to `--text-6xl` (12 to 60 px) from `tokens.css`; nothing below 12 px.

## 3. Shape and spacing
Use the scale in `tokens.css`; do not invent radii or spacing steps. Hairline borders over shadows. No glow card.

## 4. Components and motifs
- Signature motif: one thin red horizontal rule (`--redline-rule`) for hard constraints and section dividers. Keep it rare.
- Mono receipt block: the transcript with masked verdicts and sha256 earns its place on home. It is real product output, never mocked-up skeleton bars.
- Verified seal: green check, only on an actually signed verdict.
- Tape (`components/Tape*.astro`): shows real data from `data/tape.ts`; do not add rows that are not real runs.
- Focus: `a:focus-visible` 2 px indigo outline; keep it on every interactive element. `prefers-reduced-motion` already collapses transitions; keep it.
- Cards differ when content differs; merge the three property cards if they repeat the three steps (audit item 8).

## 5. Imagery
Product output only: real transcripts, proof cards, verification pages. No stock illustrations, 3D blobs, robot or sparkle symbols, no AI-generated faces. Proof cards and OG images are built from `docs/brand/*.html` templates.

## 6. Anti-slop rules (design-dept gate, WI-261105-056)
Blockers:
1. No claim that someone uses Parley in a setting where nobody does (KYC/AML, enterprise negotiation, inheritance). Scenarios on `/demo` are labelled sample runs.
2. "Real decision" never describes scripted engine runs. Say "sample decision".
3. No invented number or testimonial. State the version (v0.2.0) and that it is early where the page makes capability claims.
4. The page never contradicts itself (what is verified, what is private, what the coordinator sees).
5. Product shown working or plainly labelled as not live.
Copy and layout:
6. CTAs name the action: "Open the demo", "Read the 3 steps". One arrow style at most; no arrow on every CTA.
7. No formula headlines ("Not X, not Y", "Prove it never sold you out") beyond one deliberate line. No em dashes in headings or CTAs.
8. No eyebrow pill above the H1 repeating the headline.
9. Three numbered steps are allowed here because the process has three steps (tell, ok or no, check).
10. Real 390 px check before merge, including the transcript card and the tape: no horizontal scroll.
11. Contrast 4.5:1 for all small text on dark, focus visible, reduced motion respected.

## 7. Copy
Plain, exact, limits first: say what the product does not give you. Languages en, es, uk change together; keep each claim identical. Run the global `anti-slop` skill on every UI or copy change; a FAIL on a blocker item stops the PR. For prose also run `stop-slop` (global `~/.claude/skills/stop-slop/`).

## 8. Review
New or changed hero, proof card, OG card, logo or media template goes to design-dept (`wi.py new --owner design-dept`). Routine guide posts from an approved template skip it.
