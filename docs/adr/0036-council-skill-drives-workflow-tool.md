# Skills may drive the built-in Workflow tool; `/council` is the reference pattern

> **Status: Accepted** — ratified via PR [#492](https://github.com/dividedby/skills/pull/492) opening. Records the `/council` skill design (issue [#492](https://github.com/dividedby/skills/issues/492)).

## Disambiguation: two things called "workflow" in this repo

This ADR is about the **built-in `Workflow` tool** — the Claude Agent SDK
orchestration primitive that exposes `parallel()`, `pipeline()`, and `agent()`
calls inside a single interactive session. A skill invokes it by telling the
model to drive those primitives in its execution of a task.

This is **not** the sense of "workflow" used in:

- [`docs/agents/workflow-authoring.md`](../agents/workflow-authoring.md) —
  which documents scheduled **GitHub Actions `claude -p` cron loops** (the
  `apply-agent-research`, `changelog-health`, and similar proposal loops that
  run headless on a cron schedule, emit `total_cost_usd`, and must be enrolled
  in the cross-repo `COST_SURFACE`).
- [`skills/config/workflow-onboarding/SKILL.md`](../../skills/config/workflow-onboarding/SKILL.md) —
  which onboards a repo into those same **scheduled proposal loops** (installs
  LOOP/NETWORK labels, seeds `installed-skills.md`).

The two senses do not overlap. The scheduled `claude -p` loops are CI pipeline
concerns; the built-in Workflow tool is a session-time orchestration primitive.
Future ADRs, skills, and docs should use **"Workflow tool"** to mean the latter
and **"proposal loop"** or **"scheduled workflow"** to mean the former.

## Context

The built-in Workflow tool provides three primitives for multi-agent
orchestration within a session:

- `parallel()` — fan-out: multiple agents run simultaneously on the same input
- `pipeline()` — sequence: each agent's output feeds the next
- `agent()` — a single sub-agent with a model, effort level, and schema

Prior to `/council`, no skill in this repo drove the Workflow tool. All
existing skills either ran as a single model pass or called sub-skills
sequentially in prose (e.g., `/software-design` calls `/codebase-design` and
`/domain-modeling`). The sub-skill calls in those skills are instruction-level
—"invoke X and hand it Y"— not Workflow-tool `agent()` calls.

Issue [#492](https://github.com/dividedby/skills/issues/492) proposed a blind
multi-persona panel skill (`/council`) whose core value depends on Round 1
isolation (no seat sees another's output) and a dedicated chair synthesis pass.
That structure is exactly what `parallel()` + a sequential `agent()` provides.
Implementing it as prose instructions alone would be brittle: there is no
instruction-level mechanism to enforce blind isolation across seats.

## Decision

Skills in this repo **may drive the built-in Workflow tool** when the
task structure genuinely requires parallel or pipeline orchestration that
instruction-level prose cannot enforce.

`/council` is the reference pattern. Its three-round structure (blind
`parallel()` in Round 1, peer-rank `parallel()` in Round 2, chair `agent()`
synthesis in Round 3) is the archetypal use case:

- Round 1 isolation is an **integrity property** — a seat that sees a peer's
  output in Round 1 produces a correlated, not independent, evaluation. Only
  `parallel()` with per-seat sandboxing can enforce this.
- The chair synthesis requires a **dedicated agent** that reads all prior
  output and has a schema-enforced output contract. A plain prose step at the
  end of a sequential skill cannot enforce the four-block output contract at
  the session level.

**Amendment (#531): Round 2 isolation is dual, not just label-stripped.**
Anonymizing seat labels in Round 2 removes authorship bias, but a peer's full
response still carries the reasoning trace that produced it, which biases a
cross-reviewer toward agreement — a visible chain of reasoning reads as
supporting evidence even when the conclusion is wrong. Round 2 redistribution
now strips the trace too: each seat receives only the structured
verdict/finding/evidence, never the derivation, and each seat's prompt states
that it weighs peer arguments as unvetted — never pre-confirmed by an earlier
pass. `repo-audit`'s Round 2 (also Workflow-tool-driven per this ADR) carries
the same tightening.

Authoring rules for skills that drive the Workflow tool:

1. **Principle-level only.** The SKILL.md contains an *illustrative sketch*,
   not a literal runnable script ([ADR 0002](./0002-design-skills-prescribe-at-principle-level.md)).
   The sketch shows the orchestration *shape*; actual prompts and schemas are
   seat-specific and tuned at invocation time.
2. **Workflow tool, not reimplementation.** Do not reimplement parallel
   execution or schema enforcement in skill prose. That is the Workflow tool's
   job. The skill's prose contributes the selector, the roster, the round
   structure, and the output contract — not the execution engine.
3. **Schema at the output boundary.** The chair/final agent in any
   Workflow-tool skill should enforce the output contract via a schema binding
   so partial output is a Workflow error, not a silently incomplete response.
4. **No cost surface change for skills.** Skills are user-invoked tools, not
   unattended cron loops. A Workflow-tool skill does not need `--max-budget-usd`
   backstops, `total_cost_usd` emission, or `COST_SURFACE` enrollment — those
   rules apply to the scheduled `claude -p` loops governed by
   `docs/agents/workflow-authoring.md`.

## Consequences

- `/council` becomes the first skill in this repo to drive the Workflow tool,
  and the canonical example for skills that need parallel fan-out with strict
  isolation.
- Any future skill proposing to drive `parallel()`, `pipeline()`, or `agent()`
  should cite this ADR, follow its four authoring rules, and note what
  structural property the Workflow tool enforces that prose cannot.
- Skills that call sub-skills sequentially in prose (like `/software-design`)
  are **not** Workflow-tool skills — they remain instruction-level orchestration
  wrappers. The distinction is whether Workflow-tool primitives are needed to
  enforce an integrity property (isolation, schema, parallel timing).
- The "workflow" disambiguation above should be applied when editing or
  reviewing docs that use the word — prefer "Workflow tool" vs "proposal loop"
  / "scheduled workflow" to avoid the ambiguity this ADR names.
