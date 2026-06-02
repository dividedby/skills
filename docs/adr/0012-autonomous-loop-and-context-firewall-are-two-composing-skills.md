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

**Rejected alternatives.** *One combined skill* — loses loopless-run
discoverability, the whole reason #67 was requested. *Making autonomous-loop
propose-only too* (inheriting ADR 0003 universally) — excludes the most common
AFK case, burning down a feature backlog, and contradicts what the repo already
does. *Mutually-disclaiming siblings* (each SKILL.md saying "this is NOT the
other") — the trigger-collision worry that prompted it is better solved by a
shared vocabulary and a one-way compose pointer.
