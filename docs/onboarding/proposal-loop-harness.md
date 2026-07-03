# The proposal-loop harness

A **[proposal loop](../../CONTEXT.md)** is a scheduled, skill-driven GitHub
Actions workflow that reads some input, then **proposes via labeled issues and
never applies** — no commits, edits, or PRs. Four of this owner's proposal
loops share this harness's `cli.py`; only the *skill*, the *input*, and the
*label* differ. Three vendor a thin caller stub per consumer repo (below);
the fourth — `changelog-health` — is centralized and host-only, with no
per-repo setup doc:

- **[`consumer-setup.md`](./consumer-setup.md)** — `apply-agent-research`
  (KB + governance docs → agent-meta improvements). The rich one: adds the
  knowledge-mirror input and the cross-repo `skill-request` / `skill-promotion`
  channels. Files through the skill's own guarded `cli.py`, so it uses only the
  harness's shared `digest` (not the `publish` seam).
- **[`arch-review-setup.md`](./arch-review-setup.md)** —
  `improve-codebase-architecture` (the codebase → refactor proposals). The
  leanest member: no extra input, no cross-repo channels — harness + a skill,
  plus the harness `publish` seam (the agent emits a structured `<output>`/`<body>`;
  the harness files the one capped issue) so the per-run cap lives in code.
- **[`staleness-setup.md`](./staleness-setup.md)** — `staleness-audit`
  (the repo's toolchain pins → a ranked staleness report, complementing
  Dependabot). Monthly, and like arch-review uses the `publish` seam. Distinctive
  in two ways: it needs **`WebSearch`/`WebFetch`** for upstream latest/EOL
  validation, and its skill *can* mutate (a verify-gated apply station) yet the
  loop runs it **report-only** — no `Edit`/`Write`, so the cron never applies.

This file is the **common skeleton** the three vendored loops reference
(`changelog-health` needs no separate setup doc — its workflow file is
self-contained). Read it first, then the loop-specific doc.

## The load-bearing decisions

- **Propose via issues; a human decides** ([ADR 0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md)).
  The loop's *only* mutation is filing issues. `permissions: contents: read,
  issues: write`. No `Edit`/`Write` tools, no commits, no PRs. This producer/decider
  split is what makes unattended operation safe.
- **Fetch the skill fresh each run; never vendor it** ([ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
  `git clone --depth 1` the skill's source repo and `cp -R` the skill into
  `~/.claude/skills/` at the start of every run. A committed copy silently drifts;
  for a security-relevant skill (a leak guard) that drift is the worst failure
  mode. The skill is used **by file path**, so any readable location works.
- **Vendor only the thin caller stub; everything load-bearing lives in the reusable body** ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md), [ADR 0029](../adr/0029-apply-agent-research-joins-the-reusable-body-rail.md)).
  All three vendored loops run as GitHub Actions `workflow_call` reusable
  bodies in `dividedby/skills` (#382) — `changelog-health` doesn't follow this
  pattern; it's a single centralized workflow in the host repo, no vendoring
  needed. The drift-prone logic — the `stream-json` cost
  scrape, the `<output>`/`<body>` publish seam, the `claude -p` invocation with
  scoped `--allowedTools`, pinned `--model`, `--max-budget-usd`, the first-Monday
  gate, and the loop prompts — lives in the `*-reusable.yml` bodies and resolves
  fresh from `dividedby/skills` on every run. Each repo commits only the **thin
  caller stub**: `on:` (cron schedule), `permissions:`, `uses:`, and `secrets:`
  (plus loop-specific `with:` inputs for `apply-agent-research`). The home repo
  uses a local `./` ref (canary, runs latest body); consumers pin `@claude-loops-v1`.
  One fix in a reusable body reaches every caller on its next run, killing the
  #117/#211 drift class.

## The thin caller stub

Each loop's workflow file in any repo is just `on:` + `permissions:` + `uses:` +
`secrets:` (plus `apply-agent-research`'s `with:` inputs). Everything
load-bearing — the `claude -p` invocation, scoped `--allowedTools`, pinned
`--model` and `--max-budget-usd`, cron gate logic, `concurrency`, the harness
clone, the cost-ledger `digest` step — lives in the corresponding
`*-reusable.yml` body in `dividedby/skills` and is inherited automatically by
every caller. This is the canonical thin-stub form; per-loop docs cross-link
here rather than duplicating it.

The home repo (`dividedby/skills`) calls each body via a local `./` ref (the
canary — always running the latest body before consumers pin). Consumer repos
vendor a thin caller that pins `@claude-loops-v1`; a tag move is the single
gated rollout that updates the body for all consumers at once.

```yaml
name: <Loop Name>

