# The proposal-loop harness is fetched fresh; only the workflow envelope is vendored

[ADR 0008](0008-consumers-fetch-the-skill-fresh-not-vendored.md) de-vendored the
*skill*, but the proposal-loop **publish seam** — the shell that parses the
agent's `<output>`/`<body>` blocks, files the one capped issue, and scrapes the
`total_cost_usd=…` ledger line — stayed committed in each repo's workflow `.yml`.
That copy drifts: the same invalid-JSON fix had to be hand-applied twice,
independently, in [#119](https://github.com/dividedby/skills/pull/119) and
`dividedby/agent-research#211`. Every future harness fix would pay that tax once
per onboarded repo.

## Decision

All drift-prone harness logic moves onto the **same fetch-fresh rail** as the
skill, living in `dividedby/skills` `harness/`:

- the **publish CLI**, rewritten as a tested Python stdlib module (the #117 root
  cause was brittle `sed`/`jq` hand-escaping of JSON — a tested parser kills that
  class; this clears the [ADR 0004](0004-runbook-helpers-are-python-stdlib.md)
  "helpers are stdlib once they earn tests" bar);
- the **loop prompts**, because the prompt and the publish CLI share the
  `<output>`/`<body>` contract and must version in lockstep — leaving the prompt
  vendored while fetching the CLI would split one contract across two update rails.

Each repo commits only the **workflow envelope** (the "stub"): `on:` cron,
`permissions:`, secret/token names, `--allowedTools`/`--disallowedTools` scoping,
and a thin clone-and-invoke body (`git clone dividedby/skills` → `python3
<clone>/harness/cli.py publish`, prompt `cat` from the clone). The envelope is
the part that *must* be committed — GitHub Actions reads it from the default
branch — and is also exactly the intentional per-repo customization a reconciler
should never touch.

The stub ↔ harness **interface** (CLI subcommands, expected paths) is a
deliberately stable contract, documented in
[`docs/onboarding/proposal-loop-harness.md`](../onboarding/proposal-loop-harness.md)
and versioned conservatively.

## Consequences

- Kills the #117/#211 drift class: one fix in `harness/` reaches every loop on its
  next run.
- Makes a standalone run-book-wiring **reconciler unnecessary**
  ([#120](https://github.com/dividedby/skills/issues/120) collapses into this ADR):
  there is almost nothing left to reconcile, and what remains splits cleanly —
  intentional per-repo settings (leave alone) and **pinned-action currency**
  (`actions/checkout@v6` etc.), which is the staleness loop's
  ([#118](https://github.com/dividedby/skills/issues/118)) job, not this one's.
- **Extends 0008's accepted trust boundary** from skill code to harness shell: a
  scheduled run now auto-executes whatever harness shell is at `dividedby/skills`
  HEAD with the consumer's tokens. Same call as 0008, one layer out — accepted for
  the same reasons (same maintainer, Actions never passes secrets to fork-PR runs).
- Introduces the stub ↔ harness interface contract. A breaking interface change is
  a manual rollout across the ~3 owned repos — rare by construction, since the
  drift-prone logic no longer lives on this surface.

## Rejected alternative

Keep the wiring vendored and build an update/reconcile mode that diffs installed
workflow + prompt against a canonical template and PRs the delta (the original
#120 framing). Rejected: it builds a cross-repo diff/PR machine to *manage* drift
that this ADR *deletes at the source*, and it would still have to special-case the
intentional per-repo envelope to avoid clobbering it — the same over-engineering
0008 rejected for its pinned-SHA variant.
