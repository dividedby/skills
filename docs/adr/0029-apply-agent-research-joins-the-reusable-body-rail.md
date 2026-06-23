# apply-agent-research joins the reusable-body rail (ADR 0014 carve-out lifted)

[ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)
moved the proposal-loop harness onto the fetch-fresh rail but **carved out**
`apply-agent-research`: its body "forks on mode (host/consumer/producer), where no
single shared body exists to host," so it stayed a full-copy envelope vendored in
all 5 repos, guarded only by a drift report. Spike #404 disproved that premise.

## Decision

`apply-agent-research` collapses to one `workflow_call` reusable body in
`dividedby/skills` (`.github/workflows/apply-agent-research-reusable.yml`) plus a
thin caller per repo — exactly the pattern ADR 0014 already endorsed for the
knob-only loops (arch-review, staleness-review).

The three "modes" are **env-wiring, not body forks** (#404), along two orthogonal
axes that never interact:

- **Mode = `SKILLS_TRACKER_TOKEN` presence** ([ADR 0015](0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)):
  unset → host, set → consumer (gates cross-repo filing only).
- **`is-knowledge-source`** (`workflow_call` input, default `false`) gates only the
  knowledge-mirror clone: the producer (`agent-research`) reads its native
  `knowledge/`; the host and every consumer clone the public
  `dividedby/agent-research-knowledge` mirror.

So one body with two conditional points — a clone gate (`if: ${{ !inputs.is-knowledge-source }}`)
and a `MIRROR_DIR` expression — serves all three modes. The body is hardened to the
form #394 applied to the other two loops: SHA-pinned `actions/checkout` (no `ref:`),
scoped `--allowedTools` (no bare `Bash(...:*)`), `--disallowedTools` on
`gh issue create`/`comment`, **no `--permission-mode acceptEdits`** (the loop writes
nothing to the tree — it files via the guarded `cli.py` shim), pinned `--model`,
`--max-budget-usd`, and an `if: always()` digest reading `harness/cli.py` from the
fresh `dividedby/skills` clone. A single unconditional fresh clone of
`dividedby/skills` supplies the harness, the skill lib (`SKILL_DIR`), and the
published-skill catalog (`SKILLS_SRC`) for all modes — the host no longer reads
these from its own checkout, matching how the other two reusable bodies already run.

## Consequences

- The "remaining vendored surface" ADR 0014 left (5 full-copy envelopes + per-consumer
  thin callers) collapses to one reusable body + 5 thin callers.
  `tools/check_workflow_drift.py` moves its `apply-agent-research` anchors from the
  full-envelope set to a reusable-body set (`APPLY_BODY_PATH`: SHA-pin present;
  `acceptEdits` + bare wildcards forbidden) and treats every caller — including
  skills' own canary — as a thin local-`./` caller.
- **A broken body now breaks all 5 loops at once.** Mitigation: the skills canary
  (`workflow_dispatch`, host mode) must run green before the `@claude-loops-v1` tag is
  moved; consumers pin the tag, not `main`.
- No change to the trust boundary beyond what ADR 0014/0008 already accepted.

## Rejected alternatives

- **Keep the carve-out.** Its premise (mode ⇒ body fork) was the whole justification;
  #404 falsified it. A full-copy envelope per repo re-incurs the #117/#211 drift tax
  that ADR 0014 exists to kill.
- **Add a `knowledge-mirror` input.** One producer, one public mirror — the slug is
  hardcoded in the body. Add the input only if a second knowledge source ever appears.
