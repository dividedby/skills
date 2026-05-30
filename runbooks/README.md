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
    - `kb_source.py` — `load_kb_source` (curated `knowledge/` allow-list) +
      `read_kb` (read only the listed subpaths under an injected KB root; each
      note carries its `subject`/`category` axes, in stable order). The
      self-improvement acquisition contract — the C parallel to `repo_scan`
      (explicit; no auto-discovery).
  - Orchestrators:
    - `self_improvement.py` — `run(...)` builds/commits the integration map
      consumer-side, then proposes at most one skill refinement via the real
      proposal gate, filed under `source:self-improvement` (#19). Never edits a
      skill. Without the proposal seams it is the #16 analysis-only run.
    - `gap_scanner.py` — `run(...)` scans the curated repos read-only, then
      detects a recurring need and proposes at most one new skill via the real
      sanitizer + proposal gate, filed under `source:gap-scanner` (#20). Sanitizer
      runs before the gate so private content is dropped before filing. Without
      the proposal seams it is the #17 scan-only skeleton.
- `config/` — curated allow-lists (explicit; no auto-discovery):
  `gap-scanner-repos.json` (D's repo list) and `kb-source.json` (C's KB slug +
  `knowledge/` subpaths).
- `tests/` — stdlib `unittest`. Pure helpers use synthetic inputs (no fakes);
  orchestrators use integration dry-runs against fixture dirs + injected fakes.
- `prompts/` — run-book prompts (the orchestration the AFK agent follows):
  `self-improvement.md`, `gap-scanner.md`.

## Tests

```bash
python3 -m unittest discover -s runbooks
```

Zero third-party dependencies — Python 3 standard library only.
