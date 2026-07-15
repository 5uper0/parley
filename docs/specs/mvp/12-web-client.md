# 12 — Web client

## Purpose

Expose the complete journey to non-technical users on a phone without teaching them “agents”,
“max-min”, schemas or cryptography.

## Screens

Landing/explanation, create case, checkout, invite status, participant welcome, private interview,
sheet review, evidence manager, waiting room, proposal review, accept/reject confirmation, revision,
agreement/deadlock receipt, settings/deletion.

## UX rules

- One primary action per screen and a visible step indicator for multi-step work.
- Autosave long forms; back navigation preserves answers and scroll position.
- Explain privacy before the first sensitive answer and again before disclosure.
- Render “red line” as “something I cannot accept”; technical detail is progressive disclosure.
- Waiting, generation, delivery and verification operations longer than 300 ms show status; submit
  controls disable during requests and remain idempotent.
- Error messages state cause and recovery next to the affected field.
- Mobile first at 375 px; no horizontal scrolling; body text at least 16 px; touch targets at least
  44×44 px with 8 px separation.

## Accessibility and visual contract

- WCAG 2.2 AA minimum: 4.5:1 normal-text contrast, keyboard completion, visible focus, semantic
  headings/forms, screen-reader status announcements, no meaning by color alone.
- Respect zoom and `prefers-reduced-motion`; motion is optional and never blocks input.
- Use existing `docs/brand/` semantic tokens and one SVG icon family; no emoji as structural icons.
- Plain system fallback fonts must preserve layout while brand fonts load with `font-display: swap`.

## Privacy contract

- Every view labels content as `Private to you` or `Shared with all parties`.
- No private content appears in URL, page title, analytics event, browser notification or email.
- Before sharing evidence or confirming a sheet, show the exact information leaving the private area.

## Acceptance criteria

- Two first-time participants complete create → invite → elicit → ratify → receipt on mobile.
- Entire flow is operable with keyboard and a screen reader.
- Refresh, back, expired session and slow network preserve or recover state without duplicate action.
- Automated tests cover all state screens; manual checks run at 375/768/1024/1440 px, 200% zoom,
  reduced motion and dark/light contrast if dark mode ships.

## Not in MVP

Native applications, live chat, voice, collaborative document editing, custom themes, dashboard
analytics, gamification.
