# Repo-audit keeps isolated instances up through Stage 3 and probes the UI

> **Status: Accepted** — maintainer decision (2026-11-21). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

## Context

ADR 0042's Stage 2 photographs a web UI with the built-in browser and stops the
server before the lenses start. The built-in browser needs a launch file in the
repo, which the read-only rule forbids writing, and it renders in light mode only.
A screenshot cannot measure what a browser can answer exactly: accessibility
violations, horizontal overflow, undersized targets, console errors, failed
requests, copy length and colours outside the design tokens. A stopped server
leaves no lens able to walk a task or send a request.

## Decision

- **Isolated instances.** For a web UI, Stage 2 starts the app on throwaway data
  (its demo mode, a variable that moves its data into the scratchpad, a profile
  flag or a temp profile), on a port its docs do not reserve. Two instances: a
  primary for captures, the probe and walkthroughs, and a second, with its own
  data directory and port, for the architecture lens's fault and security
  requests. With no such mode the UI is "not probed" with a reason.
- **Lifetime.** Both stay up through Stage 3. The main session stops both before
  Stage 4. Instances run inside the Execution boundary and the execute answer of
  ADR 0047.
- **Probe.** A Playwright install in the scratchpad, never in the repo, drives a
  matrix of main screens, states, widths and themes. A bundled `probe.js` returns
  one JSON cell each: axe-core violations, overflow, undersized targets, console
  errors and failed requests, copy metrics and undeclared colours. A keyboard-only
  pass covers each primary flow; a hosted site also gets lab Lighthouse numbers
  from its local build. The page carries failing cells and totals; raw JSON stays
  in the scratchpad.
- **Tests in CI.** `probe.js` keeps its judgements in pure helpers, tested with
  `node:test` and run by the `gate` job, the first non-Python test it runs. The
  browser side is checked by a scratch fixture run, since CI has no Chromium.
- **Unchanged.** The read-only rule, the Execution boundary's contents, the
  lenses, the other stages and the rubric's areas.

## Consequences

- A run on a web UI leaves processes alive for the length of Stage 3, so the run
  log records each one and stopping them is a failure condition when missed.
- The audit gains a Node and Playwright dependency, installed per run into the
  scratchpad; a machine that cannot install Chromium gets "Tool unavailable:
  Playwright Chromium" and a design lens that works from source.
- Automated accessibility checks find about a third to a half of WCAG issues, so
  the probe sets a minimum and the keyboard pass and the design lens cover the
  rest.
- Lighthouse numbers are lab figures from a local build, labelled as such: total
  blocking time stands in for INP, and localhost leaves out network latency.
- The `gate` job now sets up Node (the version `gate.yml` pins).
