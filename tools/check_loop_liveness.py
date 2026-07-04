"""Report-only loop-liveness check for the fleet's scheduled proposal loops.

Every recurring `claude -p` loop that runs as part of the reusable-rail
(#382/ADR 0029) — improve-codebase-architecture, apply-agent-research,
staleness-review — is expected to fire on its own cron in every enrolled
repo (including skills' own canary copies). A loop that silently stops
firing, or whose latest scheduled run failed, otherwise goes unnoticed until
the next manual audit (#522) — this check catches that class automatically.

Roster: reused directly from check_workflow_drift.py — REPOS (consumer
repos) plus the skills canary repo, crossed with the three reusable-rail
workflow paths it already reads (APPLY_PATH/ARCH_PATH/STALE_PATH). Plus two
host-only loops (changelog-health, skill-divergence-audit) that live only in
skills and are never vendored to consumers, so they're checked against the
skills repo only. No second roster is maintained here (#532 AC).

Cadence is parsed from each workflow file's own `cron:` schedule (the
day-of-week field's comma count -> runs/week -> days between runs). One
documented exception: staleness-review's cron reads as weekly but is
additionally gated to the first Monday of the month by the reusable body
(docs/agents/workflow-authoring.md item 7) — that job-level gate isn't
visible in the cron string itself, so the caller stub's own "first Monday"
comment (see staleness-review.yml) overrides the naive weekly reading with a
~30 day cadence.

Flags: no scheduled run within 2x cadence, or the latest scheduled run's
conclusion was "failure". Opens one dedup'd `loop-liveness` issue per repo
listing every stale/failed loop found there. Report only — never a gate.

Prerequisites
-------------
- ISSUES_TOKEN: fine-grained PAT, owner dividedby, all repositories,
  Contents:Read + Actions:Read + Issues:Write. Passed as --read-token.
  Until the secret is created the job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_loop_liveness.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from tools._drift_common import _gh, ensure_label, fetch_file, open_issues
    from tools._drift_common import file_issue as _file_issue_io
    from tools.check_workflow_drift import (
        APPLY_PATH,
        ARCH_PATH,
        REPOS,
        SKILLS_BRANCH,
        SKILLS_REPO,
        STALE_PATH,
    )
except ImportError:
    from _drift_common import _gh, ensure_label, fetch_file, open_issues
    from _drift_common import file_issue as _file_issue_io
    from check_workflow_drift import (
        APPLY_PATH,
        ARCH_PATH,
        REPOS,
        SKILLS_BRANCH,
        SKILLS_REPO,
        STALE_PATH,
    )

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# The three reusable-rail loop paths check_workflow_drift.py already reads.
LOOP_PATHS: tuple[str, ...] = (APPLY_PATH, ARCH_PATH, STALE_PATH)

# Host-only loops: recurring scheduled jobs that live only in the skills repo
# (never vendored to consumers), checked against SKILLS_REPO only — pairing
# them with consumer repos would 404 (#532 follow-up: the roster only covered
# the three reusable-rail loops, not these two).
HOST_LOOP_PATHS: tuple[str, ...] = (
    ".github/workflows/changelog-health.yml",
    ".github/workflows/skill-divergence-audit.yml",
)

# ponytail: matched against the caller stub's own prose comment (see
# staleness-review.yml) rather than also fetching the reusable body — the
# stub already documents the job-level first-Monday gate in a comment.
FIRST_MONDAY_MARKER = "first monday"

CRON_RE = re.compile(r'cron:\s*["\']([^"\']+)["\']')

SKILLS_REPO_WRITE = SKILLS_REPO  # issues are always filed here

LABEL = "loop-liveness"
LABEL_COLOR = "FBCA04"  # amber; distinct from the other three fleet-drift labels
LABEL_DESCRIPTION = "A recurring scheduled loop has gone quiet or its latest run failed"


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no I/O)
# ---------------------------------------------------------------------------


def build_roster() -> list[tuple[str, str, str]]:
    """(repo, branch, workflow_path) for every enrolled repo x reusable-rail loop,
    plus the skills-repo-only host loops (checked once, never against consumers).

    Repos come straight from check_workflow_drift.REPOS plus the skills
    canary (SKILLS_REPO/SKILLS_BRANCH) — no second roster maintained here.
    """
    repos = dict(REPOS)
    repos[SKILLS_REPO] = SKILLS_BRANCH
    roster = [(repo, branch, path) for repo, branch in repos.items() for path in LOOP_PATHS]
    roster += [(SKILLS_REPO, SKILLS_BRANCH, path) for path in HOST_LOOP_PATHS]
    return roster


def extract_cron(content: str) -> Optional[str]:
    """Pull the `cron: "..."` schedule expression out of workflow YAML text."""
    match = CRON_RE.search(content)
    return match.group(1) if match else None


def cron_cadence_days(cron_expr: str, content: str = "") -> Optional[float]:
    """Expected days between runs, from a 5-field cron `m h dom month dow`.

    Reads only the day-of-week field's comma count (every fleet cron here
    only varies day-of-week; a `*` day-of-week means daily). *content* is
    optionally checked for a documented first-Monday-of-month gate (job-level,
    invisible to the cron string itself — see staleness-review.yml) which
    overrides the naive weekly reading with a ~30 day cadence.

    Returns None if *cron_expr* isn't a recognizable 5-field cron.
    """
    if FIRST_MONDAY_MARKER in content.lower():
        return 30.0
    fields = cron_expr.split()
    if len(fields) < 5:
        return None
    dow = fields[4]
    if dow == "*":
        return 1.0
    return 7.0 / len(dow.split(","))


def check_liveness(
    cadence_days: float,
    last_run_iso: Optional[str],
    last_conclusion: Optional[str],
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Return a flag reason, or None if the loop looks healthy.

    *last_run_iso*/*last_conclusion* describe the most recent scheduled run
    (both None if the workflow has never had one). Flags: no run at all, the
    latest run's conclusion is "failure", or the latest run is more than 2x
    cadence old. *now* is injectable for deterministic tests.
    """
    if last_run_iso is None:
        return "no scheduled run found"
    if last_conclusion == "failure":
        return f"latest scheduled run failed ({last_run_iso})"
    now = now or datetime.now(timezone.utc)
    last_dt = datetime.fromisoformat(last_run_iso.replace("Z", "+00:00"))
    age_days = (now - last_dt).days
    threshold = cadence_days * 2
    if age_days > threshold:
        return (
            f"no completed run in {age_days}d (cadence {cadence_days:.2f}d, "
            f"2x threshold {threshold:.2f}d)"
        )
    return None


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
#
# fetch_file, ensure_label, open_issues, _gh are shared with the other
# fleet-drift checkers — see tools/_drift_common.py (#526).


