"""Proposal gate: the pure decision that picks the few proposals worth filing.

Called by the ``apply-agent-research`` skill (via ``cli.py``). The cap (a shared
per-run budget, default 1, wired to 2 across all channels) and dedup live here so
they do not depend on model judgment. The caller gathers candidates and
open-issue dedup keys across every enabled channel and injects them in ONE call;
this module never touches the tracker.
"""

MAX_BUDGET = 2


def decide(candidates, open_issues, min_priority=1, budget=1):
    """Return ``{"file": [candidates]}`` — the ranked proposals to file, best
    first, at most ``budget`` (itself clamped to ``MAX_BUDGET``). An empty list
    means file nothing.

    ``candidates`` is a list of dicts each carrying ``dedup_key`` (str) and
    ``priority`` (int). ``open_issues`` is an iterable of dedup-key strings
    already open on the tracker. A candidate is eligible when its key is not
    already open and its priority clears ``min_priority``. Eligible candidates
    are ranked by priority (ties break on the smallest dedup key); duplicate
    keys within the batch keep only the best-ranked occurrence. The budget is a
    ceiling, not a target — the caller should inject only candidates it would
    defend individually.
    """
    budget = max(0, min(budget, MAX_BUDGET))
    open_keys = set(open_issues)
    eligible = [
        c
        for c in candidates
        if c["dedup_key"] not in open_keys and c["priority"] >= min_priority
    ]
    eligible.sort(key=lambda c: (-c["priority"], c["dedup_key"]))
    chosen, seen = [], set()
    for c in eligible:
        if c["dedup_key"] in seen:
            continue
        seen.add(c["dedup_key"])
        chosen.append(c)
        if len(chosen) == budget:
            break
    return {"file": chosen}
