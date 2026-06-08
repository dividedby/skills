# The improve-codebase-architecture prompt is a fetched-fresh skeleton plus a local repo-context include

[ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)
put the proposal-loop **prompts** on the fetch-fresh rail so one upstream fix
reaches every loop. [ADR 0015](0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)
made the `apply-agent-research` prompt a single portable artifact serving the
host and every Consumer — because that loop's per-repo differences are all
**env-expressible** (`MIRROR_DIR`, `SKILL_DIR`, `SKILLS_SRC`, `PRIVATE_MARKERS`,
`SKILLS_TRACKER_TOKEN`).

`improve-codebase-architecture` does **not** have that property. Its per-repo
differences *are the substance of the prompt* — **what to review** and **which
disciplines to respect** — not incidental wiring:

| | `dividedby/skills` instance | `dividedby/agent-research` instance |
|---|---|---|
| Primary scope | `skills/<bucket>/<name>/` SKILL.md + markdown | `kb_afk/` modules + seams |
| Disciplines | mattpocock cross-plugin links, `plugin.json` | test-first (red→green), one-test-per-module, ADRs binding, `tools/` untested, `sources/` append-only |

You cannot express "review `kb_afk/`, respect red→green, `sources/` is
append-only" in env vars. So the in-tree prompt is the **skills-repo's own
instance**, and `agent-research` correctly **vendors its own**. But that leaves
`agent-research` in exactly the split ADR 0014 names: it already fetches
`harness/cli.py` fresh (the `<output>`/`<body>` publish parser — the #211 drift
class) yet keeps the **whole prompt** local, so if the `<output>`/`<body>`
**schema** ever changes upstream, every vendored arch-review prompt needs a
hand-edit. See [#148](https://github.com/dividedby/skills/issues/148).

## Decision

Split the arch-review prompt into two parts joined by the stub:

1. **A fetched-fresh, scope-free skeleton** at
   `harness/prompts/improve-codebase-architecture.md`. It carries everything
   **shared**: the unattended/publish-seam framing, Task steps 1–6 (the proposal
   discipline), and the full **`<output>`/`<body>` schema + field rules** — but
   with the repo-specifics that today bleed into those steps (`kb_afk/`, "design
   tokens", "name the mirrored test move") **generalized** to repo-agnostic
   phrasing. It contains **no repo scope**.
2. **A local repo-context include** at the conventional path
   **`.github/arch-review-context.md`** — the only vendored part. It carries the
   irreducibly repo-specific substance: primary scope, fallback scope,
   out-of-scope, and the binding disciplines/ADRs (and may add repo-specific emit
   hints). It names its own path so the agent knows it is editable.

The **workflow stub concatenates** them into the system prompt
(`--append-system-prompt "$(cat $HARNESS/prompts/improve-codebase-architecture.md;
printf '\n\n'; cat .github/arch-review-context.md)"`); the skeleton's Scope
section forward-references the appended **Repo context** block. The skills repo's
own arch-review becomes just another consumer of the skeleton with its own
include (reading the skeleton from its `ref: main` checkout, not a clone).

This restores ADR 0014's single-source property for the lockstep-sensitive parts
while keeping the repo-specific scope local — the content-seam analog of what ADR
0015 did with an env seam.

## Two kinds of "shared", one seam

The split rests on a distinction #148 originally conflated:

- **Lockstep-with-the-parser** — the `<output>`/`<body>` schema + field rules.
  If these drift from `harness/cli.py publish`, the run **breaks**. This is the
  load-bearing reason this prompt must ride ADR 0014's rail.
- **Shared editorial discipline** — Task steps 2–6 (map-before-judge,
  research-before-proposing, observed-vs-anticipated, concrete before/after, one
  recommendation, prescription-proportional, skip-beats-forcing). Consistent
  **by preference**; a repo varying them breaks nothing mechanically.

The skeleton single-sources **both**, but only the first is why the rail is
mandatory here. The second rides along for consistency, generalized so a repo
adds its own discipline back through the include rather than forking the prose.

## Why a content seam, not env (contrast ADR 0015)

`apply-agent-research`'s variation is **wiring** — paths, tokens, markers —
expressible as env the prompt reads. `improve-codebase-architecture`'s variation
is **content** — what to review and which disciplines bind — which has no env
representation. So the seam is a vendored **content file**, not an env contract.

## Why a fixed conventional path, not an `ARCH_CONTEXT_FILE` env var

#148 proposed an `ARCH_CONTEXT_FILE` env var "mirroring ADR 0015." But 0015
needed env because the **agent** read those paths (and one was a role
discriminator). Here the **stub** concatenates the include, so the agent never
consumes a path — an env var would document a variable nothing reads. The
convention `.github/arch-review-context.md` is the contract; a stub may `cat`
elsewhere since the path is purely stub-local.

## Consequences

- **Missing include hard-fails.** Scope is load-bearing: a skeleton with no scope
  reviews blindly — the "reaching for something to file" failure the prompt
  warns against. The stub `test -f`s the include and fails the run if absent,
  like the existing `test -f …/SKILL.md` gate. Adopting the loop *requires*
  shipping the include. (This removes today's graceful degradation when a repo
  lacks `CONTEXT.md`; the trade is intentional.)
- **The self-edit affordance points at the local include only.** The agent may
  propose edits to its in-repo files including `.github/arch-review-context.md`,
  but **not** the fetched skeleton — it is upstream-owned and this loop has no
  cross-repo channel to file against `dividedby/skills`, so a proposal to edit it
  would land un-actionable in the consumer's own tracker.
- **The residual lockstep risk closes.** A `<output>`/`<body>` schema change now
  reaches every arch-review loop on its next run; no vendored prompt to hand-edit.
- **Onboarding ships one local file.** `arch-review-setup.md` documents the
  context-include contract and the stub↔skeleton interface.
- **The skills host self-review is unchanged** — its scope + ecosystem (mattpocock
  cross-plugin) context move verbatim into its own `.github/arch-review-context.md`.
- `harness/cli.py publish` is unchanged: the schema is stable by construction.

## Rejected alternatives

- **Full env-parametrization (à la ADR 0015).** The variation isn't
  env-expressible — scope and disciplines are prose, not paths/tokens.
- **Leave it fully vendored (status quo).** Keeps the schema-lockstep risk ADR
  0014 exists to delete; `agent-research` stays split across two update rails.
- **An `ARCH_CONTEXT_FILE` env var.** A documented variable for a value nothing
  reads, since the stub does the concatenation (see above).
