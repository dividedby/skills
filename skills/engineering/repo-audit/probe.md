# Repo Audit — UI Probe

The one home for the UI probe: how Stage 2 measures a web UI that a screenshot
cannot, with Playwright in a scratch install and `probe.js` (beside this file).
`SKILL.md` Stage 2 owns the rule (isolated instances, the matrix, lifetime) and
cites this file for the method; the lenses read the probe's output and do not
re-measure it. Judging copy, brand and usability from the numbers is the design
lens's job ([`briefs.md`](./briefs.md)). The probe measures and judges nothing
itself. Other UI types use their [`types.md`](./types.md) entries.

Commands are sketches of the principle: use the repo's own run commands, and say
where a step differs. `$B` is the scratchpad folder of
[`baseline.md`](./baseline.md#setup).

## 1. Scope and trust

The probe starts the app and loads its pages in a browser, so it is the repo's
code running. It runs only when the conditions in `SKILL.md` Stage 2 hold, inside
the [Execution boundary](./SKILL.md#execution-boundary) and the answer in
[Ownership and trust](./SKILL.md#stage-1--scope). Skipped: see section 10.

## 2. Scratch install

Never in the repo, never global. Pin exact versions and record them in the run
log (checked 2026-11-22: Playwright 1.65.1, axe-core 4.14.1, Lighthouse 13.6.0;
look up current ones with `pnpm view <pkg> version` and keep the pin).

```sh
mkdir -p $B/pw && cd $B/pw && pnpm init
pnpm add --store-dir $B/cache/pnpm-store --save-exact playwright@1.65.1 axe-core@4.14.1
PLAYWRIGHT_BROWSERS_PATH=$B/pw/browsers pnpm exec playwright install chromium
```

`--store-dir` keeps pnpm's package cache in the scratchpad too. If the
download fails or Chromium will not launch, the dimension is "Tool unavailable:
Playwright Chromium". `probe.js` never imports from the repo: it finds
Playwright and axe-core in the folder named by `PROBE_MODULES` (or `--modules`)
and Chromium in `PLAYWRIGHT_BROWSERS_PATH`, defaulting to `$PROBE_MODULES/browsers`.
axe-core is injected from that folder, so a run needs no CDN and no network
beyond the app.

## 3. Instances

`SKILL.md` Stage 2 sets the rule. How:

- **Port.** Ask the OS for a free port and check the repo's docs, config and
  launcher for ports they reserve before using it; do not guess:
  `python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'`.
  Re-test just before starting. If the app loses a race, read its log and retry
  once on another port.
- **Data.** Read the config code for the variable, flag or demo mode that moves
  the data. A name found only by guessing is verified: files appear under the
  scratch data folder after a run, and the repo's real data folder is unchanged
  (a listing with mtimes before and after). Unverified isolation is "not probed",
  never run.
- **Environment.** Start each instance under the scrubbed environment in
  [`baseline.md`](./baseline.md#setup) with `timeout`, record its PID, port and
  data path in the run log, and stop it by PID, never by name.

## 4. Run one cell

```sh
env -i PATH="$PATH" HOME="$B/home" PROBE_MODULES="$B/pw" timeout 120 \
  node <skill folder>/probe.js --url http://127.0.0.1:<port>/<path> \
  --screen <name> --state <state> --width <px> --theme light|dark \
  --out $B/probe/cells/<screen>--<state>--<width>--<theme>.json \
  [--screenshot $B/probe/shots/<same name>.png] [--min-target <px>] \
  [--actions <file.mjs>] [--delay-ms <ms> --delay-match '<glob>'] [--keyboard <n>]
```

Exit code 0 means a cell was written, findings or not; 2 means the probe failed
(bad argument, Playwright or Chromium missing, navigation error). Dark mode is
Playwright's colour-scheme emulation, so the product's own `prefers-color-scheme`
styles apply. Each cell opens a fresh browser, so cells do not share state.

`node probe.js --summarise $B/probe/cells --out $B/probe/summary.json` totals
the cells per screen, failing screens first, and lists every failing cell with
its failing checks. Long unstructured blocks are counted, never failing: the probe cannot know the main path. A screen row carries `spaceDelimited`, false when any cell is not, and leaves word figures out of that row. The page's tables come from it.

## 5. The matrix

Each main screen × the states the product has (empty, loading, error,
populated) × the widths it supports × the themes it supports.

- **Widths:** 1280; 375 when the product targets phones (profile, README or UI
  doc); any width the repo's UI doc names.
- **Themes:** light, and dark when the source answers `prefers-color-scheme` or
  has a theme toggle. A product with one theme gets that one, and the other is
  "Not applicable (product has no dark theme)".
- **Write the cell list to `$B/probe/matrix.md` before running**, then log the
  cell count and wall time. The depth caps for the matrix are not set yet:
  until they are, sample by screen and say so ("Depth: <what was sampled>").
- Re-run a failing cell once; report only what reproduces, and say "flaky" for
  the rest.

## 6. States

Reach a state by scripted interaction, in a small ES module given to
`--actions` that exports `default async (page, ctx)`; `ctx.note(text)` adds a
line to the cell's `notes`. The module runs after the page settles and before
measuring.

- **Dialogs and panels:** click the control that opens each, then measure.
  A local app's task list opens an edit dialog; a hosted site opens a cookie
  banner's preferences panel.
- **Errors:** trigger each by invalid input, or by aborting a request in the
  module (`page.route('**/api/*', (r) => r.abort())`). Destructive actions run
  only against the isolated data.
- **Loading:** `--delay-ms` with `--delay-match` holds matching requests for that
  long and measures while they are pending (a local app's list request; a hosted
  site's image or font). For network throttling instead, open a CDP session in
  the actions module and call `Network.emulateNetworkConditions`.
- **Empty and populated:** start the isolated instance with and without sample
  data, or delete the throwaway data between cells.

## 7. What a cell holds

`schema: 1`. Every list is capped at 20 entries; a capped list is named in
`truncated`.

| Field      | Content                                                                                                                                                                                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `axe`      | one entry per violated rule: `rule`, `impact`, `selector` (first node), `count` (nodes)                                                                                                                                                                    |
| `overflow` | `present` (the page scrolls sideways), `scrollWidth`, `clientWidth`, and `elements` (the ones that start the overflow, not their children)                                                                                                                 |
| `targets`  | `small`: under 24×24 CSS px (WCAG 2.2 SC 2.5.8); `belowRepoMin`: under the repo's documented minimum from `--min-target`, else `repoMin: null`                                                                                                             |
| `console`  | console errors and uncaught page errors; `failedRequests`: failed requests and responses of 400 or more, with no query string or body                                                                                                                      |
| `copy`     | `visibleWords`, `longestBlockWords`, `longSentences` (over 25 words), `meanSentenceWords`, `longUnstructuredBlocks` (plain-prose blocks over 60 words), `repeatedBlocks` (distinct blocks of 8 words or more that appear more than once), `spaceDelimited` |
| `colours`  | `unmatched`: computed colours in use that match no declared CSS custom property (either theme), `declared`: how many distinct colours the custom properties hold, `unparsed`                                                                               |
| `keyboard` | only with `--keyboard`: `focusable`, `steps`, `trap`, `orderJumps`                                                                                                                                                                                         |
| `notes`    | lines the actions module added                                                                                                                                                                                                                             |
| other      | `url` (no query), `screen`, `state`, `width`, `theme`, `probe` (Playwright and axe versions), `screenshot`, `truncated`                                                                                                                                    |

Read them with their limits:

- axe-core finds about a third to a half of WCAG issues
  ([Deque](https://www.deque.com/automated-accessibility-coverage-report/)). A
  clean axe result is a minimum, not a pass; the keyboard pass (section 9) and
  the design lens cover the rest.
- The 24 px check does not model the spacing exception (an undersized target
  with enough clear space around it passes). It exempts disabled controls and
  links inside running text. A repo minimum is read from its UI doc or a
  `rules.md` row, else `null`.
- With 0 declared colours, every colour is unmatched: report it as "no design
  tokens", not as a hundred misses. Browser defaults (a button's grey) appear as
  unmatched; the design lens judges which matter.
- Copy metrics count text the user sees, grouped by block: the text under one
  block element, so a heading, list item or disclosure between two runs of text
  splits them. A block inside a heading, list item or open disclosure is
  structured and is never counted in `longUnstructuredBlocks`. `repeatedBlocks`
  compares text within one screen cell, never across screens, and stores none of
  it. `spaceDelimited` is false when more than half the letters are in an unspaced
  script (Chinese, Japanese, Thai, Lao, Khmer, Myanmar): the word and sentence
  fields mean nothing for that screen, and the totals leave them out. On any
  screen, the word, sentence and block fields count only the blocks that are
  themselves space-delimited, so a mixed-script screen is measured on its spaced
  text. Whether the
  copy is too long is the design lens's call, by the thresholds in
  [`briefs.md`](./briefs.md).

## 8. Lighthouse (a hosted site only)

Run it when the profile says the repo is a hosted site
([`types.md`](./types.md)); otherwise "Not applicable (not a hosted site)".
Run it against the **local primary instance** (a local build or preview of the
site): the run makes no request to the deployed URL.

```sh
cd $B/pw && pnpm add --store-dir $B/cache/pnpm-store --save-exact lighthouse@13.6.0
env -i PATH="$PATH" HOME="$B/home" CHROME_PATH="<$B/pw/browsers/chromium-*/ app binary>" timeout 180 \
  pnpm exec lighthouse http://127.0.0.1:<port>/ --only-categories=performance \
  --output=json --output-path=$B/probe/lh-<page>.json --chrome-flags="--headless=new" --quiet
```

`CHROME_PATH` is the full Chromium Playwright installed (not the headless
shell). From the JSON, report: `audits["largest-contentful-paint"]`,
`audits["cumulative-layout-shift"]`, `audits["total-blocking-time"]`, transfer
bytes and request count by type from `audits["resource-summary"].details.items`.
Compare them with the Core Web Vitals "good" thresholds: LCP 2.5 s or less, CLS
0.1 or less, INP 200 ms or less, and with a budget file when the repo has one
(`budget.json`, a `lighthouserc` file, a bundle-size config), one row each; with
none, say "no budget".

Every number is labelled **lab**. Total blocking time is a proxy for INP, not
INP, and says so. A run against localhost leaves out network latency.

## 9. Keyboard-only pass

For each primary flow (named in the README or UI doc; five at most):

1. Reach the flow's start with an actions module, then run the cell with
   `--keyboard <n>`, `n` at least twice the `focusable` count so a cycle shows
   (200 at most). Each step records the focused element, its accessible name,
   whether a visible focus indicator was drawn (an outline or shadow: confirm on
   a screenshot when it matters), its container and position.
2. Walk the controls with the actions module: Enter and Space on each control,
   Esc on each dialog and menu, then check where focus is after the update the
   action caused. Add a `ctx.note` per step.
3. Checks: tab order follows visual order (`orderJumps` lists upward jumps; the
   wrap to the start is expected once); focus is visible on every stop; every
   control works from the keyboard; focus stays or moves somewhere sensible after
   a re-render; no trap. `trap.trapped` means focus loops through the same
   elements without ever returning to the document; a cycle through the
   document is the normal wrap-around. `focusable` (a radio group counting once)
   sizes `n` only: it misses contenteditable regions and scrollers, so it is not
   used to judge a trap. Open shadow roots are followed (each inner stop has its own key
   and counts as a tab stop). An iframe is opaque: focus inside it is logged as
   the iframe with `opaque: true`, its stops are not counted, and a run of them
   is never reported as a trap; walk its controls by hand and say so in the log. A modal dialog cycles by design, so a trap there
   counts only when Esc does not release it.
4. Write `$B/probe/keyboard-<flow>.md`, one row per step:
   `n | element | accessible name | focus visible (y/n) | action | note`. The log
   is the evidence; the page gets one row per flow.

## 10. Skipped dimensions

Each skip is a reason from [`rubric.md`](./rubric.md)'s list, never silence.

| Case                                                       | Reason                                                  |
| ---------------------------------------------------------- | ------------------------------------------------------- |
| Untrusted repo and the answer is No, or no answer          | Untrusted not run                                       |
| No demo, data-dir or profile mode, or isolation unverified | Needs X: an isolated data mode                          |
| A second data dir and port are impossible                  | Needs X: a second data dir and port (primary is probed) |
| Chromium or Playwright will not install                    | Tool unavailable: Playwright Chromium                   |
| No user-facing UI (a CLI, a library, an infra repo)        | Not applicable (no user-facing UI)                      |
| Lighthouse on an app that is not a hosted site             | Not applicable (not a hosted site)                      |
| A theme the product lacks                                  | Not applicable (product has no dark theme)              |
| A width the product does not support                       | Not applicable (product does not support 375 px)        |
| No primary flow documented (keyboard pass)                 | Not applicable (no documented primary flow)             |
| Matrix sampled                                             | Depth: <what was sampled>                               |

## 11. Output

Everything goes under `$B/probe/`: `matrix.md`, `cells/*.json`, `summary.json`,
`shots/`, `keyboard-*.md`, `lh-*.json`. Raw JSON stays there for the design lens;
the page carries the totals and failing cells ([`template.html`](./template.html)
header). Screenshots are embedded under the size rule in `SKILL.md` Stage 6; keep
every failing cell's and the first cell per screen. Real user data never enters
the folder: the instances run on throwaway data, and URLs lose their query strings
before they are written.

## 12. Checking the probe itself

`probe.test.mjs` tests the pure helpers (`node --test`); it needs no browser.
To check the browser side, serve a static page in the scratchpad (not committed)
with one horizontal overflow, one 16 px button, one image with no alt text and
one 30-word sentence. Run the probe at 1280 light and 375 dark: each of the four
shows in the cell (`overflow`, `targets.small`, `axe` rule `image-alt`,
`copy.longSentences: 1`). A twin page without the overflow shows
`overflow.present: false`. Add a plain paragraph of 80 words in short sentences, the same 10-word
sentence in two elements and an 80-word list item: the cell shows
`copy.longUnstructuredBlocks: 1` (the list item is structured) and
`copy.repeatedBlocks: 1`.
