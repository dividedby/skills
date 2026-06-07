"""Urgency ranking for staleness findings: a pure decision, not model judgment.

The report ranks findings most-urgent-first so a reader acts on the riskiest pin
first. "Most urgent" must be deterministic and reproducible — it drives what a
human sees at the top of the report — so the ordering lives here as executable
code (ADR 0004: pure, Python stdlib, table-driven tests, never registered in
plugin.json), not prose the agent re-sorts by feel each run.

Pure: a list of finding dicts in, a new ordered list out. No I/O. The skill prose
owns gathering each finding's `gap` (from `version_gap.classify`) and `eol_passed`
(from the web-validation step); this module owns only the ordering.
"""

# Higher = more urgent. A pin whose current version is past upstream EOL is the
# top risk regardless of how many versions behind it is; within the same EOL
# state, a larger version gap is more urgent.
_GAP_RANK = {"major": 3, "minor": 2, "patch": 1, "none": 0, "unknown": 0}


def urgency_key(finding):
    """Return a sort key (higher = more urgent) for one finding.

    ``finding`` is a dict carrying ``gap`` (``major|minor|patch|none|unknown``) and
    ``eol_passed`` (``True`` when current is past upstream EOL; ``False``/``None``
    otherwise — a missing or unverified EOL is treated as not-passed, never as
    urgent, so the absence of web data cannot manufacture urgency).
    """
    eol_rank = 1 if finding.get("eol_passed") is True else 0
    gap_rank = _GAP_RANK.get(finding.get("gap"), 0)
    return (eol_rank, gap_rank)


def rank_findings(findings):
    """Return a new list of ``findings`` ordered most-urgent-first.

    Stable: findings of equal urgency keep their input order. Does not mutate the
    input list or its dicts.
    """
    return sorted(findings, key=urgency_key, reverse=True)
