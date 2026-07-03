# Authoring a scheduled headless-Claude workflow

This doc is for two distinct audiences — read the section that matches your role:

- **Author** — you are editing a `*-reusable.yml` body in `dividedby/skills`
  (adding a proposal loop, or changing its model, budget, tools, or first-Monday
  gate). The checklist below applies to you in full. Re-cadencing — changing the
  cron *schedule* — is a caller-stub edit, not a body edit: the schedule lives in
  the stub, only the first-Monday gate lives in the body.
- **Consumer** — you are vendoring a thin caller stub in another repo
  (a `uses: dividedby/skills/.github/workflows/*-reusable.yml@claude-loops-v1`
  block). You inherit `--model`, `--max-budget-usd`, `--allowedTools`, the cron
  gate, `concurrency`, and the cost-ledger `digest` step from the reusable body.
  **Do not re-author any of those in your stub.** The only thing you set is the
  cron schedule (derived by the hash-stagger rule in step 5) and any
  loop-specific `with:` inputs. See the per-loop setup docs for your stub form.

Post-#382 / [ADR 0029](../adr/0029-apply-agent-research-joins-the-reusable-body-rail.md),
all three proposal loops run as `workflow_call` reusable bodies; consumers vendor
only the thin caller stub. The checklist below is the **author** checklist — it
governs what goes into the `*-reusable.yml` body. Every such body is metered
`claude -p` spend, so the rules are about **cost legibility and budget fit**, not
just "does it run" (the shared Agent SDK monthly credit that originally motivated
this has since been walked back; the tracking is retained in case it returns). The
binding decisions live in ADR
[0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md) (per-run
budget/cap + the 2026-06-20 cadence amendment) and ADR
[0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)
(the reusable-body rail; thin caller stubs vendor only `on:`/`permissions:`/`uses:`/`secrets:`).
The hash-stagger rule itself lives one repo over, in **agent-research ADR 0022** —
the estate's scheduling convention — and is summarised in step 5.

## The checklist

