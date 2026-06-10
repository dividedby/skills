# The proposal-loop harness

A **[proposal loop](../../CONTEXT.md)** is a scheduled, skill-driven GitHub
Actions workflow that reads some input, then **proposes via labeled issues and
never applies** — no commits, edits, or PRs. All three of this owner's proposal
loops share this harness; only the *skill*, the *input*, and the *label* differ:

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

This file is the **common skeleton** all three reference. Read it first, then the
loop-specific doc.

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
- **Fetch the harness fresh too; vendor only the envelope** ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
  The drift-prone harness logic — the `stream-json` cost scrape and the
  `<output>`/`<body>` publish seam, plus the loop prompts — lives in
  `dividedby/skills` `harness/` and is fetched fresh on the same rail as the skill.
  Each repo commits only the thin **workflow envelope** (the "stub"): `on:` cron,
  `permissions:`, token names, tool scoping, and a clone-and-invoke body. One fix
  in `harness/` reaches every loop on its next run, killing the #117/#211 drift
  class (the same invalid-JSON fix had to be hand-applied twice before this).

## Skeleton workflow (the stub)

The stub clones `dividedby/skills` for the harness + the prompt, runs the agent,
and calls `harness/cli.py` for the cost scrape and (for a publish-seam loop) the
filing. **In `dividedby/skills` itself the harness arrives with the `ref: main`
checkout** — the checkout *is* the fresh harness — so its own two workflows skip
the extra clone and call `harness/cli.py` directly. A downstream consumer repo
clones it into a temp dir, shown here:

```yaml
name: <Loop Name>
on:
  schedule:
    - cron: "<off-the-hour slot>"   # see scheduling note
  workflow_dispatch:
jobs:
  <loop-name>:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    concurrency: { group: <loop-name>, cancel-in-progress: false }
    permissions:
      contents: read        # never more
      issues: write
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      GH_REPO: ${{ github.repository }}
      LABEL: source:<provenance>
    steps:
      - uses: actions/checkout@v6
        with: { ref: <default-branch>, fetch-depth: 1 }

      # --- Fetch the harness fresh (ADR 0014) ---
      - name: Install the proposal-loop harness
        run: |
          set -euo pipefail
          git clone --depth 1 https://github.com/dividedby/skills.git "$RUNNER_TEMP/skills"
          echo "HARNESS=$RUNNER_TEMP/skills/harness" >> "$GITHUB_ENV"

      # --- Fetch the skill fresh (ADR 0008) ---
      - name: Install the skill
        run: |
          set -euo pipefail
          mkdir -p ~/.claude/skills
          cp -R "$RUNNER_TEMP/skills/<path-to-skill>" ~/.claude/skills/   # or another repo
          test -f ~/.claude/skills/<skill-name>/SKILL.md
      # If the skill bundles a code guard, run its unit tests here as a HARD GATE
      # and fail the run on failure — never file with a broken guard.

      - name: Run the loop
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
        run: |
          set -euo pipefail
          # stream-json + tee so the final `result` event (carrying total_cost_usd)
          # reaches the log before claude exits — cost is captured even on failure.
          # --model is pinned to an exact model ID (default claude-sonnet-4-6) so
          # cost is deterministic and the cost-hub projection holds — see
          # "Pin --model" below.
          # --max-budget-usd is a per-run spend backstop — size it ~2.5–3× the
          # loop's observed max cost from the ledger so it never trips a healthy
          # run but caps a runaway well below the job's wall-clock timeout.
          claude -p \
            --output-format stream-json --verbose \
            --model claude-sonnet-4-6 \
            --max-budget-usd 3.00 \
            --permission-mode acceptEdits \
            --allowedTools "<scoped to what the loop needs>" \
            --append-system-prompt "$(cat "$HARNESS/prompts/<loop>.md")" \
            "<one-line task pointer to the system prompt>" \
            | tee "$RUNNER_TEMP/agent.jsonl"

      - name: Digest the run (result log + cost ledger)
        if: always()
        run: |
          set -euo pipefail
          python3 "$HARNESS/cli.py" digest \
            --jsonl "$RUNNER_TEMP/agent.jsonl" \
            --result-out "$RUNNER_TEMP/agent.log" \
            --cost-out "$RUNNER_TEMP/agent.cost"

      # --- publish-seam loops only (e.g. arch-review); skip for a loop that
      #     files through the skill's own guarded cli.py ---
      - name: Publish proposal
        run: |
          set -euo pipefail
          python3 "$HARNESS/cli.py" publish \
            --log "$RUNNER_TEMP/agent.log" \
            --label "$LABEL" \
            --label-description "<provenance description>" \
            --cost-file "$RUNNER_TEMP/agent.cost" \
            --heading "<Loop Name>"

      - name: Summarise a failed run
        if: failure()
        run: |
          { echo "## <Loop Name>"; echo; \
            echo "**Cost:** $(cat "$RUNNER_TEMP/agent.cost" 2>/dev/null || echo n/a)"; echo; \
            echo '```'; tail -n 50 "$RUNNER_TEMP/agent.log" 2>/dev/null || echo "(no log)"; \
            echo '```'; } >> "$GITHUB_STEP_SUMMARY"
```

## The stub ↔ harness interface contract

This is the **stable, versioned** seam between the vendored envelope and the
fetched-fresh harness ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
The drift-prone logic no longer lives on this surface, so the contract changes
rarely; when it does, it is a **manual rollout** across the ~3 owned repos.

