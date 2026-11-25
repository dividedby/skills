Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 3 — Lenses (parallel)

Before launching, curl each instance. Restart any that is down as a new
background task on the same port and data directory, and log it as
`process restarted` in the run log. A lens that finds an instance down reports
it, and the methods that need it wait for the restart: the lens marks them
"blocked: instance down" and carries on with the rest; the main session restarts
the instance and continues that lens (SendMessage to the same agent) to run
them. A lens never starts an instance of its own, except the architecture lens's
outbound-calls restart of the handed-over second instance
([`briefs.md`](../briefs.md) shared header).

First write `<scratchpad>/briefs/shared-header.md` once, with one copy of what
every lens needs: the shared header's facts ([`briefs.md`](../briefs.md): the
pinned commit, the profile, the execute answer, the size facts, the paths of the
baseline digest and the fleet-standards results), the read-only rule, the
[Execution boundary](../SKILL.md#execution-boundary) and the Severity section of
[`rubric.md`](../rubric.md), verbatim. Then launch the applicable lens agents (at
most four at `standard`) in one message as background agents, so they run concurrently
and the harness notifies the main session as each returns. Each prompt
tells the lens to read that file first, then its own section of
[`briefs.md`](../briefs.md) by path and heading (not line ranges, which drift),
and adds only the parts specific to the lens: its areas and their applicability
facts, the relevant captures, the probe output paths, the running instances'
addresses (the primary for every lens, the second for the architecture lens,
with its data directory, PID and background task id), the path of its raw output, the type entries
and the tier's reading rule, the path of the `rules.md` rows for the areas it
owns, and the adaptations (dropped bullets, types bullets, the user's focus).
The product lens is also told to read [`rubric.md`](../rubric.md) CI cost
severity by path. The [lens table](../SKILL.md#lenses-depth-and-budgets) sets the lens's
agent type, model and tools (launch with that agent type and model). Each writes
its report (and the design lens, when it has a High or Blocker finding, its
mockup spec) to a named scratchpad path and returns a short summary. A CLI,
native, infra or library repo has no instance: the hand-over gives the scratch
build path and the wrapper command to run it (or "none: static only"), and a
method that needs an instance takes its reason from [`probe.md`](../probe.md#10-skipped-dimensions)
Skipped dimensions or the type's entry. The design lens is one agent: its copy table, brand inventory and
walkthrough logs go in its report file, and its walkthrough screenshots come from
its own session on the primary instance.

With a previous run, each lens also gets that run's findings in the areas it
owns (key, area, title, evidence path). Its report ends with a "Previous keys"
line: each such key it re-raised, with its new finding, and each it did not
re-check, with why (sampled out, not read). A key it names there is never
`fixed`.

Each lens has a wall-time and token ceiling: 1.5 times its row in the [budget
table](../SKILL.md#lenses-depth-and-budgets) for the run's depth and tier. Log each lens's
wall time and tokens against its row.

- **Over its ceiling:** stop the lens. Use what it wrote so far and mark it
  partial; if it wrote nothing, mark it failed. No retry.
- **Errors, hits a usage or rate limit, or returns without a report file:** if
  it wrote nothing, relaunch it once with the same brief. A second failure marks
  the areas it owns "Not assessed (lens failed: reason)".
- **Failed after writing something:** keep the partial output, marked partial,
  with the reason. No retry.
- **Thin report:** a report that has no result and no skip reason for a method
  of its areas, or no rules-block entry for a `rules.md` row of its areas, is
  marked partial, reason "thin: <method or row>".
- **Not progressive:** the checkpoints are each lens-return notification and any
  other wake-up during Stage 3. At each, the main session records every running
  lens's report file size (`wc -c`, 0 when absent) in the run log's Checkpoints
  table with its own `TZ=America/Chicago date +%H:%M`, and a returning lens's
  final size. A lens is not progressive when, at every checkpoint inside its
  run, its file was no larger than its start-time line (`head -n 1 <file> |
wc -c`); the Agents row status says `done (not progressive)`. A lens with no checkpoint
  inside its run is not judged, and the Checkpoints table says "not judged" for
  it. The lens's own finding times are supporting evidence only.
- **Resume, same session only.** The rule is in [The run log](../SKILL.md#the-run-log).

Each lens that runs the repo's code checks the repo after each such command (the
shared header in [`briefs.md`](../briefs.md)). The main session runs the check at
each agent return, and copies the lens's checks into the proof as
`after gate: <lens>: <command>` rows.

Log each agent as [The run log](../SKILL.md#the-run-log) directs.

**Done when:** every launched lens has returned, been stopped or been marked
failed, each one's report file exists, or its areas are marked "Not
assessed", and both instances are stopped (Stage 2, Lifetime).
