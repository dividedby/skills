#!/usr/bin/env python3
"""SessionStart roadmap drift nudge (TEMPLATE — copy to a consumer's
`.claude/hooks/` and edit the config block). Cheaply compares the census
against current issue state; on drift, prints a one-line nudge to run
/doc-regen. Advisory only (never blocks, never edits); throttled; fails open
silently (offline / no gh / no roadmap). Stdlib only (ADR 0004).

The census parser keys off *column index*, not a fixed schema, so a repo
adapts by editing ISSUE_COL / STATUS_COL / DONE_TOKEN below — see the matching
`roadmap-drift-nudge.test.py` to confirm your config against a sample table."""
import json
import os
import subprocess
import sys
import time

# --- config (edit per repo) -------------------------------------------------
ROADMAP = "docs/plans/roadmap.md"
STAMP = ".git/roadmap-drift-nudge.stamp"  # never committed; repoint if .git must stay pristine
THROTTLE_SECONDS = 6 * 60 * 60
GH_TIMEOUT = 8
ISSUE_COL = 0   # zero-based census column holding the issue number
STATUS_COL = 3  # zero-based census column holding the status
DONE_TOKEN = "done"  # substring (lowercased) in the status cell that means closed/done
# ---------------------------------------------------------------------------


def parse_census(text: str) -> dict[int, str]:
    """Map issue number -> normalized status from the census table. Pure; a
    row counts only when its ISSUE_COL cell is an integer (skips header and
    `| --- |` separator rows automatically)."""
    rows: dict[int, str] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= max(ISSUE_COL, STATUS_COL):
            continue
        num_cell = cells[ISSUE_COL].lstrip("#").strip()
        if not num_cell.isdigit():
            continue
        status = cells[STATUS_COL].replace("*", "").replace("`", "").strip().lower()
        rows[int(num_cell)] = status
    return rows


def compute_drift(rows: dict[int, str], states: dict[int, str]):
    """Pure. Returns (stale_closed, unfiled_open):
    - stale_closed: issues closed on GitHub but not yet Done in the census.
    - unfiled_open: issues open on GitHub with no census row."""
    stale_closed = sorted(n for n, st in rows.items()
                          if states.get(n) == "closed" and DONE_TOKEN not in st)
    unfiled_open = sorted(n for n, st in states.items()
                          if st == "open" and n not in rows)
    return stale_closed, unfiled_open


def _throttled() -> bool:
    try:
        return (time.time() - os.path.getmtime(STAMP)) < THROTTLE_SECONDS
    except OSError:
        return False


def _stamp() -> None:
    try:
        with open(STAMP, "w") as f:
            f.write(str(int(time.time())))
    except OSError:
        pass


def _issue_states():
    try:
        out = subprocess.check_output(
            ["gh", "issue", "list", "--state", "all", "--limit", "400",
             "--json", "number,state"],
            text=True, stderr=subprocess.DEVNULL, timeout=GH_TIMEOUT)
        return {it["number"]: it["state"].lower() for it in json.loads(out)}
    except Exception:
        return None


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    if not os.path.exists(ROADMAP) or _throttled():
        return 0
    states = _issue_states()
    if states is None:
        return 0  # offline / no gh — retry next session (no stamp written)
    _stamp()
    try:
        with open(ROADMAP) as f:
            rows = parse_census(f.read())
    except OSError:
        rows = {}
    stale_closed, unfiled_open = compute_drift(rows, states)
    if not stale_closed and not unfiled_open:
        return 0
    parts = []
    if stale_closed:
        parts.append(f"{len(stale_closed)} closed issue(s) still non-Done in the census "
                     f"(#{', #'.join(map(str, stale_closed))})")
    if unfiled_open:
        parts.append(f"{len(unfiled_open)} open issue(s) with no census row "
                     f"(#{', #'.join(map(str, unfiled_open))}) — some may be aggregate-covered")
    msg = ("Roadmap drift: " + ROADMAP + " may be stale vs `gh` issue state — "
           + "; ".join(parts) + ". Run `/doc-regen` to reconcile (it edits the "
           "working tree for review and writes additive issue comments; it never commits).")
    print(json.dumps({"hookSpecificOutput":
          {"hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