1. **Pin `--model` explicitly — to the exact model ID.** Never rely on the OAuth
   default — it can silently flip to opus. And a floating alias (`sonnet`,
   `opus`) is not a pin: it silently inherits the next model release into an
   unattended loop. Pin the exact ID (e.g. `claude-sonnet-5`) and bump it only
   after testing the loop's prompts on the new model (#180). Tier per the #161
   cost/quality verdicts: **sonnet is cheaper *and* scored ≥ opus** on the
   proposal-loop tasks, so every loop here pins sonnet. Opus is reserved for a
   quality-critical distillation surface — which lives elsewhere in the estate
   (agent-research's `synthesize`), not in this repo. The pin is determinism, not
   only a saving.

2. **Carry a `--max-budget-usd` backstop.** Every headless `claude -p` invocation
   takes `--max-budget-usd`, sized ~2.5–3× the workflow's observed max (#181).
   It's a backstop against a runaway run, not a routine ceiling — a healthy run
   should never hit it. The four loops here run at `$4.00`. No history yet? Size
   off the nearest same-shape workflow and revisit once runs accrue.

3. **Emit `total_cost_usd` so the run is metered.** Run with
   `--output-format stream-json --verbose` into a JSONL log, and pass the
   **prompt via stdin** (the variadic `--allowedTools` eats a positional prompt —
   see the `claude-p-headless-stdin-gotcha` memory). Then
   `python3 harness/cli.py digest --jsonl <log> …` parses the final `result`
   event and writes the `total_cost_usd=… num_turns=…` cost line — the scrape
   logic lives in the **fetched-fresh harness**, so one fix reaches every loop.
   A workflow that doesn't emit this line is **unmetered spend** — do not ship it
   (global rule in `~/.claude/CLAUDE.md`). A crashed/empty run (no `result` event
   at all) or a completed-but-failed run (`result.is_error: true`) PREPENDS
   `error=no-result` / `error=is_error` to that line, so COST_SURFACE can tell a
   failed run apart from a genuinely cheap one instead of both collapsing into
   `total_cost_usd=n/a` or an indistinguishable low number; a clean run's line
   carries no `error=` field and is byte-identical to the pre-error-field format.

4. **Onboard into the cost surface — cross-repo.** This repo has no local cost
   registry; the estate's cost hub lives in **agent-research**. Add the
   `(repo, workflow) -> runs/month` entry to `COST_SURFACE` in agent-research's
   `kb_afk/cost_surface.py` (the single registry the per-repo token map and the
   monthly projection derive from; its `tests/test_cost_surface.py` pins the
   numbers test-first) and a row in agent-research's `docs/cost-tracking.md`. A
   cron change **is** a `runs/month` change. For a consumer in another repo, also
   add its `<CONSUMER>_ACTIONS_TOKEN` secret to that `cost-ledger.yml` (GHA can't
   enumerate secrets).

5. **Cron off-the-hour, and self-stagger by hash.** Never schedule on the top of
   the hour (GitHub's busy-hour cron delay). Derive the slot from the job
   identity so onboarding a new consumer needs zero schedule coordination
   (agent-research ADR 0022):

   ```python
   offset = int(sha1(f"{repo}/{workflow}".encode()).hexdigest()[:6], 16)
   minute = offset % 60
   hour   = WINDOW_START + (offset // 60) % WINDOW_HOURS
   ```

   The hash picks only the **minute and hour within the assigned day**; the
   day/frequency stays as the calendar assigns it. **Keep the window inside one
   UTC day** — a literal `* * 5` Friday-evening band straddles UTC midnight and
   fires a day early; the Friday-evening band lives on **Saturday UTC** (`* * 6`,
   `WINDOW_START=0`, `WINDOW_HOURS=4` = Fri 19–23 CT).

6. **First-Monday (or first-of-month) cadence? Guard it in the job.** POSIX cron
   can't express "first Monday" (restricting both day-of-month and day-of-week
   ORs them). Schedule every Monday and gate the run:
   `[ "$(date -u +%-d)" -le 7 ] || exit 0` — exactly the `first-monday-gate` job
   `staleness-review` uses.

## The reference cadence (this repo, 2026-06-30 amendment)

Encode new workflows against the four loops this repo runs. All sonnet, all
**propose-only** — never edit/commit/merge. Cadence: the two Mon/Wed/Sat loops
are hash-staggered (step 5) into the 00–04 UTC off-peak band (ADR 0022), and
weekly `changelog-health` derives its Thu 01:33 UTC slot the same way; monthly
`staleness-review` uses a hand-chosen slot instead (`8 13 * * 1`). The three
proposal loops file budgeted, ranked issues; `changelog-health` is
advisory-only, filing at most one dedup'd issue per repo.

| Loop | Model | Cron (UTC) | ≈ CT | cap |
| --- | --- | --- | --- | --: |
| `improve-codebase-architecture` | sonnet | `5 0 * * 1,3,6` | Sun/Tue/Fri 19:05 | ≤1 |
| `apply-agent-research` | sonnet | `19 1 * * 1,3,6` | Sun/Tue/Fri 20:19 | ≤1 |
| `staleness-review` | sonnet | `8 13 * * 1` (1st-Mon gate) | Mon 08:08 | 1 |
| `changelog-health` | sonnet | `33 1 * * 4` | Wed 20:33 | ≤1 (dedup) |

Two non-obvious choices worth copying:

- **The per-run cap lives in the reusable body**, not in the thin caller stub:
  `harness/cli.py publish` clamps to `MAX_PROPOSALS` (ADR 0019, lowered 5 → 2 on
  2026-06-20, then 2 → 1 on 2026-06-30), and `apply-agent-research`'s skill gate
  clamps to its own `MAX_BUDGET`. Changing the thin caller stub's comment does
  not change the cap — change the reusable body.
- **`apply-agent-research` consumes the published knowledge mirror**, so its
  cadence rides behind the producer (agent-research synthesizes Mon/Wed/Fri and
  pushes the mirror; consumers read it). The 3×/week consumer cadence is the
  ADR 0019 amendment.

Per-run cost rolls into the cross-repo `COST_SURFACE` projection (step 4); keep
the `$4` backstop unless a loop's observed max moves.