# Thin caller stub (#382). Body lives in <loop-name>-reusable.yml.
# Home repo: local `./` ref runs its own latest body (the canary).
# Consumers: pin @claude-loops-v1 — a tag move is the single gated rollout.

on:
  schedule:
    - cron: "<off-the-hour slot>"   # derive via hash-stagger (see below); gate
                                    # logic (e.g. first-Monday) lives in the body
  workflow_dispatch:

jobs:
  run:
    # The calling job must grant the token scopes the reusable body needs: a
    # called workflow can't be granted more than the caller holds, and the repo
    # default is read-only — without this the body's `issues: write` request
    # exceeds the caller's grant and the run startup-fails.
    permissions:
      contents: read
      issues: write
    # Home-repo form (canary — calls local body at HEAD):
    uses: ./.github/workflows/<loop-name>-reusable.yml
    # Consumer form (pins a stable tag):
    # uses: dividedby/skills/.github/workflows/<loop-name>-reusable.yml@claude-loops-v1
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    # apply-agent-research consumers add with: inputs (see consumer-setup.md):
    # with:
    #   is-knowledge-source: false
    #   private-markers: ""
    #   max-budget-usd: "4.00"
    # secrets:  # (in addition to CLAUDE_CODE_OAUTH_TOKEN above)
    #   ISSUES_TOKEN: ${{ secrets.ISSUES_TOKEN }}
