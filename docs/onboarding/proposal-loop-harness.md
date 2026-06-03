# The proposal-loop harness

A **[proposal loop](../../CONTEXT.md)** is a scheduled, skill-driven GitHub
Actions workflow that reads some input, then **proposes via labeled issues and
never applies** — no commits, edits, or PRs. Both of this owner's proposal loops
share this harness; only the *skill*, the *input*, and the *label* differ:

- **[`consumer-setup.md`](./consumer-setup.md)** — `apply-agent-research`
  (KB + governance docs → agent-meta improvements). The rich one: adds the
  knowledge-mirror input and the cross-repo `skill-request` / `skill-promotion`
  channels.
- **[`arch-review-setup.md`](./arch-review-setup.md)** —
  `improve-codebase-architecture` (the codebase → refactor proposals). The
  simplest member: harness + a skill, nothing more.

This file is the **common skeleton** both reference. Read it first, then the
loop-specific doc.

## The two load-bearing decisions

- **Propose via issues; a human decides** ([ADR 0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md)).
  The loop's *only* mutation is filing issues. `permissions: contents: read,
  issues: write`. No `Edit`/`Write` tools, no commits, no PRs. This producer/decider
  split is what makes unattended operation safe.
- **Fetch the skill fresh each run; never vendor it** ([ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
  `git clone --depth 1` the skill's source repo and `cp -R` the skill into
  `~/.claude/skills/` at the start of every run. A committed copy silently drifts;
  for a security-relevant skill (a leak guard) that drift is the worst failure
  mode. The skill is used **by file path**, so any readable location works —
  `~/.claude/skills/` is parity convention, not a requirement.

## Skeleton workflow

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
      - uses: actions/checkout@v5
        with: { ref: <default-branch>, fetch-depth: 1 }

      # --- Fetch the skill fresh (ADR 0008) ---
      - name: Install the skill
        run: |
          set -euo pipefail
          tmp=$(mktemp -d)
          git clone --depth 1 https://github.com/<owner>/<skills-repo>.git "$tmp/src"
          mkdir -p ~/.claude/skills
          cp -R "$tmp/src/<path-to-skill>" ~/.claude/skills/
          test -f ~/.claude/skills/<skill-name>/SKILL.md
          echo "Installed <skill-name>@$(git -C "$tmp/src" rev-parse --short HEAD)"
      # If the skill bundles a code guard, run its unit tests here as a HARD GATE
      # and fail the run on failure — never file with a broken guard.

      - name: Ensure provenance label exists
        run: gh label create "$LABEL" --color "5319E7" --description "..." >/dev/null 2>&1 || true

      - name: Run the loop
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
        run: |
          set -euo pipefail
          # stream-json + tee to JSONL so the final `result` event (carrying
          # total_cost_usd) reaches the log before claude exits — cost is then
          # captured even on a failed run, and the cross-repo ledger can scrape it.
          claude -p \
            --output-format stream-json --verbose \
            --permission-mode acceptEdits \
            --allowedTools "<scoped to what the loop needs>" \
            --append-system-prompt "$(cat .github/workflows/prompts/<loop>.md)" \
            "<one-line task pointer to the system prompt>" \
            | tee "$RUNNER_TEMP/agent.jsonl"
          # Clean summary (last result event) + the cost ledger line. Best-effort:
          # a failed run already failed the pipe above; fromjson? skips non-JSON.
          jq -rR 'fromjson? | select(.type=="result") | .result // ""' \
            "$RUNNER_TEMP/agent.jsonl" | tail -1 > "$RUNNER_TEMP/agent.log" || true
          jq -rR 'fromjson? | select(.type=="result") | "total_cost_usd=\(.total_cost_usd // "n/a")  duration_ms=\(.duration_ms // "n/a")  num_turns=\(.num_turns // "n/a")"' \
            "$RUNNER_TEMP/agent.jsonl" | tail -1 > "$RUNNER_TEMP/agent.cost" || true

      - name: Summarise run
        if: always()
        run: |
          { echo "## <Loop Name>"; echo; \
            cat "$RUNNER_TEMP/agent.cost" 2>/dev/null || true; echo; echo '```'; \
            tail -n 50 "$RUNNER_TEMP/agent.log" 2>/dev/null || echo "(no log)"; \
            echo '```'; } >> "$GITHUB_STEP_SUMMARY"
```

## Conventions baked into the skeleton

- **Off-the-hour cron** (`17`/`37` past, pre-peak) to dodge GitHub's busy-hour
  cron delay. Pick a slot **after** any upstream that produces this loop's input
  (e.g. a Consumer runs after the knowledge mirror's synthesis push).
- **`concurrency` with `cancel-in-progress: false`** so a long run is never
  killed mid-flight by the next tick.
- **Scoped `--allowedTools`.** Grant only what the loop needs (`Read Grep Glob`,
  `Bash(gh:*) Bash(git:*)`, etc.). *Exception:* if the skill invokes a guard via a
  **pipe** (`printf ... | python3 cli.py`), `Bash` must be **unscoped** — a scoped
  `Bash(python3:*)` blocks a command that starts with `printf`. The no-commits
  invariant then rests on `contents: read` + the absence of `Edit`/`Write`, not on
  Bash scoping. See agent-research#127.
- **Adapt the runner to the repo's existing convention.** If the repo already
  runs Claude via `anthropics/claude-code-base-action`, match that instead of the
  `npm install -g @anthropic-ai/claude-code` + `claude -p` shown here. The skill is
  used by file path, so no skill-discovery config is needed either way.
- **Emit the cost-ledger line.** The runner streams `stream-json` JSONL and the
  summary step surfaces a single `total_cost_usd=<…>  duration_ms=<…>
  num_turns=<…>` line. A cross-repo **cost hub** (`dividedby/agent-research`)
  scrapes that line from each participating repo's run logs to project monthly
  spend, so every proposal loop must emit it — it is part of the skeleton, not a
  per-loop add-on. Use `--output-format stream-json --verbose` (not plain `json`,
  which buffers and goes dark on a hang) so the final `result` event lands in the
  log before `claude` exits; cost is then captured even on a failed run. The hub
  reads logs via a least-privilege `Actions: Read` PAT it holds — see the
  onboarding doc's manual steps for the token the human must mint.

## Required secrets

- **`CLAUDE_CODE_OAUTH_TOKEN`** — so the run can authenticate. A repo already
  running Claude in Actions has this; reuse it.
- Any **loop-specific** token (e.g. a Consumer's `SKILLS_TRACKER_TOKEN` for
  cross-repo writes) — see that loop's doc.
