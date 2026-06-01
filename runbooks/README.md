# Run-books

> **Mostly retired.** The central-push run-book topology (integration map,
> self-improvement and gap-scanner orchestrators, the curated KB/repo allow-lists)
> was replaced by the decentralized-pull `apply-agent-research` skill and the
> `skill-request` flow — see
> [`docs/design/cross-repo-knowledge-application.md`](../docs/design/cross-repo-knowledge-application.md).
> What remains here are the two pure decision helpers the new skill reuses,
> plus the CLI seam that exposes them to the workflow.

Internal machinery for the skill-improvement workflows — **not** published
skills, never registered in `plugin.json`. See
[`CONTEXT.md`](../CONTEXT.md) for the `run-book` vocabulary,
[ADR 0003](../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)
for the producer/decider model, and
[ADR 0004](../docs/adr/0004-runbook-helpers-are-python-stdlib.md) for why the
helpers are Python stdlib.

## Layout

- `lib/` — the survivors. Two **pure decision** helpers (inputs in, decision out,
  no tracker/git/clone I/O) and one CLI seam over them.
  - Pure decisions:
    - `proposal_gate.py` — `decide(candidates, open_issues, min_priority=1)`
      picks at most one proposal to file (dedup + priority + deterministic
      tie-break).
    - `sanitizer.py` — `check(body, private_markers=())` blocks private-repo
      content from this public tracker.
  - Seam:
    - `cli.py` — exposes `sanitizer.check` and `proposal_gate.decide` as
      stdin/stdout subcommands (`sanitize`, `gate`) so the `apply-agent-research`
      skill enforces the leak guard and the one-proposal cap *mechanically* in CI,
      not by prompt discipline. Holds no policy of its own.
- `tests/` — stdlib `unittest`. Pure helpers use synthetic inputs (no fakes); the
  CLI is exercised over its stdin/stdout contract.

## Tests

```bash
python3 -m unittest discover -s runbooks
```

Zero third-party dependencies — Python 3 standard library only.
