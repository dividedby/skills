# context-firewall folds into autonomous-loop as a supporting doc, not a standalone skill

> **Status: proposed** — supersedes [ADR 0012](0012-autonomous-loop-and-context-firewall-are-two-composing-skills.md). Pending maintainer ratification; until then 0012 stands and no skill is moved or deleted. Decision spike: [#446](https://github.com/dividedby/skills/issues/446).

[ADR 0012](0012-autonomous-loop-and-context-firewall-are-two-composing-skills.md)
kept `autonomous-loop` and `context-firewall` as **two independently-invokable
skills**, on the deciding rationale that the firewall has a **loopless** user —
`agent-research`'s daily synthesis, a single monolithic run with no loop — who a
combined "autonomous-**loop**" skill would never reach. We now **retire
context-firewall as a standalone skill** and re-home its discipline as a
supporting doc, `skills/engineering/autonomous-loop/FIREWALL.md`, that
autonomous-loop reads for per-item context hygiene. The firewall **knowledge is
kept in full**; only its standalone *trigger* is dropped.

**ADR 0012's load-bearing premise didn't hold.** Its case for two skills rested
on a predicted standalone loopless invoker. That prediction never materialized:
no `daily synthesis` / monolithic standalone-firewall consumer is wired anywhere
in the repo, and the only realized `agent-research` machinery
(`apply-agent-research`) is **itself a loop**. The maintainer's lived workflow is
the data point the prediction was waiting on — every real use co-invokes
("implement issues a/b/c/d with autonomous-loop + context-firewall, close with
flow-pr"); context-firewall has **never** been invoked on its own. A trigger
protecting a user who never arrives is cost (an adjacent-trigger collision
surface ADR 0012 itself flagged) without benefit.

**The harness baseline subsumes the dispatch, not the discipline.** The fold
argument in #446 — "the global harness already mandates per-item sub-agent
dispatch, so the standalone firewall is redundant" — is half right. The
delegation baseline supplies only the firewall's **step 2** (a fresh sub-agent
per item); context-firewall's own text concedes this ("a builder/architect
delegation already *is* a do-and-report firewall — the remaining job is the
orchestrator-side half"). It does **not** teach step 1 (identify the repeatable
per-item unit), step 3 (the proactive between-item budget checkpoint before the
harness force-compacts), or step 4 (intentional flush-to-durable-artifact +
drop). Those three are real, non-obvious orchestrator discipline no delegation
table carries. So the argument correctly retires the standalone *skill* but does
**not** justify deleting the *knowledge* — which is exactly why it becomes a doc,
not nothing.

**agent-teams is not evidence here.** Per the [#445](https://github.com/dividedby/skills/issues/445)
eval, Claude Code "agent teams" does not strengthen the fold: the
baseline-subsumes-dispatch claim rests on the **plain Agent tool**, which
supplies disposable per-item isolation with or without agent-teams, and
agent-teams (parallel collaborating sessions) is orthogonal to the decisive
single-disposable-distillation case. This decision cites it as **no part** of
its rationale.

**The loopless user keeps a documented home — as a doc, not a trigger.** #446
requires that whatever wins leaves the loopless monolithic-run user a documented
home for per-item context hygiene. `FIREWALL.md` is that home: a cross-linked,
independently-readable discipline doc, reached from autonomous-loop's per-item
step, from `docs/agents/skill-authoring.md` (where it is a copy-in pattern for
*any* multi-item skill, loop or not), and from the `CONTEXT.md` vocabulary entry.
A genuinely loopless run — scheduled or programmatic — bakes the technique in and
references the doc; it never needed a discoverable trigger, which only matters
for interactive invocation. The thing ADR 0012 feared losing (discoverable
firewall guidance for the no-loop case) is preserved; only the unused invocation
path is removed.

**Resulting shape (carved here, implemented in #448).**

- One invokable skill: `autonomous-loop`. `context-firewall` is de-registered
  (`plugin.json`, engineering README, installed-skills snapshot).
- Two coordinate supporting docs, kept on their orthogonal axes (ADR 0012's own
  deletion-test logic — the two disciplines pass it independently):
  - **`RUNNING-AFK.md`** — unattended-safety axis (guardrails, gate spectrum,
    monitor/stop/resume) **plus the worked backlog example, which keeps the
    per-item brief↔issue reconciliation block**. Reconciliation reconciles a
    *brief against an issue* — a briefed-backlog concern, not a generic firewall
    one — so it stays loop-side rather than polluting the generic doc.
  - **`FIREWALL.md`** — generic, shape-agnostic context-hygiene axis (per-item
    sub-agent, budget checkpoint, compaction). Pointable by any multi-item skill.
  - `SKILL.md` gains a short "per-item hygiene → FIREWALL.md" pointer replacing
    today's `/context-firewall` cross-references.
- The progress-file mechanics, currently documented twice, dedupe to one owner
  (FIREWALL.md owns flush/drop; RUNNING-AFK.md references it).
- `CONTEXT.md` keeps the **firewall** vocabulary entry (the term survives; only
  the skill does not).

**Rejected alternatives.**

- *Affirm ADR 0012 as-is (two standalone skills).* Keeps a trigger for a
  loopless invoker the evidence says doesn't exist, and retains the
  adjacent-trigger collision surface — paying for insurance never claimed.
- *Retire context-firewall in favor of the harness baseline (#446 option c).*
  Deletes steps 1/3/4 (the orchestrator-side discipline the baseline doesn't
  teach) **and** leaves the loopless user with no documented home — fails a #446
  acceptance criterion.
- *Inline-merge the firewall prose into autonomous-loop's `SKILL.md`.* Bloats the
  skill body and destroys the cleanly-pointable generic discipline that
  skill-authoring and non-loop callers depend on. A coordinate supporting doc
  keeps it pointable without a standalone trigger.

**Boundary.** This ADR is the spike's recommendation; it implements nothing.
[#448](https://github.com/dividedby/skills/issues/448) (rewrite via
`/writing-great-skills`) implements the de-registration and the doc re-cut;
[#447](https://github.com/dividedby/skills/issues/447) wires `/flow-pr` as the
per-item close-out. Both were gated on this decision and inherit a **one-skill**
outcome. On ratification, add the `> Superseded by ADR 0033` blockquote to
ADR 0012.
