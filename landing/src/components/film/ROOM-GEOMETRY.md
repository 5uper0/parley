# Room hotspot geometry

Source of coordinates: `landing/src/data/film-hotspots.ts` (percent of the full image). Hotspot box: 44 x 44 CSS px, centred on the point.

## Phone crop (viewport width W <= 720, portrait image 1080 x 1920)

| quantity | formula | W = 390 |
|---|---|---|
| image width | 1.25 * W | 487.5 |
| image height Hi | 1.25 * W * 1920 / 1080 | 866.7 |
| image left | -0.125 * W | -48.8 |
| image top | -0.55 * Hi | -476.7 |
| stage height Hs | 0.28 * Hi = W * 28 / 45 | 242.7 |
| hotspot left | (x * 1.25 - 12.5) / 100 * W | see below |
| hotspot top | (y - 55) / 28 * Hs | see below |

Same crop as the POC `place()` (zoom 1.25, rows 55% to 83%), done in CSS, no script.

## Positions at 390

| n | object | x % | y % | left px | top px |
|---|---|---|---|---|---|
| 1 | Three sealed notes (Cara's note) | 62.5 | 61.6 | 255.9 | 57.2 |
| 2 | Bob's assistant | 51.4 | 60.8 | 201.8 | 50.3 |
| 3 | Result card | 16.7 | 71.4 | 32.7 | 142.1 |
| 4 | Receipt | 81.5 | 72.9 | 348.6 | 155.1 |
| 5 | Install card | 53.2 | 78.1 | 210.6 | 200.2 |
| 6 | Book | 52.3 | 68.6 | 206.2 | 117.9 |
| 7 | Plaque | 40.0 | 65.1 | 146.2 | 87.5 |

## Pairwise distances at 390 (px)

Two 44 px boxes do not intersect when max(dx, dy) >= 44. Box gap = max(dx, dy) - 44.

| pair | dx | dy | box gap |
|---|---|---|---|
| 1-2 | 54.1 | 6.9 | 10.1 |
| 1-3 | 223.3 | 84.9 | 179.3 |
| 1-4 | 92.6 | 97.9 | 53.9 |
| 1-5 | 45.3 | 143.0 | 99.0 |
| 1-6 | 49.7 | 60.7 | 16.7 |
| 1-7 | 109.7 | 30.3 | 65.7 |
| 2-3 | 169.2 | 91.9 | 125.2 |
| 2-4 | 146.7 | 104.9 | 102.7 |
| 2-5 | 8.8 | 149.9 | 105.9 |
| 2-6 | 4.4 | 67.6 | 23.6 |
| 2-7 | 55.6 | 37.3 | 11.6 |
| 3-4 | 315.9 | 13.0 | 271.9 |
| 3-5 | 177.9 | 58.1 | 133.9 |
| 3-6 | 173.6 | 24.3 | 129.6 |
| 3-7 | 113.6 | 54.6 | 69.6 |
| 4-5 | 138.0 | 45.1 | 94.0 |
| 4-6 | 142.3 | 37.3 | 98.3 |
| 4-7 | 202.3 | 67.6 | 158.3 |
| 5-6 | 4.4 | 82.3 | 38.3 |
| 5-7 | 64.4 | 112.7 | 68.7 |
| 6-7 | 60.0 | 30.3 | 16.0 |

## Other widths

| layout | stage width | stage height | smallest box gap | pair | smallest inset from stage edge |
|---|---|---|---|---|---|
| phone | 320 | 199.1 | 0.4 | 1-2 | 4.8 |
| phone | 360 | 224.0 | 6.0 | 1-2 | 8.2 |
| phone | 390 | 242.7 | 10.1 | 1-2 | 10.7 |
| phone | 414 | 257.6 | 13.4 | 1-2 | 12.7 |
| phone | 720 | 448.0 | 55.9 | 1-2 | 38.3 |
| wide, viewport 721 | 641 | 360.6 | 3.6 | 5-6 | 19.8 |
| wide, viewport 1440 | 1020 | 573.8 | 31.7 | 5-6 | 44.6 |

## Changes from the POC coordinates

| n | POC portrait | now | reason |
|---|---|---|---|
| 1 | 42.6, 61.5 (Bob's note) | 62.5, 61.6 (Cara's note) | was 48 px from hotspot 2 in x and 2 px in y at 390, boxes touched at 360 and sat on top of the plaque |
| 2 | 52.5, 61 | 51.4, 60.8 | centred on the pawn |
| 5 | 53, 77 | 53.2, 78.1 | centred on the card |
| 6 | 49, 68 | 52.3, 68.6 | was 19.5 px (x) and 78 px (y) from hotspot 5; moved right to clear the plaque |
| 7 | 36, 66 | 40, 65.1 | moved onto the plaque itself |

Numbers are arithmetic from the formulas above, not browser measurements. The lead measures bounding boxes in Playwright (AC-1).