- **`harness/prompts/<loop>.md`** — the loop's system prompt, `cat` by the stub.
  Two reasons a prompt rides the harness rail rather than being vendored per repo:
  for a **publish-seam** loop (arch-review, staleness) the prompt and the `publish`
  parser share the `<output>`/`<body>` contract and version together; for
  **`apply-agent-research`** the prompt is instead **parametrized by env** and serves
  both the host and every Consumer from one source, so the rail preserves "one fix
  reaches every loop" ([ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)).
  **`improve-codebase-architecture` is a hybrid:** the harness prompt is only the
  **scope-free skeleton**, and the stub concatenates it with a vendored local
  **Repo-context include** (`.github/arch-review-context.md`, hard-failed with
  `test -f`) because that loop's per-repo variation is *content* — review scope and
  binding disciplines — with no env representation
  ([ADR 0016](../adr/0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md),
  [`arch-review-setup.md`](./arch-review-setup.md)).
  That prompt reads its wiring from the env the stub exports — `MIRROR_DIR`,
  `SKILL_DIR`, `SKILLS_SRC`, `PRIVATE_MARKERS`, and `SKILLS_TRACKER_TOKEN` (whose
  presence is the host/consumer role discriminator). The exact contract and what a
  Consumer stub must export is in [`consumer-setup.md`](./consumer-setup.md).
- **`python3 harness/cli.py digest --jsonl F --result-out F --cost-out F`** —
  every loop. Reduces the `stream-json` JSONL to the last result event's `.result`
  (whole, multi-line preserved) and the `total_cost_usd=…  duration_ms=…
  num_turns=…` ledger line. Best-effort (exit 0 even with no result event); run it
  `if: always()` so cost is captured on a failed agent run too.
- **`python3 harness/cli.py publish --log F --label L [--label-color H]
  [--label-description T] [--cost-file F] [--heading H] [--repo R]`** —
  publish-seam loops only. Parses the agent's `<output>` JSON + raw `<body-N>`
  blocks (or the legacy single `<body>`), files ≤5 issues under `L` (cap in code —
  [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)), writes
  the rich step summary, and emits `issue_url` / `issue_urls` to
  `$GITHUB_OUTPUT`. **Fails loudly (exit 1)** on a missing/garbled/unknown-status
  block — pair it with an `if: failure()` summarise step that surfaces the raw log.
  Reads `$GH_REPO` / `$GITHUB_STEP_SUMMARY` / `$GITHUB_OUTPUT` from the Actions env.

The `publish` parser is unit-tested (`harness/tests/`, gated by
`.github/workflows/harness-tests.yml`) precisely because it is the #117 drift
surface — a tested stdlib parser replaces the brittle `sed`/`jq` hand-escaping
that caused it ([ADR 0004](../adr/0004-runbook-helpers-are-python-stdlib.md)).

## Conventions baked into the skeleton

- **Off-the-hour cron + stateless hash-stagger.** Schedule off the top of the hour
  (`17`/`37` past, pre-peak) to dodge GitHub's busy-hour cron delay, and pick a slot
  **after** any upstream that produces this loop's input (a Consumer runs after the
  knowledge mirror's synthesis push). To avoid hand-coordinating slots as more repos
  onboard, derive the minute/hour from the job's own identity — a **stateless hash
  slot** (agent-research [ADR 0022](https://github.com/dividedby/agent-research/blob/main/docs/adr/0022-consumer-workflows-self-stagger-by-hash.md)):

  ```python
  offset = int(sha1(f"{repo}/{workflow}".encode()).hexdigest()[:6], 16)
  minute = offset % 60
  hour   = WINDOW_START + (offset // 60) % WINDOW_HOURS
  ```

  The hash picks only the **minute and hour within the assigned day**; the
  day/frequency stays as the cadence dictates. The shared **Friday-evening consumer
  window** (where `apply` / `improve-codebase-architecture` across all repos consume
  the same week's Friday synthesis) is `WINDOW_START=0`, `WINDOW_HOURS=4` on
  **Saturday UTC** (`* * 6`) — Saturday 00–04 UTC **is** Friday 19–23 CT, and the
  single `* * 6` mask avoids the UTC-midnight day-of-week straddle a literal
  `* * 5` evening window would hit. **First-Monday cadence** (e.g. staleness-review):
  POSIX cron can't express it, so fire every Monday and gate the job on
  `[ "$(date -u +%-d)" -le 7 ]`.
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
- **Adapt the runner to the repo's existing convention.** If the repo already
  runs Claude via `anthropics/claude-code-base-action`, match that instead of the
  `claude.ai/install.sh` + `claude -p` shown here. The skill is used by file path,
  so no skill-discovery config is needed either way.
- **Emit the cost-ledger line.** `harness/cli.py digest` writes the single
  `total_cost_usd=<…>  duration_ms=<…>  num_turns=<…>` line that a cross-repo
  **cost hub** (`dividedby/agent-research`) scrapes from each participating repo's
  run logs to project monthly spend. Every proposal loop must emit it — it is part
  of the skeleton, not a per-loop add-on. Use `--output-format stream-json
  --verbose` (not plain `json`, which buffers and goes dark on a hang) so the final
  `result` event lands in the log before `claude` exits; cost is then captured even
  on a failed run. The hub reads logs via a least-privilege `Actions: Read` PAT it
  holds — see the onboarding doc's manual steps for the token the human must mint.
- **Pin `--model` — default `claude-sonnet-4-6`.** Always pass an explicit
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
- Any **loop-specific** token (e.g. a Consumer's `SKILLS_TRACKER_TOKEN` for
  cross-repo writes) — see that loop's doc.
