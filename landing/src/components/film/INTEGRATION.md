# film page integration (pieces B and C)

All edits are in `landing/src/pages/film.astro`. Copy comes from `landing/src/data/film-copy.ts` (`hero`, `menu`).

1. Piece B: uncomment `import Hero from "../components/film/Hero.astro";` (frontmatter), then replace the whole `<div id="hero-slot">...</div>` block with `<Hero />`. Hero must render the H1, sub and `Try the demo` as HTML (the slot does today).
2. Piece C: uncomment `import Room from "../components/film/Room.astro";`, then replace `<div id="room-slot"></div>` with `<Room />`.
3. Open a section from the room: set `location.hash` to `#how-1`, `#how-2`, `#code`, `#receipt`, `#install`, `#docs` or `#status` (R-17). The page script adds `.hl` to that section on `hashchange`. `history.replaceState` does not fire it.
4. Sticky header: sections use `scroll-mt-24`; keep new anchors on the same offset.
5. Drop the unused `hero` / `DEMO_URL` import in `film.astro` once Hero owns that copy.
