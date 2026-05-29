# Run-books

Internal machinery for the skill-improvement workflows — **not** published
skills, never registered in `plugin.json`. See
[`CONTEXT.md`](../CONTEXT.md) for the `run-book` vocabulary,
[ADR 0003](../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)
for the producer/decider model, and
[ADR 0004](../docs/adr/0004-runbook-helpers-are-python-stdlib.md) for why the
helpers are Python stdlib.

## Layout

- `lib/` — pure decision helpers (inputs in, decision out; no tracker/git/clone
  I/O). The run-books inject everything; this is the seam that makes the
  ≤1-issue-per-run cap and the no-private-code rule testable offline.
  - `proposal_gate.py` — `decide(candidates, open_issues, min_priority=1)`
    picks at most one proposal to file (dedup + priority + deterministic
    tie-break).
  - `sanitizer.py` — `check(body, private_markers=())` blocks private-repo
    content from this public tracker.
- `tests/` — stdlib `unittest` over synthetic inputs. No fakes; the helpers are
  pure.
- `prompts/` — run-book prompts (the orchestration the AFK agent follows).

## Tests

```bash
python3 -m unittest discover -s runbooks
```

Zero third-party dependencies — Python 3 standard library only.
