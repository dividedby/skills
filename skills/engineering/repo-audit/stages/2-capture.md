Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 2 — Capture

Gather the evidence the lenses cannot gather blind. Anything here that executes
the repo's code follows the execute answer from Stage 1:

- **At `quick`,** the instances, the UI probe and the other UI captures below do
  not run, reason "Depth: quick run, `<method>` not run" (for the probe,
  "Depth: quick run, probe not run"); the baseline and the fleet check do.
- **Isolated instances (web UIs).** Start the app against throwaway data: the
  repo's demo or sample mode, an environment variable that points its data into
  the scratchpad, a profile flag, or a temp profile. Use a free port its docs and
  config do not reserve, never the user's real data folder, and the scrubbed
  environment; [`probe.md`](../probe.md) says how. Start two: a **primary** for
  captures, the probe and walkthroughs, and a **second**, with its own data
  directory and port, for the fault and security requests the architecture lens
  makes. With none of these modes the UI is "not probed (reason)", the reason
  from [`rubric.md`](../rubric.md), and the design lens works from source. Log
  each process in the run log (started, port, data directory, stopped).
- **UI probe.** [`probe.md`](../probe.md) against the primary instance: each main
  screen, in the states the product has (empty, loading, error, populated), at
  the widths it supports and in the themes it supports, with states reached by
  scripted interaction; a keyboard-only pass of each primary flow; for a hosted
  site, Lighthouse. Screenshots come from the same run. Raw JSON stays in the
  scratchpad. Every skipped dimension records its reason.
- **Other UI types** (CLI, native app, userscript): capture as the type's entry
  in [`types.md`](../types.md) directs, unless a repo rule forbids the method
  (see its How to use).
- **Lifetime.** Both instances stay up through Stage 3, each started as a
  harness background task ([`probe.md`](../probe.md#3-instances)) so the end of a
  turn does not reap it. The main session stops both before Stage 4 and logs it;
  none is left running at publish.
- **Baseline.** The main session runs [`baseline.md`](../baseline.md) before the
  lenses launch, under the [Execution boundary](../SKILL.md#execution-boundary). It writes
  `digest.md` with the raw output beside it in the scratchpad and judges
  nothing: the lenses do. It also covers the build time and the sizes of state
  or output files the code lens needs, and for a private repo at `standard`
  the all-refs secret scan the go-public feasibility check reads.
- **Fleet standards.** When the repo passes the ownership test, the main session
  runs the check in [`fleet-standards.md`](../fleet-standards.md) and fixes
  nothing it finds; a repo with no remote is "Not assessed (Needs X: a remote)";
  otherwise the section is "n/a (not a fleet repo)". Neither runs a row. The
  main session may hand the check to one `fleet-check (helper)`: it stays
  read-only, writes its results to a scratchpad file, and the main session reads
  that file, not the raw output.

**Done when:** each main screen has a capture (or the reason it has none), the
captures sit in the scratchpad, a web UI has a probe cell set per main screen and
a `probe` folder summary (or the reason it has none) and both instances are up
for Stage 3 (or the reason there are none), every checklist row has a result (or the
section is marked not checked, with the reason, or n/a for a repo that is not a
fleet repo), and `digest.md` is written with
a reason for every tool or gate that did not run.