```

The cron schedule is the **only per-consumer customization** in the thin caller
stub — derive it with the hash-stagger rule in the
[Conventions section](#conventions-in-the-reusable-body) below. All other
configuration is inherited from the reusable body.

## The reusable body ↔ harness interface contract

This is the **stable, versioned** seam between the `*-reusable.yml` bodies and
the fetched-fresh harness ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
The drift-prone logic no longer lives on this surface, so the contract changes
rarely; when it does, it is a **manual rollout** to update the reusable bodies.

- **`harness/prompts/<loop>.md`** — the loop's system prompt, `cat`'d by the
  reusable body. Two reasons a prompt rides the harness rail rather than being
  vendored per repo: for a **publish-seam** loop (arch-review, staleness) the
  prompt and the `publish` parser share the `<output>`/`<body>` contract and
  version together; for **`apply-agent-research`** the prompt is instead
  **parametrized by env** and serves both the host and every Consumer from one
  source, so the rail preserves "one fix reaches every loop"
  ([ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)).
  **`improve-codebase-architecture` is a hybrid:** the harness prompt is only the
  **scope-free skeleton**, and the reusable body concatenates it with a vendored
  local **Repo-context include** (`.github/arch-review-context.md`, hard-failed
  with `test -f`) because that loop's per-repo variation is *content* — review
  scope and binding disciplines — with no env representation
  ([ADR 0016](../adr/0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md),
  [`arch-review-setup.md`](./arch-review-setup.md)). The arch-review skeleton's
  body-drafting rules (Step 5) include a **Design-tension block** — competing-constraint
  analysis naming 2–3 candidate-specific tensions and a triage decision statement —
  for human review before implementation starts (ADR 0020, second amendment).
  That prompt reads its wiring from the env the reusable body exports — `MIRROR_DIR`,
  `SKILL_DIR`, `SKILLS_SRC`, `PRIVATE_MARKERS`, and `ISSUES_TOKEN` (the cross-repo
  credential; mode is determined by the explicit `is-tracker-host` input, not token
  presence — ADR 0032). The exact contract and what a Consumer's `with:` inputs
  must cover is in [`consumer-setup.md`](./consumer-setup.md).
- **`python3 harness/cli.py digest --jsonl F --result-out F --cost-out F`** —
  every loop. Reduces the `stream-json` JSONL to the last result event's `.result`
  (whole, multi-line preserved) and the `total_cost_usd=…  duration_ms=…
  num_turns=…` ledger line. A failed run (no result event, or `result.is_error:
  true`) prepends `error=no-result` / `error=is_error` to that line; a clean run's
  line is unchanged. Best-effort (exit 0 even with no result event); run it
  `if: always()` so cost is captured on a failed agent run too.
- **`python3 harness/cli.py publish --log F --label L [--label-color H]
  [--label-description T] [--cost-file F] [--heading H] [--repo R]`** —
  publish-seam loops only. Parses the agent's `<output>` JSON + raw `<body-N>`
  blocks (or the legacy single `<body>`), files ≤1 issue under `L` (cap in code —
  [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)), writes
  the rich step summary, and emits `issue_url` / `issue_urls` to
  `$GITHUB_OUTPUT`. **Recovers loudly, then fails loud** — on a malformed
  `<output>` it applies a deterministic one-shot JSON repair, then salvages any
  `<body-N>` blocks under reconstructed titles (each degradation emits a
  `::warning::`); it exits 1 only when nothing is salvageable (no output and no
  bodies, or unknown status) — [ADR 0025](../adr/0025-publish-seam-recovers-malformed-output-loudly-before-failing.md).
  Pair it with an `if: failure()` summarise step that surfaces the raw log.
  Reads `$GH_REPO` / `$GITHUB_STEP_SUMMARY` / `$GITHUB_OUTPUT` from the Actions env.

- **`python3 harness/cli.py fetch-rubric --out-dir DIR`** —
  arch-review only. Downloads the depth rubric from `mattpocock/skills@main`
  codebase-design paths into `DIR/depth-LANGUAGE.md` and `DIR/depth-DEEPENING.md`.
  **Hard-fails (exit 1)** on any network or HTTP error per ADR 0020(c) — an
  unattended run with a missing rubric would produce unsound depth proposals. The
  two upstream URLs live once in `harness/cli.py`; a future upstream path change is
  a one-line fix there, picked up by every consumer on next run. Float policy: no
  SHA pin — tracks `mattpocock/skills@main` automatically per ADR 0020(b). Supply-chain
  implication: third-party changes enter unattended runs unreviewed; pin a SHA in
  your own thin caller stub's `uses:` ref if that tradeoff is unacceptable.

The `publish` parser is unit-tested (`harness/tests/`, gated by
`.github/workflows/gate.yml`) precisely because it is the #117 drift
surface — a tested stdlib parser replaces the brittle `sed`/`jq` hand-escaping
that caused it ([ADR 0004](../adr/0004-runbook-helpers-are-python-stdlib.md)).

## Conventions in the reusable body

The `*-reusable.yml` bodies implement all load-bearing conventions. A consumer
vendoring the thin caller stub inherits them automatically — **do not re-author
cron gate logic, `concurrency`, `--allowedTools`, `--model`, `--max-budget-usd`,
or the cost-ledger `digest` step in the thin caller stub.** Authors adding or
modifying a reusable body are responsible for these:

- **Off-the-hour cron + stateless hash-stagger.** The cron **schedule**
  (`on.schedule.cron`) lives in each caller stub (the one per-consumer
  customization); all gate logic (e.g. the first-Monday check) lives in the
  reusable body. Schedule off the top of the hour and pick a slot **after** any
  upstream that produces this loop's input (a Consumer runs after the knowledge
  mirror's synthesis push). To avoid hand-coordinating slots as more repos
  onboard, derive the minute/hour from the job's own identity — a **stateless hash
  slot** (agent-research [ADR 0022](https://github.com/dividedby/agent-research/blob/main/docs/adr/0022-consumer-workflows-self-stagger-by-hash.md)):

  ```python
  offset = int(sha1(f"{repo}/{workflow}".encode()).hexdigest()[:6], 16)
  minute = offset % 60
  hour   = WINDOW_START + (offset // 60) % WINDOW_HOURS
  ```

  The hash picks only the **minute and hour within the assigned day**; the
  day/frequency stays as the cadence dictates. The shared **Mon/Wed/Sat consumer
  window** (where `apply` / `improve-codebase-architecture` across all repos consume
  the same run's synthesis) is `WINDOW_START=0`, `WINDOW_HOURS=4` on
  **Mon/Wed/Sat UTC** (`* * 1,3,6`) — the `* * 1,3,6` mask avoids the UTC-midnight
  day-of-week straddle a CT-evening window would hit. **First-Monday cadence**
  (e.g. staleness-review): POSIX cron can't express it, so the stub fires every
  Monday and the reusable body gates on `[ "$(date -u +%-d)" -le 7 ]`.
- **`concurrency` with `cancel-in-progress: false`** so a long run is never
  killed mid-flight by the next tick.
- **Scoped `--allowedTools`, plus `--disallowedTools` for the filing tool.** Grant
  only what the loop needs (`Read Grep Glob`, `Bash(gh:*) Bash(git:*)`, etc.).
  *Exception:* if the skill invokes the budgeted proposal **gate** via a pipe
  (`echo '<json>' | python3 cli.py gate`), `Bash` must stay **unscoped** — a scoped
  `Bash(python3:*)` blocks a command that starts with `echo`. The no-commits
  invariant then rests on `contents: read` + the absence of `Edit`/`Write`, not on
  Bash scoping. See agent-research#127. *For a loop that files through a guarded
  shim* (`apply-agent-research`'s `cli.py file` / `cli.py comment`, which sanitize
  then `gh`-write only on ALLOW), additionally set `--disallowedTools "Bash(gh issue
  create:*) Bash(gh issue comment:*)"` so the agent cannot bypass the guard with a
  direct write. A publish-seam loop (arch-review) instead scopes `gh` to read-only
  subcommands so the agent cannot file at all — the harness `publish` step is the
  sole filing path.
