# Run-books

Internal machinery for the skill-improvement workflows — **not** published
skills, never registered in `plugin.json`. See
[`CONTEXT.md`](../CONTEXT.md) for the `run-book` vocabulary,
[ADR 0003](../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)
for the producer/decider model, and
[ADR 0004](../docs/adr/0004-runbook-helpers-are-python-stdlib.md) for why the
helpers are Python stdlib.

## Layout

- `lib/` — helpers. The **pure decision** helpers take inputs and return a
  decision with no tracker/git/clone I/O; the **orchestrators** wire seams with
  all I/O injected, so the whole workflow is testable on fixtures.
  - Pure decisions:
    - `proposal_gate.py` — `decide(candidates, open_issues, min_priority=1)`
      picks at most one proposal to file (dedup + priority + deterministic
      tie-break).
    - `sanitizer.py` — `check(body, private_markers=())` blocks private-repo
      content from this public tracker.
  - Seams:
    - `map_store.py` — `read_map` / `write_map` for the integration map;
      `write_map` writes only if changed (keeps re-runs to a minimal diff).
    - `repo_scan.py` — `load_repo_list` (curated allow-list) + `scan` context
      manager (shallow-clone listed repos via an injected `clone`, clean up on
      exit).
  - Orchestrators:
    - `self_improvement.py` — `run(...)` builds/commits the integration map
      consumer-side, then proposes at most one skill refinement via the real
      proposal gate, filed under `source:self-improvement` (#19). Never edits a
      skill. Without the proposal seams it is the #16 analysis-only run.
    - `gap_scanner.py` — `run(...)` scans the curated repos read-only and exits
      clean; files nothing yet (#17).
- `config/` — `gap-scanner-repos.json`, the curated repo allow-list (explicit;
  no auto-discovery).
- `tests/` — stdlib `unittest`. Pure helpers use synthetic inputs (no fakes);
  orchestrators use integration dry-runs against fixture dirs + injected fakes.
- `prompts/` — run-book prompts (the orchestration the AFK agent follows):
  `self-improvement.md`, `gap-scanner.md`.

## Tests

```bash
python3 -m unittest discover -s runbooks
```

Zero third-party dependencies — Python 3 standard library only.
