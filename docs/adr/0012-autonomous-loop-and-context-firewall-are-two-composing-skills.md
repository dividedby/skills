# autonomous-loop and context-firewall are two composing skills

Two requested capabilities — running an agent unattended over a backlog (#65)
and keeping output quality from decaying as one long run fills its window (#67)
— ship as **two separate engineering skills that compose**, not one combined
skill and not mutually-disclaiming siblings. In the same decision, the
`autonomous-loop` skill is scoped to **generalize** the **Proposal loop** family
rather than inherit its constraints.

**Why two, not one.** Both bodies of knowledge pass the deletion test
independently: delete context-firewall and a loop over multi-item iterations
must re-teach per-item context hygiene; delete autonomous-loop and the
loop-hardening knowledge (HITL→AFK, caps, monitor/stop) has no home. The
deciding factor against folding them into one skill is **discoverability of the
loopless case**: context-firewall's motivating request — `agent-research`'s daily
synthesis — is a **single monolithic run with no loop at all**. A combined
"autonomous-**loop**" skill would bury the firewall technique behind a loop
trigger the monolithic-run user never reaches for. context-firewall must stay
independently invokable.

**Compose, not disclaim.** The skills do not pretend not to know each other.
They share one unit — the **work item** (one briefed, independently-runnable
chunk) — and autonomous-loop carries a one-way pointer: when an iteration is
itself multi-item, reach for context-firewall. The cleanest loops make the
**iteration boundary a context boundary**; a CI-cron runtime gives that for free
(a fresh `claude -p` per run), while a single interactive session or a monolithic
run does not — there context-firewall supplies it via sub-agent dispatch. The two
also share a concrete artifact: the **durable progress file** serves
autonomous-loop's monitor/stop/resume *and* context-firewall's
flush-then-compact, so dropping in-context state is safe because it is persisted.

**Applying loops are first-class; ADR 0003 is the strict end, not the rule.**
[ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md) makes the
**Proposal loop** family propose-only because an AFK agent editing the published
plugin unsupervised is unacceptable. autonomous-loop is general methodology: it
teaches loops that **commit / open PRs / auto-merge on a green gate** (the kind
that burned down #64 then #66), with propose-only as the *strictest* setting on
a gate spectrum, not the universal one. The control that makes unattended
applying safe is **graduation-by-guardrail**, not observation time — you earn AFK
when (1) a deterministic guard blocks irreversible ops (the #64 git-guard is the
worked example — it was sequenced first precisely to harden the loop that then
did #66), (2) work lands on branches/PRs never `main`, (3) every iteration passes
its feedback gate or halts, and (4) an iteration / cost / time cap bounds the run.

**Defer, don't reinvent — on both sides.** autonomous-loop owns only loop
discipline (stop condition, feedback gates, HITL→AFK + cap, monitor/stop). It
defers **execution** to an existing runtime (`/loop`, `/schedule`, or CI-cron
`claude -p` — it teaches runtime *selection*, not a new runtime) and **input** to
`to-issues`/`triage`, treating a briefed backlog as what it consumes. context-
firewall likewise reuses the existing Agent/sub-agent dispatch rather than a new
sub-agent runtime.

**The brief is the contract, but per-item pickup reconciles it against the live
issue.** A firewall "loads only one work item's inputs," and the brief — not the
issue body and discussion — is that contract for the work (per `triage/
AGENT-BRIEF.md`). That principle stays. But two failure modes survive it: a brief
that *looks* complete while silently dropping load-bearing context the body
carries (the same distilled-artifact-diverging-from-source drift as the #86
defect), and a brief that goes stale because clarifying or scope-changing
comments land after it was written. So at **per-item pickup, inside the
disposable firewalled sub-agent**, the agent reads the issue's current full body
+ all comments and reconciles them against the brief; on a **material**
discrepancy it **halts the item and records why in the progress file** rather
than proceeding on its own reconstruction (mirroring the gate-or-halt model —
there is no author to bounce to mid-run, and a confident wrong guess on a stale
brief is unrecoverable while a recorded halt is). Trivial/cosmetic mismatches do
not halt. Because the full read lives in the per-item context, the bloat is
transient and discarded — the orchestrator never accumulates it, so the firewall
is preserved (the composition already documented above). *Rejected here:* an
**orchestrator-once read** (hoists the body into the accumulating context — the
bloat the firewall exists to prevent); **blanket
read-everything-every-iteration** (same accumulation, every pass); and
**fold-then-proceed without halting** (silently self-authors a new brief from a
possibly-stale read, the unrecoverable wrong-guess this exists to stop). Only
*per-item-in-sub-agent + halt* catches the drift without breaking the firewall.

**Rejected alternatives.** *One combined skill* — loses loopless-run
discoverability, the whole reason #67 was requested. *Making autonomous-loop
propose-only too* (inheriting ADR 0003 universally) — excludes the most common
AFK case, burning down a feature backlog, and contradicts what the repo already
does. *Mutually-disclaiming siblings* (each SKILL.md saying "this is NOT the
other") — the trigger-collision worry that prompted it is better solved by a
shared vocabulary and a one-way compose pointer.
