Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 5 — Plan and mockups

Turn verified findings into a **Now / Next / Later** plan:

- **Now** — high value, small effort, low risk; can start tomorrow. Every
  Blocker is in Now, whatever its effort.
- **Next** — the redesigns and refactors that need a go-ahead.
- **Later** — strategic work (release path, new capabilities).

Each plan item links to its finding. Keep the plan short enough to read in a
minute; the tables hold the detail.

Mockups exist only when the design lens reports a High or Blocker finding. Render
up to three screens, each behind such a finding and the only ones the design
lens specs, as HTML inside the page, in the template's mockup frame,
following the theme toggle. Mockups are hand-written HTML and CSS that match the
platform's look; they are not screenshots of code, and they show the rewritten
copy, never placeholder text. The template ships a browser
frame; for a desktop-window, phone or terminal frame, copy
[`snippets.html`](../snippets.html)'s frame as its header says. With no such
finding, or no design lens, write none and say why on the page ([Page
content](./6-publish.md#page-content), Mockups).