def fetch_last_scheduled_run(
    repo: str, workflow_filename: str, read_token: str
) -> Optional[tuple[str, str]]:
    """(created_at ISO, conclusion) for the most recent SCHEDULED run of
    *workflow_filename* in *repo*, or None if it has never had one.

    conclusion is "" (falsy) for a run still in progress — the caller's
    `check_liveness` only flags an explicit "failure", so an in-progress run
    falls through to the age check exactly like a successful one.
    """
    result = _gh(
        [
            "api", f"repos/{repo}/actions/workflows/{workflow_filename}/runs",
            "-f", "event=schedule",
            "-f", "per_page=1",
            "--jq",
            '(.workflow_runs[0] // {}) | [(.created_at // ""), (.conclusion // "")] | @tsv',
        ],
        token=read_token,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh api {repo}/actions/workflows/{workflow_filename}/runs: "
            f"exit {result.returncode}: {result.stderr.strip()}"
        )
    line = result.stdout.strip()
    if not line:
        return None
    created_at, conclusion = line.split("\t", 1)
    if not created_at:
        return None
    return created_at, conclusion


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a repo with stale/failed loops (dedup + create)."""
    short = repo.split("/")[-1]
    return f"[loop-liveness] {short}: recurring loop(s) show no recent successful run"


def build_issue_body(repo: str, findings: dict[str, str]) -> str:
    """Build the markdown body for a loop-liveness issue.

    *findings* maps workflow path -> flag reason.
    """
    lines = [
        f"## Loop liveness check flagged `{repo}`",
        "",
        "The following recurring scheduled loops have not shown a completed",
        "run within 2x their cadence, or their latest scheduled run failed.",
        "This is an automated report from the weekly `loop-liveness` job",
        "([`tools/check_loop_liveness.py`](../../tools/check_loop_liveness.py)).",
        "",
    ]
    for path, reason in sorted(findings.items()):
        lines.append(f"- `{path}`: {reason}")
    lines += [
        "",
        "### What to do",
        "",
        "1. Check the workflow's Actions run history in this repo for the actual failure/silence.",
        "2. Fix the underlying cause (secret expiry, upstream API change, disabled schedule, etc.).",
        "3. Close this issue once the loop shows a recent successful run.",
    ]
    return "\n".join(lines)


def file_issue(
    repo: str, findings: dict[str, str], write_token: str, dry_run: bool
) -> None:
    """Open or print a loop-liveness issue for *repo* in skills."""
    title = _issue_title(repo)
    body = build_issue_body(repo, findings)
    dry_run_extra = [f"  {path}: {reason}" for path, reason in sorted(findings.items())]
    _file_issue_io(
        SKILLS_REPO_WRITE, title, body, LABEL, write_token, dry_run, dry_run_extra
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check the fleet's recurring scheduled loops for liveness."
    )
    parser.add_argument(
        "--read-token", default="", help="PAT for cross-repo Contents:Read + Actions:Read"
    )
    parser.add_argument("--write-token", default="", help="Token for Issues:Write in skills")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be filed; make no mutating API calls",
    )
    args = parser.parse_args(argv)

    read_token = args.read_token.strip()
    write_token = args.write_token.strip()

    if not read_token:
        print(
            "NOTICE: --read-token empty/absent. Exiting without checking (inert no-op until the secret exists).",
            file=sys.stderr,
        )
        sys.exit(0)

    if not write_token:
        write_token = read_token  # fallback: use the same token for both

    ensure_label(LABEL, LABEL_COLOR, LABEL_DESCRIPTION, write_token, args.dry_run)

    if args.dry_run:
        open_titles: set[str] = set()
    else:
        open_titles = open_issues(LABEL, write_token)

    any_error = False
    now = datetime.now(timezone.utc)
    per_repo_findings: dict[str, dict[str, str]] = {}

    for repo, branch, path in build_roster():
        try:
            content = fetch_file(repo, branch, path, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {repo}/{path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        if content is None:
            print(f"WARN: {repo}/{path} not found — skipping (structural drift already covers this)")
            continue

        cron = extract_cron(content)
        if cron is None:
            print(f"WARN: {repo}/{path}: no cron schedule found, skipping")
            continue

        cadence = cron_cadence_days(cron, content)
        if cadence is None:
            print(f"WARN: {repo}/{path}: unparsable cron {cron!r}, skipping")
            continue

        try:
            last_run = fetch_last_scheduled_run(repo, os.path.basename(path), read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching run history for {repo}/{path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        last_iso, last_conclusion = last_run if last_run else (None, None)
        reason = check_liveness(cadence, last_iso, last_conclusion, now=now)
        if reason:
            print(f"STALE: {repo}/{path}: {reason}")
            per_repo_findings.setdefault(repo, {})[path] = reason
        else:
            print(f"OK:    {repo}/{path}")

    for repo, findings in per_repo_findings.items():
        title = _issue_title(repo)
        if title in open_titles:
            print(f"SKIP:  issue already open for {repo} (dedup)")
        else:
            file_issue(repo, findings, write_token, args.dry_run)

    if any_error:
        sys.exit(1)
    # Always exit 0 on staleness found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
