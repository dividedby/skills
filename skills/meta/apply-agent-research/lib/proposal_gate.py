"""Proposal gate: the pure decision that picks at most one proposal to file.

Called by the ``apply-agent-research`` skill (via ``cli.py``). The cap (at most
one issue per run) and dedup live here so they do not depend on model judgment.
The caller gathers candidates and open-issue dedup keys and injects them; this
module never touches the tracker.
"""


def decide(candidates, open_issues, min_priority=1):
    """Return ``{"file": candidate}`` for the single proposal to file, or
    ``{"file": None}`` to file nothing.

    ``candidates`` is a list of dicts each carrying ``dedup_key`` (str) and
    ``priority`` (int). ``open_issues`` is an iterable of dedup-key strings
    already open on the tracker. A candidate is eligible when its key is not
    already open and its priority clears ``min_priority``. Among eligible
    candidates the highest priority wins; ties break on the smallest dedup key.
    """
    open_keys = set(open_issues)
    eligible = [
        c
        for c in candidates
        if c["dedup_key"] not in open_keys and c["priority"] >= min_priority
    ]
    if not eligible:
        return {"file": None}
    chosen = min(eligible, key=lambda c: (-c["priority"], c["dedup_key"]))
    return {"file": chosen}