- **Emit the cost-ledger line.** `harness/cli.py digest` writes the single
  `total_cost_usd=<…>  duration_ms=<…>  num_turns=<…>` line that a cross-repo
  **cost hub** (`dividedby/agent-research`) scrapes from each participating repo's
  run logs to project monthly spend. Every proposal loop must emit it — it is part
  of the reusable body, not a per-loop add-on. Use `--output-format stream-json
  --verbose` (not plain `json`, which buffers and goes dark on a hang) so the final
  `result` event lands in the log before `claude` exits; cost is then captured even
  on a failed run. The hub reads logs via a least-privilege `Actions: Read` PAT it
  holds — see the onboarding doc's manual steps for the token the human must mint.
- **Pin `--model` — default `claude-sonnet-5`.** Always pass an explicit
  `--model`, using an exact model ID rather than a floating alias like `sonnet`;
  never rely on the `CLAUDE_CODE_OAUTH_TOKEN` default. An unpinned loop runs
  whatever the subscription default happens to be, which can silently flip (e.g.
  to opus) and blow the budget without a code change, and makes the cost hub's
  projection unreliable (its per-run repricing assumes a known model). A floating
  alias has the same staleness class in miniature: it silently inherits the next
  release of that tier, untested, in an unattended loop — bump the pin only after
  testing the prompts against the new model (#180). **Sonnet is the
  default choice** for these propose-only loops — the #161 cost/quality benchmark
  found model is the cost lever but barely moves output quality for synthesis/
  apply/audit-shaped work; reserve `opus` for a loop that is *demonstrably*
  quality-critical (in the corpus, only agent-research's downstream-read
  `synthesize` keeps opus). This pairs with the cost-ledger line above: pinned model
  + emitted cost is what keeps an onboarded loop inside the hub's $100/mo Agent SDK
  credit budget (`dividedby/agent-research` `docs/cost-tracking.md`, ADR 0020 cost
  amendment).

## Required secrets

- **`CLAUDE_CODE_OAUTH_TOKEN`** — so the run can authenticate. A repo already
  running Claude in Actions has this; reuse it.
- Any **loop-specific** token (e.g. a Consumer's `ISSUES_TOKEN` for
  cross-repo writes) — see that loop's doc.
