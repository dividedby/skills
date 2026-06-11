#!/usr/bin/env python3
"""PreToolUse roadmap self-update guard (TEMPLATE — copy to a consumer's
`.claude/hooks/` and edit the config block). Denies an issue-referencing
`git commit` unless ROADMAP is touched somewhere in the branch (staged, or
earlier vs the base branch). Fails open on anything it cannot determine.
Stdlib only (ADR 0004)."""
import json
import re
import subprocess
import sys

# --- config (edit per repo) -------------------------------------------------
ROADMAP = "docs/plans/roadmap.md"  # where the roadmap lives
# Branch(es) a PR may merge into. A list supports two-hop repos
# (feature→staging→main): list every base, and the roadmap counts as touched if
# it changed vs *any* of them. A bare string is still accepted.
BASE_BRANCH = ["main"]
# One-line cap (chars) for the census Notes/Status cells that keep the table thin
# (ADR 0025 thin-pointer cell). Cells at the cap are fine; over-cap is denied.
CELL_CAP = 120
# Census columns subject to the cell-cap/multi-line check, matched on the header.
CAPPED_HEADERS = {"status", "notes"}
# ---------------------------------------------------------------------------
ISSUE_REF = re.compile(r"#\d+")
# Burn-down header line: "**N issues — C closed (P%), O open.**" — we read O.
BURNDOWN_OPEN = re.compile(r"(\d+)\s+open\b")


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    """A `| --- | --- |` separator row: every cell is only dashes/colons."""
    return bool(cells) and all(set(c) <= {"-", ":"} and c for c in cells)


def _census_cols(text: str) -> tuple[dict[str, int], int] | None:
    """From the first markdown table header carrying both an issue (`#`) and a
    `Status` column, return ({header_lower: col_index}, issue_col). Pure; returns
    None when no such header exists (caller fails open)."""
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _split_row(line)
        if _is_separator(cells):
            continue
        lowered = [c.lower() for c in cells]
        if "status" in lowered and ("#" in lowered or "issue" in lowered):
            idx = {h: i for i, h in enumerate(lowered)}
            issue_col = idx.get("#", idx.get("issue"))
            return idx, issue_col
    return None


def _census_rows(text: str):
    """Yield each census data row's cells (issue cell is an integer). Skips the
    header, the `| --- |` separator, and any non-table line."""
    cols = _census_cols(text)
    if cols is None:
        return
    _, issue_col = cols
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _split_row(line)
        if len(cells) <= issue_col:
            continue
        if cells[issue_col].lstrip("#").strip().isdigit():
            yield cells


def _cell_violations(census_text: str) -> list[str]:
    """Flag census Status/Notes cells that exceed CELL_CAP or span multiple lines
    (a `<br>` or embedded newline). Pure; empty/rowless/malformed input yields no
    violations (fail open). Returns one message per offending cell."""
    cols = _census_cols(census_text)
    if cols is None:
        return []
    idx, _ = cols
    capped = {idx[h] for h in CAPPED_HEADERS if h in idx}
    out: list[str] = []
    for cells in _census_rows(census_text):
        for col in capped:
            if col >= len(cells):
                continue
            cell = cells[col]
            if "<br>" in cell or "\n" in cell:
                out.append(f"multi-line cell: {cell[:40]!r}")
            elif len(cell) > CELL_CAP:
                out.append(f"over-cap cell ({len(cell)}>{CELL_CAP}): {cell[:40]!r}")
    return out


def _burndown_consistent(text: str) -> bool:
    """True when the Burn-down 'O open' count matches the census open-row count
    (rows whose Status is not Done). Pure; a missing Burn-down line, no census,
    or unparseable count returns True (fail open)."""
    m = BURNDOWN_OPEN.search(text)
    cols = _census_cols(text)
    if m is None or cols is None:
        return True
    idx, _ = cols
    status_col = idx["status"]
    rows = list(_census_rows(text))
    if not rows:
        return True
    open_rows = 0
    for cells in rows:
        if status_col >= len(cells):
            continue
        status = cells[status_col].replace("*", "").replace("`", "").strip().lower()
        if status != "done":
            open_rows += 1
    return int(m.group(1)) == open_rows


def _base_branches() -> list[str]:
    """Normalize BASE_BRANCH to a list (a bare string is wrapped)."""
    if isinstance(BASE_BRANCH, str):
        return [BASE_BRANCH]
    return list(BASE_BRANCH)


def _changed() -> set[str] | None:
    """Files changed in this branch: staged, plus vs each base. Returns None
    when git is unusable for *every* probe (e.g. not a repo, no git) so the
    caller can fail open rather than deny on an undeterminable state."""
    files: set[str] = set()
    any_ok = False
    diffs = [["git", "diff", "--cached", "--name-only"]]
    diffs += [["git", "diff", "--name-only", f"{base}...HEAD"]
              for base in _base_branches()]
    for args in diffs:
        try:
            out = subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            continue
        any_ok = True
        files.update(line.strip() for line in out.splitlines() if line.strip())
    return files if any_ok else None


def _enforced(cmd: str) -> bool:
    """Only an issue-referencing `git commit` is enforced."""
    return "git commit" in cmd and bool(ISSUE_REF.search(cmd))


def decide(cmd: str, changed: set[str] | None, roadmap_text: str | None = None) -> int:
    """Pure deny/allow decision: 0 = allow, 2 = deny. For an issue-referencing
    commit, deny when ROADMAP is untouched across `changed`, OR when the in-branch
    ROADMAP content (`roadmap_text`) carries an over-cap/multi-line census cell or
    a Burn-down that disagrees with the census. `changed is None` (git
    undeterminable) and `roadmap_text is None` (content unavailable/unparseable)
    each fail open → allow on that dimension."""
    if not _enforced(cmd):
        return 0
    if roadmap_text is not None:
        if _cell_violations(roadmap_text) or not _burndown_consistent(roadmap_text):
            return 2
    if changed is None or ROADMAP in changed:
        return 0
    return 2


def _roadmap_text() -> str | None:
    """The in-branch ROADMAP content (working tree). None when unreadable so the
    content checks fail open rather than deny on an undeterminable state."""
    try:
        with open(ROADMAP, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def main() -> int:
    try:
        cmd = (json.load(sys.stdin).get("tool_input", {}) or {}).get("command", "")
    except Exception:
        return 0  # fail open on malformed/absent input
    if not _enforced(cmd):
        return 0
    text = _roadmap_text()
    if decide(cmd, _changed(), text) == 0:
        return 0
    if text is not None and (_cell_violations(text) or not _burndown_consistent(text)):
        print(f"roadmap-guard: this commit references an issue but {ROADMAP} has a "
              f"census cell over the {CELL_CAP}-char one-line cap / spanning multiple "
              f"lines, or a Burn-down count that disagrees with the census Status "
              f"column. Thin the cell (ADR 0025) or fix the Burn-down, then re-commit.",
              file=sys.stderr)
    else:
        print(f"roadmap-guard: this commit references an issue but does not touch "
              f"{ROADMAP}. Update the issue's census row (Status, and Deps if changed) "
              f"in this branch first. If this commit is pure infra, omit the #NN.",
              file=sys.stderr)
    return 2  # deny


if __name__ == "__main__":
    sys.exit(main())
