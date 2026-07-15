# Brand calibration — Linear benchmark (2026-07-09)

*Ran `extract-design` on linear.app to sharpen (not replace) the `brand.md` identity. We borrow
Linear's **structure and craft**, never its colors/logo. Our signal palette and the red-line / receipt
/ ✓-seal signature stay — that's our identity; Linear has no equivalent.*

## What we take (deltas to `tokens.css` / `brand.md`)
| Dimension | Current | Sharpened (Linear-calibrated) | Why |
|---|---|---|---|
| **Dark surface** | mid-dark | **near-black, cool** `#0A0B0D` (hsl ~210° 4%) | premium, calm, serious; the audited-terminal feel |
| **Neutral ramp** | cool slate | keep, but **push the blue-grey cast** consistently (hsl 210–223°) | one disciplined ramp, no warm drift |
| **Text on dark** | white-ish | **cool off-white** `#F7F8F8` (never pure #fff) | softer, less glare, more refined |
| **Display weight** | 700 | **510–560** for h1–h3 | Linear's insight: lighter display reads *premium*, bold reads *loud* |
| **Heading leading** | ~1.15 | **~1.0–1.05** (tight) | editorial density, precision |
| **Base size** | 16 | **15** (mono stays 13–14) | tighter, more technical |
| **Radii** | 8 / 12 | keep tight (**6 / 10 / 14**) | precision over softness — Linear uses 4/7/16 |
| **Elevation** | subtle shadow | **hairline 1px border + one big soft ambient shadow** (`0 0 64px rgba(0,0,0,.4)`) | depth by border first; the ambient glow is the craft move |
| **Background motif** | red-line rule only | **add a faint line-grid** (`repeating-linear-gradient`, ~3px/7px, in the darkest neutral) behind heroes | technical "graph-paper / ledger" texture; pairs with the red line |

## What we deliberately reject
- Linear's **acid-yellow `#e4f222` / neon-green `#00ff05`** — their identity, and neon violates our
  no-crypto rule. Our green is the muted **verify** `#0E8F63`, not a signal-glow.
- Pill-heavy shapes / "material-you" softness — we stay precise (small radii, hairlines).

## The signature we keep and lead with (Linear has none of this)
The **red-line rule** (a crossed constraint), the **mono receipt** blocks (hash / signature / transcript),
and the **green ✓ seal** (verified, non-betrayal). Provability made tactile. Every public surface should
show at least one of these — it's what makes a Parley screenshot unmistakable and *true*.

## Method
Prove the direction on one exemplar (the proof-card, `docs/brand/proofcard-v2.html`) → get taste
approval → then roll the sharpened tokens through `tokens.css` + every public surface (README hero,
demo money-shot, OG card, dashboard, try-it playground) via `design-system` + `ui-ux-pro-max`.
