# Inbox/Roadmap bodies are human-facing; agent operating instructions live in the skill/docs, discoverable via a breadcrumb

Each Idea Inbox and Roadmap issue body grew into a **monolith** holding three
different things at once: the human-scannable backlog/ideas, the agent operating
instructions (how to drain the inbox, how to reconcile the roadmap), and archived
history. That conflation costs all three readers. An agent loads the **whole raw
body** every time it acts — token bloat that scales with history, not with the work
in front of it (the moodreader roadmap reached 98.6KB). A human who just wants
"what's next" reads **past** the `How to use this doc`, `Self-update protocol`, and
embedded `🤖 operating instructions` blocks to reach anything actionable. And the
instructions, duplicated between the ISSUE_TEMPLATE and the live body, **drift** —
moodreader's template drain protocol diverged from the protocol in its live issue
body.

## Decision

Split the monolith along a **progressive-disclosure** boundary: the body is the
human-facing surface, the instructions live once in the skill/docs, and agents
rediscover them by entering through the skill (backstopped by a hidden breadcrumb).

1. **Issue bodies are human-facing.** The Roadmap body is a read-only-mirror banner
   + a one-line `## Burn-down` + the `## Census` + a single consolidated `## Legend`.
   The Idea Inbox body is the live `## Ideas` list + a collapsed `✅ Actioned`
   rolling window. **No agent operating instructions live in either body** — the
   `How to use this doc`, `Self-update protocol`, and embedded `🤖 operating
   instructions` blocks are removed.
2. **Agent operating instructions live in exactly one canonical place each.**
   Roadmap reconcile lives in `skills/engineering/roadmap/SKILL.md`; inbox drain
   lives in a new `docs/agents/idea-inbox.md`. One source per protocol — this single
   source is what **kills the template/body drift**: there is no second copy to
   diverge from.
3. **Discovery is progressive.** An agent acts via **skill-entry**: invoking
   `/roadmap` self-loads the reconcile protocol, and drain stays a convention that
   points at `docs/agents/idea-inbox.md`. That is backstopped by a hidden
   HTML-comment **breadcrumb** at the top of each body, of the form
   `<!-- agent-protocol: reconcile=/roadmap; drain=docs/agents/idea-inbox.md -->`
   — invisible in the rendered GitHub view, an explicit path for an agent that reads
   the raw body **without** entering via the skill. The concrete breadcrumb schema
   string is specified once in SKILL.md (issue #228), not in this ADR.

## Why this is consistent with 0020 / 0021 / 0023

- **0020 (working-tree doc, mirrored read-only).** The mirror stays a **faithful
  render** of the doc; this ADR only changes *what the doc contains* (human-facing
  sections, breadcrumb, no instructions), not who renders it. `render()` is
  untouched, so the glance-from-web property is preserved.
- **0021 (inbox vs roadmap — everything registers in the roadmap).**
  **Registration is unchanged.** Intake stays a convention; an idea still enters the
  Inbox and a filing still registers in the census. This ADR moves the *drain
  instructions* out of the body, not the intake contract.
- **0023 (census is an execution view, GitHub/git is the archive).** This **extends
  0023's execution-view intent**: 0023 declared the census an execution view rather
  than an archive; this ADR makes the *whole body* a human-facing execution surface,
  with the agent protocol and the archive both pushed off it.

## Rejected alternatives

- **Keep instructions inline but wrap them in `<details>`.** No token win: the agent
  still loads the **raw** body, and a collapsed `<details>` is collapsed only in the
  rendered view, not in the raw text an agent reads. Rejected — it solves the human
  readability complaint but not the bloat or drift.
- **Promote inbox drain to its own skill.** Intake stays a **convention** (ADR
  0021), and drain is **rare and human-initiated** — a dedicated skill is ceremony
  for a path that doesn't run on a cadence. The canonical doc
  (`docs/agents/idea-inbox.md`) is the single source without the skill overhead.
  Rejected.

## Consequences

- This **supersedes** the embedded `How to use this doc` + `Self-update protocol`
  sections in `templates/roadmap.md`, and the embedded operating-instructions in the
  inbox `ISSUE_TEMPLATE` and inbox body. Those are removed in their respective
  slices (#228/#229); the template and ISSUE_TEMPLATE become thin seeds that point
  at the canonical SKILL.md / `docs/agents/idea-inbox.md`.
- The breadcrumb is the **only** machine-readable affordance left in the body — an
  agent that bypasses the skill has exactly one documented path to its protocol, and
  the schema for that path is owned by SKILL.md (#228), not duplicated per ADR.
