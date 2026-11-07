# Parley brand sheet (2026-11-07, proposed, design-dept agreement open)

Short form of [`docs/brand/brand.md`](../docs/brand/brand.md) and [`docs/brand/tokens.css`](../docs/brand/tokens.css), which stay canonical. This file answers anti-slop gate items 20, 21, 23, 25 for `/` and `/demo`.

## Type pair and why
- **Inter** for headings and body. Neutral infrastructure voice; the page makes claims, so the type should not add any. Open source.
- **JetBrains Mono** only for artefacts the product really produces: transcript lines, hashes, signatures, code. Mono marks "this is the record", so it is not used for headings or section labels.
- Not a reason: large mono headings, wide-tracked uppercase labels. The hero label above the H1 and the `/demo` pill were removed on 2026-11-07 for this.

## Accent
- **Indigo** (`#6675d3` dark, `#3a45b0` light) means "the neutral engine". Green means a verified result, red means a crossed red line, amber means a masked verdict. Colour carries product meaning, so red and green are not used as decoration.
- No gradient, no glow, no purple-to-cyan. The only shadows are hairline borders and an inset 1px highlight.

## Theme
- Dark is the default, light is kept (`data-theme="light"`). Proposed, not yet agreed with design-dept; kill rule: if not agreed by 2026-11-20, ship as is.

## Decoration rules
- No eyebrow pill or label above the H1.
- The transcript card in the hero is a real artefact and stays.
- One arrow style: none on CTAs (2026-11-06). Dashes are periods or colons.

## Contrast (gate item 25), measured 2026-11-07
`python3 scripts/contrast-check.py` reads `landing/src/styles/global.css` and the `/demo` tokens. Text needs 4.5:1. Before: dark `--subtle` was 4.13:1 on bg and 3.90:1 on surface, demo dark `--dim` and light `--dim` also failed. After: `--subtle` dark `#7a8394` (5.16 and 4.87), demo `--dim` dark `#7E848E`, light `#6B717D`. Result: 36 pass, 0 fail.
