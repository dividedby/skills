# The publish seam recovers a malformed `<output>` loudly before failing the run

## Context

`harness/cli.py publish` is a **post-hoc parse seam**: it runs in a CI step
after the agent session is gone. There is no session to resume; upstream
resume-and-repair tools (e.g. Sandcastle) operate at the live session layer and
are unavailable here.

Intermittently (~1–2 runs in 10) the agent emits invalid JSON inside the
`<output>` block. The observed error is `Expecting ',' delimiter` — a trailing
comma or a lone control character inside a string field. Before this ADR the
parser hard-failed at `json.loads` before `<body-N>` salvage could run, so the
entire run's proposals were lost. The impact is low-stakes — a re-run regenerates
them — but a wasted unattended run is a real friction cost.

The governing principle is the **loud-beats-lossy doctrine** established in
[ADR 0004](0004-runbook-helpers-are-python-stdlib.md) and repeated through the
harness: a present-but-invalid block must never silently become found-nothing.
Every recovery path must announce itself; silent degradation is forbidden.

## Decision

Two deterministic recovery levers are added before the run fails:

**(a) Conservative one-shot JSON repair (`_repair_json`).** A single
quote-state-aware character walk (NOT regex — a naive ``,(\s*[}\]])`` regex
silently corrupts valid strings like `{"reason":"foo, }"}`) repairs the common
corruption before the second `json.loads` attempt:

- Outside strings: drops structural trailing commas (a `,` whose next
  non-whitespace character is `}` or `]`).
- Inside strings: escapes lone control characters (raw newline → `\n`, tab →
  `\t`, CR → `\r`) that are not already backslash-escaped.
- Re-strips a residual ` ```json ` / ` ``` ` fence if present (in case the
  primary strip missed a variant).

On a successful repair, `parse_output` emits `::warning::` to stderr and returns
the parsed dict. The caller proceeds normally. On a second failure, it raises
`ValueError` and control passes to level (b).

**(b) `<body-N>` salvage decoupled from `<output>` (`_salvage_bodies`).** When
`parse_output` raises `ValueError`, `_publish` calls `_salvage_bodies`, which
scans the raw log for `<body-N>` blocks (and the legacy `<body>` block) using
the same `extract_block` helper. For each block found it reconstructs a title
from the body's first markdown heading or first non-empty line, prefixed
`recovered: `. If ≥1 block exists, `_publish` files them under the reconstructed
titles (applying the same `MAX_PROPOSALS` cap), emits `::warning::` to stderr,
and returns 0.

**(c) Fail-loud floor.** Only when `_salvage_bodies` returns `[]` — no body
blocks at all — does the run fail (exit 1) without writing a summary. The
workflow's `if: failure()` step then surfaces the raw log. This preserves the
distinction between:

- *missing* (no `<output>`, no `<body-N>` → nothing salvageable → loud failure)
- *recovered-with-degradation* (warned loudly, proposals filed, run exits 0)

One file on the fetch-fresh harness rail reaches all three proposal loops on
their next run — no envelope change is required.

## Consequences

- Common `<output>` corruption (trailing comma, control char) no longer wastes
  an unattended run; the step summary notes the degradation.
- Degradation is always announced via `::warning::` in the CI step output —
  never silently swallowed.
- In-agent validate-before-exit (envelope-touching; coupled to issue #365;
  affordable once issue #366 lands a reusable workflow) is **deferred** until
  the observed recovery rate proves insufficient. Measurement is now possible:
  every recovery emits a warning that CI can surface and count.
- The `ParseOutputTest.test_raises_on_garbled_json` test fixture intentionally
  uses a double-comma (`,,`) pattern that is NOT fully repaired in one pass,
  preserving the fail-loud assertion for truly irreparable `<output>` with no
  `<body-N>` blocks.

## Rejected alternatives

- **Resume-and-repair** — no session at our seam; the agent is gone by the time
  `publish` runs.
- **Two-phase produce→extract** — the emitter is read-only with no side-effects
  to protect; splitting it would double agent cost with no structural benefit.
- **Migrate to Sandcastle** — a TypeScript migration; cannot use its session-
  resume capability at our seam; does not shrink the #366 workflow envelope.
- **Regex-based trailing-comma strip** — silently corrupts valid strings
  containing `, }` (e.g. `{"reason":"foo, }"}`). Forbidden; the quote-aware
  walk is the only safe implementation.
