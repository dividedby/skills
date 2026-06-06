# Skill-improvement workflows run AFK and propose via issues

Two recurring workflows consume the [`agent-research`](https://github.com/dividedby/agent-research)
knowledge base to improve this repo: a **self-improvement** workflow that
refines existing skills against how skilled practitioners build agents, and a
**gap-scanner** that reads the maintainer's *other* repos to propose net-new
skills. Both run unattended on an always-on VPS.

Neither ships as a skill. "Improve *my own* skills from *my own* KB" and
"propose skills for *my own* repos" is narrow, personal machinery — exactly what
[ADR 0001](./0001-buckets-cluster-by-user-intent.md) and the repo's ethos keep
*out* of the published plugin. They are **run-books** (see `CONTEXT.md`): cron-
driven prompts the AFK agent follows, living in this repo (co-located with what
they edit) but never registered in `plugin.json`. The self-improvement run-book
may *invoke* `improve-codebase-architecture` as a step; it is not a cron over it.

**Producer / decider split.** The VPS runs only the *producer* phase — read,
analyze, write up. A human runs the *decider* phase — review, merge. The line
between them is the control that makes unattended operation safe:

- The VPS **may auto-commit analysis/bookkeeping** — specifically the
  integration map, which is C's own reasoning baseline, not a change to a skill.
- The VPS **may not auto-merge changes to skills themselves.** Each run surfaces
  its single highest-value proposal as **at most one issue** (zero is fine) on
  the tracker, tagged with a label (e.g. `self-improvement`) the run-book also
  reads to avoid re-filing. The existing triage labels gate the merge.

The one-issue-per-run cap is deliberate: it forces each run to pick *the* best
proposal rather than spraying a backlog, and keeps the human review trickle
digestible.

**The gap-scanner files into a public tracker.** This repo is public, so its
issues are public, but the gap-scanner reads **private** repos. Its issues must
therefore describe the recurring *need* and the proposed skill in **generalized
terms — never quoting or paraphrasing proprietary code.** This aligns with the
ethos anyway: a skill worth proposing is broadly useful, so its proposal should
read as broadly useful. The scanner reads private repos read-only, shallow, and
cleans up after each run; the repo list is an explicit curated config, not
auto-discovery of everything the maintainer owns.

**Amendment (#26): the sanitizer guard covers self-improvement too.** This ADR
originally framed the structural sanitizer around the gap-scanner, because that
was the workflow obviously reading private *repos*. But self-improvement also
reads a private source — the `agent-research` KB — and (since #19) files issues
whose title/body are derived from it into this same public tracker. That is the
same private-source → public-tracker risk shape, so the guard applies to both:
each run-book runs its filed `title + body` through `check()` (always passing
the configured `private_markers`) before filing, dropping any draft that trips.
The guard is structural and necessary-not-sufficient (see `sanitizer.py`); prose
discipline still matters for private identifiers the markers don't cover.

These workflows are **independent jobs**, not a pipeline. The KB is a *source*
they consult — often the first one — not a gate: a run with no KB change can
still find a proposal from the repo itself, its own integration map, or the
maintainer's other repos.

**Rejected alternatives.** Shipping them as skills (too narrow for the plugin).
One orchestrated B→C→D pipeline (rejected — independent jobs; the KB is a source,
not a trigger). Auto-merging skill changes (no human gate; an AFK agent editing
the published plugin unsupervised is the exact risk this split avoids).

**Amendment (decentralized pull): the topology flips from push to pull, and the
consumer mechanism becomes a published skill.** agent-research ADR 0019
("knowledge consumed via decentralized pull") supersedes the *central-push*
shape of this ADR. The self-improvement and gap-scanner run-books — designed to
run on the VPS and push proposals into consumers — were built but never wired;
they are superseded. Consumption is now **decentralized pull**: each consumer
repo runs its own loop and proposes changes *to itself*. Three consequences
revise this ADR:

- **It *is* a skill now.** The "too narrow for the plugin" rejection above
  assumed a single-consumer "improve *my* skills from *my* KB" machine. The
  replacement, `apply-agent-research`, is a **general** capability any consumer
  installs (it never knows whose KB or repo it reads) — broadly useful, so
  plugin-worthy under ADR 0001. It is a **published skill**; the per-repo
  schedule that fires it is a thin run-book wrapper. The reusable pure helpers
  (`proposal_gate`, `sanitizer`) carry over unchanged; the central orchestrators
  and their topology-bound modules are deprecated.
- **The producer now commits nothing.** This ADR allowed the VPS one auto-commit
  — the integration map. The map is dropped (the host repo's own governance docs
  are the "already-do-this" baseline), so the loop writes *nothing* to the repo:
  pure read → file ≤1 issue. The producer/decider line is sharper than before.
- **The sanitizer's justification shifts, its role does not.** The KB is read via
  a *public* knowledge mirror, so the guard no longer protects the KB; it protects
  against leaking the **host repo's own** private content into a public tracker
  (load-bearing when the host is private, and for the deferred `skill-request`
  cross-repo flow). The `#26` amendment's structural guard stands.

The consumer-side realization lives in
[`docs/design/cross-repo-knowledge-application.md`](../design/cross-repo-knowledge-application.md).
The provenance label is `source:agent-research`.

**Amendment (#108): the leak guard wraps the wired filing path.** The structural
sanitizer above was originally a *separate* step the loop ran before
`gh issue create` — code-enforced as a decision, but prompt-trusted in its
*invocation* (the agent had to remember to run `sanitize`, then file). That was the
one place the producer/decider safety still rested on prompt adherence. It is now
closed the way the arch-review loop closed its publish cap (issue #104): the guard
is **folded into the filing seam** (`cli.py file` / `cli.py comment`), which
sanitizes the `title + body` and shells to `gh` **only on ALLOW**. A Consumer
workflow additionally disallows direct `gh issue create` / `gh issue comment`, so
the guarded path is the only way the wired loop writes a tracker — "sanitize before
filing" now holds by construction (the *make-the-bad-state-impossible* move applied
to the realistic forgetting-failure). This is **defense-in-depth, not a sandbox**:
an agent with arbitrary Bash could still subvert it, so the no-leak guarantee stays
*necessary-not-sufficient* and prose discipline still matters — the `#26` structural
guard is unchanged in what it inspects, only in how it is invoked.
