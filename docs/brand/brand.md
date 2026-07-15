# Parley — brand & visual identity

*The mini-brandbook. Tokens are in [`tokens.css`](tokens.css) (canonical); this doc is the rationale
and usage. Every artifact (product demo, landing, pitch, social) consumes these tokens so we never
re-decide "how it looks" per artifact. `design-system` is the steward — changes go through it.
Established 2026-07-08.*

## What Parley feels like
**Trustworthy · precise · neutral · provable.** A serious piece of infrastructure — the neutral
referee in the room, not a player. Deliberately **not** playful, and pointedly **not** crypto-flashy
(no neon-violet gradients, no gold, no glow). The aesthetic of an audited ledger and a signed receipt:
quiet confidence, exactness, nothing decorative that isn't also meaningful.

## The signal colors map 1:1 to the product
This is the core idea — color carries product meaning, not decoration:

| Color | Token | Product meaning |
|---|---|---|
| **Parley indigo** `#3A45B0` | `--color-primary` | The neutral engine / the referee. Brand, primary actions, the "winner" bar. |
| **Verify green** `#0E8F63` | `--color-verify` | A signed, proven verdict — the receipt ✓. Used for verification, the lifted "floor". |
| **Red-line red** `#C42121` | `--color-redline` | A deterministic BLOCK. A crossed red line. **Deliberate, never decorative.** |
| **Masked amber** `#B87C15` | `--color-masked` | A hidden / pending / masked verdict (what the coordinator can't see yet). |
| **Cool slate** neutrals | `--neutral-*` | Surfaces, text, borders. The quiet ground everything sits on. |

Rule: reach for the **semantic/component** tokens in code (`--color-primary`, `--verdict-block-fg`),
never the raw primitives. Red and amber are *semantic* — if you're using red for anything but a
red-line/block, stop.

## Signature motif — "the red line"
A single thin red horizontal rule (`--redline-rule`) is the recurring graphic device: section
dividers, the line a blocked option crosses, the underline under a hard constraint. It's the one
place the serious red appears outside a BLOCK state — because it *is* the red line. Pair it with the
**mono receipt** blocks (transcript, hashes, signatures) and the **green ✓ seal** for verified.

## Typography
- **UI / headings / body: Inter** — neutral, ubiquitous, high-legibility; the "invisible, trustworthy
  infra" typeface. Open-source (fits the OSS ethos).
- **Transcript / hashes / signatures / code: JetBrains Mono** — the ledger/receipt voice; load-bearing
  for the proof artifact. Open-source.
- Scale: `--text-xs … --text-6xl` (12→60px). Display uses `--tracking-tight`; mono stays normal.
- Weights: 400 body, 500 UI labels, 600 headings, 700 display. Avoid ultra-thin (reads fragile).
- *Self-host note:* the shipped demo vendors/inlines fonts (no external CDN) to keep `docker run`
  dependency-free; the CDN is fine for pitch Artifacts.

## Spacing, radius, elevation, motion
- **Spacing:** 4px base (`--space-*`). Generous whitespace — infra reads calm, not dense.
- **Radius:** moderate (`--radius-md` 8px / `--radius-lg` 12px). Not pill-heavy; precision over softness.
- **Elevation:** subtle, cool-tinted shadows (`--shadow-sm/md/lg`). Depth by hairline borders first, shadow second.
- **Motion:** fast and precise (`--dur-fast/base`, `--ease-out`). Nothing bouncy; a referee is exact.

## Logo / mark direction (to explore, not yet locked)
- **Wordmark:** `parley` — lowercase, Inter medium, `--tracking-tight`. Approachable-but-serious.
  Nod to the word's origin (a *parley* = a flag of truce to negotiate).
- **Mark concept (candidate):** N short marks converging on a single horizontal line, with a small
  ✓ seal — "several parties → one agreed, verified line." The horizontal line *is* the red-line motif.
- **Favicon / emoji for Artifacts:** ⚖️ (balance / neutral referee). Keep it stable across an artifact's redeploys.
- Keep it geometric, single-weight, monochrome-capable. No mascots, no gradients, no 3D.

## Do / Don't
- ✅ Let color mean something (indigo=engine, green=proven, red=blocked, amber=masked).
- ✅ Use the mono receipt + green ✓ to make *provability* tactile.
- ✅ Theme-aware: every surface works in light and dark (semantic layer handles it).
- ❌ No crypto tropes (neon violet, gold coins, glow, "web3" gradients) — our whole position is *no-crypto*.
- ❌ No red as an accent/decoration — it's reserved for red-lines/blocks.
- ❌ No hardcoded hex in components — always a token.

## Usage
Import the tokens, then style against the semantic/component layer:
```css
@import "tokens.css";
.btn-primary { background: var(--btn-primary-bg); color: var(--btn-primary-fg); border-radius: var(--btn-radius); }
.verdict--blocked { background: var(--verdict-block-bg); color: var(--verdict-block-fg); font-family: var(--verdict-font); }
```
See [`preview.html`](preview.html) for the live style reference (swatches, type, and the product
components — delegate card, verdict badges, max-min viz, receipt).
