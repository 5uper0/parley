# Parley social media kit (2026-10-24)

Published subset: `logo/*.svg`, this README and `build_vectors.py`. The PNGs, the PDF, `guidelines/`, `favicon/` and `fonts/` named below stay out of this repo; `build_vectors.py` needs the Inter font file from `fonts/` to rebuild.

Concept "the floor line" (reviewed by an independent design pass 2026-10-24): the red rule is the red line no option may cross. Bars stand on it: hatched amber bars are masked verdicts, the indigo bar is the floor that max-min lifts, the green tick marks the verified result, the crossed red box below the rule is the blocked option. Mark: lowercase "p" with the red dot, as in the favicon. Fonts: Inter and JetBrains Mono (SIL OFL), copied to `fonts/`. Colours are the brand signal colours brightened for a dark ground (indigo #4A57D6, green #14A878, amber #D49A2A; red-line red stays #C42121); `docs/brand/tokens.css` keeps the light-ground values. Rebuild: `build.py` (PNGs), `build_vectors.py` (SVGs, needs fonttools), `build_favicon.py`, `build_guidelines.py` (guidelines and PDF); needs Pillow.

| File | Use |
|---|---|
| avatar-square-1024.png | Square avatar for dev.to, Hugging Face, Reddit, X, LinkedIn Page, Telegram. The tile sits inside 80% of a circle crop. |
| banner-x-1500x500.png | X header, GitHub social preview source, Hugging Face org banner |
| banner-linkedin-1584x396.png | LinkedIn Page cover |
| story-cover-1080x1920.png | Story or highlight cover |
| brand-sheet-1600x1000.png | Palette and fonts on one page |
| Parley-brand-guidelines.pdf, guidelines/*.png | 8-page brand guidelines: mark, logo set, colour, type, floor-line motif, applications, misuse |
| logo/*.svg | Vector logo set outlined from Inter SemiBold: mark on dark and light, mono, with line, wordmark, avatar tiles, verdict bars |
| logo/wordmark-on-dark.svg, wordmark-on-light.svg | tight viewBox, no clear space: add the 16 percent clear space from `brands/parley.md` yourself. viewBox `184 -2050 8335.6 2628` (2026-11-23): full path bounds x 186 to 8517.6, y -2048 to 576, plus 2 units on every side; the old `-300 -1856 9118 2732` clipped the l ascender 192 units at the top. Checked at 1x: the 1-px border has no opaque pixel |
| favicon/ | icon-16, 32, 180, 192, 512 PNG and favicon.ico |
| fonts/ | Inter SemiBold and Regular, JetBrains Mono Regular and Bold (SIL OFL) |

Existing assets: `docs/brand/assets/og-card.png` (link preview), `proofcard.png`, `parley-money-shot.gif`, favicon set. Text for boilerplate and facts: `docs/press/PRESS-KIT.md` (public) and `docs/capital/media-kit/README.md` (funders).

## Rollout status (2026-10-24)

| Place | State |
|---|---|
| dev.to @parley-protocol | default avatar; upload avatar-square-1024.png (file picker is on the MacBook, so Oleh uploads) |
| Hugging Face parley-protocol | default avatar; same |
| Reddit u/parley_protocol | not checked |
| LinkedIn Page parleyprotocol | marketing-dept to apply avatar and cover |
| GitHub 5uper0/parley social preview | not set; `gh` cannot set it, upload in repo settings |
