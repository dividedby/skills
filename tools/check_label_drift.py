"""Fleet-wide REPORT-ONLY label-doc drift detector.

Reads each consumer repo's ``docs/agents/`` label docs via the GitHub API and
checks for four drift shapes. Opens a single ``label-drift`` issue in
dividedby/skills per drifted repo, naming ``setup-dividedby-skills`` as the
fixer. Never mutates a consumer repo.

Prerequisites
-------------
- DRIFT_CHECK_TOKEN: fine-grained PAT, owner dividedby, repositories:
  moodreader + agent-research + goodreads-bot + skills,
  Contents:Read + Issues:Write on skills. Until this secret is created the
  job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_label_drift.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
import base64
import enum
import os
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Repos to audit, mapped to their default branch.
# Confirmed 2026-06-20 via `gh repo view dividedby/<repo> --json defaultBranchRef`.
# ponytail: archived repos dropped by hand; if more get archived, skip via
#   gh api repos/<r> -q .archived
REPOS: dict[str, str] = {
    "dividedby/moodreader": "main",
    "dividedby/agent-research": "main",
    "dividedby/goodreads-bot": "staging",
}

SKILLS_REPO = "dividedby/skills"
SKILLS_REPO_WRITE = SKILLS_REPO  # issues are always filed here

# Label-doc paths relative to repo root (consumer convention).
# The correct form for consumer repos is triage-labels.md only.
# labels.md is the canonical source in skills; it must NOT appear in consumers.
TRIAGE_LABELS_PATH = "docs/agents/triage-labels.md"
LABELS_PATH = "docs/agents/labels.md"

# Substrings that must appear in a well-formed triage-labels.md.
# Each entry identifies one of the three required tiers.
TIER_MARKERS: list[str] = [
    "## CORE",      # real heading: "## CORE — State (all repos)" (multiple CORE subsections)
    "## LOOP",      # real heading: "## LOOP/NETWORK (full-tier repos)" — slash form in heading,
                    # hyphen form (LOOP-NETWORK) used in prose throughout the repo
    "## CHANNELS",  # real heading: "## CHANNELS (owned by `dividedby/skills`, applied by consumers)"
]

LABEL = "label-drift"
LABEL_COLOR = "D93F0B"  # orange-red; distinct from workflow-drift's rose
LABEL_DESCRIPTION = "Label-convention doc has drifted from the required dividedby structure"


# ---------------------------------------------------------------------------
# Drift classification (pure; no I/O)
# ---------------------------------------------------------------------------


class DriftShape(enum.Enum):
    """The four recognised drift shapes for consumer label docs."""
    STRAY_LABELS_MD = "stray_labels_md"
    MISSING_TIERS = "missing_tiers"
    LABELS_MD_ONLY = "labels_md_only"
    BOTH_MISSING = "both_missing"


def classify_drift(
    labels_md: Optional[str],
    triage_labels_md: Optional[str],
) -> Optional[DriftShape]:
    """Classify the label-doc state of a consumer repo into a drift shape.

    Returns a DriftShape if drift is detected, or None if the repo is clean.
    Exactly one shape is returned per repo (stray takes precedence when both
    files are present, regardless of triage-labels.md content).

    Args:
        labels_md: Content of docs/agents/labels.md, or None if absent.
        triage_labels_md: Content of docs/agents/triage-labels.md, or None if absent.
    """
    both_present = labels_md is not None and triage_labels_md is not None
    triage_only = labels_md is None and triage_labels_md is not None
    labels_only = labels_md is not None and triage_labels_md is None
    both_absent = labels_md is None and triage_labels_md is None

    if both_present:
        return DriftShape.STRAY_LABELS_MD

    if labels_only:
        return DriftShape.LABELS_MD_ONLY

    if both_absent:
        return DriftShape.BOTH_MISSING

    if triage_only:
        missing = [m for m in TIER_MARKERS if m not in triage_labels_md]
        if missing:
            return DriftShape.MISSING_TIERS
        return None

    return None  # unreachable, but satisfies type checker


def _missing_tiers(triage_labels_md: str) -> list[str]:
    """Return human-readable names of tier sections missing from *triage_labels_md*.

    Prose names use hyphen form (LOOP-NETWORK) matching the repo's prose convention;
    the real heading in the doc uses a slash (## LOOP/NETWORK).
    """
    names = {
        "## CORE": "CORE",
        "## LOOP": "LOOP-NETWORK",
        "## CHANNELS": "CHANNELS",
    }
    return [names[m] for m in TIER_MARKERS if m not in triage_labels_md]


# ---------------------------------------------------------------------------
# Issue helpers (pure; no I/O)
# ---------------------------------------------------------------------------


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a drifted repo (used for dedup and create)."""
    short = repo.split("/")[-1]
    return f"[label-drift] {short}: label-convention doc has drifted"


def build_issue_body(
    repo: str,
    shape: DriftShape,
    missing_tiers: list[str],
) -> str:
    """Build the markdown body for a label-drift issue.

    Names ``setup-dividedby-skills`` as the fixer in every case.
    """
    lines = [
        f"## Label-doc drift detected in `{repo}`",
        "",
        "This is an automated report from the weekly `check-label-drift` job",
        "([`tools/check_label_drift.py`](../../tools/check_label_drift.py)).",
        "",
    ]

    if shape == DriftShape.STRAY_LABELS_MD:
        lines += [
            "### Drift shape: stray `labels.md` present",
            "",
            f"Both `{LABELS_PATH}` and `{TRIAGE_LABELS_PATH}` exist in this repo.",
            f"`{LABELS_PATH}` is the canonical source that lives in `dividedby/skills`",
            "and must not be committed to consumer repos. Only `triage-labels.md` belongs here.",
            "",
        ]

    elif shape == DriftShape.MISSING_TIERS:
        tier_list = "\n".join(f"- {t}" for t in (missing_tiers or ["(unknown)"]))
        lines += [
            f"### Drift shape: `{TRIAGE_LABELS_PATH}` is missing required tier sections",
            "",
            f"`{TRIAGE_LABELS_PATH}` exists but does not contain all three required",
            "tiering sections (CORE / LOOP-NETWORK / CHANNELS).",
            "",
            "Missing tiers:",
            tier_list,
            "",
        ]

    elif shape == DriftShape.LABELS_MD_ONLY:
        lines += [
            "### Drift shape: only `labels.md` present, `triage-labels.md` absent",
            "",
            f"Only `{LABELS_PATH}` is present; `{TRIAGE_LABELS_PATH}` is missing.",
            "Consumer repos must carry `triage-labels.md` (the full dividedby content)",
            f"and must NOT carry `{LABELS_PATH}` (that file belongs to `dividedby/skills` only).",
            "",
        ]

    elif shape == DriftShape.BOTH_MISSING:
        lines += [
            "### Drift shape: both label docs absent",
            "",
            f"Neither `{LABELS_PATH}` nor `{TRIAGE_LABELS_PATH}` exists in this repo.",
            f"Consumer repos must carry `{TRIAGE_LABELS_PATH}` with the full",
            "dividedby CORE / LOOP-NETWORK / CHANNELS tiering structure.",
            "",
        ]

    lines += [
        "### What to do",
        "",
        "Run **`setup-dividedby-skills`** against this repo. That skill's",
        "**Concern D** reconciles the label-convention doc to the canonical",
        f"dividedby structure (seeded from `dividedby/skills {TRIAGE_LABELS_PATH}`",
        "via `docs/agents/labels.md`).",
        "",
        "Reference: [`docs/agents/labels.md`](../../docs/agents/labels.md),",
        "[`skills/config/setup-dividedby-skills/SKILL.md`](../../skills/config/setup-dividedby-skills/SKILL.md).",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _gh(args: list[str], token: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a ``gh`` subprocess with GH_TOKEN set to *token*."""
    full_env = {**os.environ, "GH_TOKEN": token}
    return subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=check,
        env=full_env,
    )


def fetch_file(repo: str, branch: str, path: str, read_token: str) -> Optional[str]:
    """Fetch *path* from *repo* at *branch* via the GitHub Contents API.

    Returns decoded text on success, or None if the file is missing (404).
    Raises RuntimeError on any other error.
    """
    api_path = f"repos/{repo}/contents/{path}"
    result = _gh(
        ["api", f"{api_path}?ref={branch}", "--jq", ".content"],
        token=read_token,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "404" in stderr or "Not Found" in stderr:
            return None
        raise RuntimeError(
            f"gh api {api_path}: exit {result.returncode}: {stderr}"
        )
    encoded = result.stdout.strip()
    if not encoded:
        return None
    # GitHub returns base64 with embedded newlines; strip them.
    decoded = base64.b64decode(encoded.replace("\n", "")).decode("utf-8")
    return decoded


def ensure_label(write_token: str, dry_run: bool) -> None:
    """Best-effort: create the label-drift label in skills if absent."""
    if dry_run:
        print(f"[dry-run] would ensure label '{LABEL}' in {SKILLS_REPO_WRITE}")
        return
    _gh(
        [
            "label", "create", LABEL,
            "--repo", SKILLS_REPO_WRITE,
            "--color", LABEL_COLOR,
            "--description", LABEL_DESCRIPTION,
        ],
        token=write_token,
        check=False,  # exits non-zero if label already exists; that's fine
    )


def open_issues_for_label_drift(write_token: str) -> set[str]:
    """Return the set of open issue titles tagged label-drift in skills."""
    result = _gh(
        [
            "issue", "list",
            "--repo", SKILLS_REPO_WRITE,
            "--label", LABEL,
            "--state", "open",
            "--json", "title",
            "--jq", ".[].title",
        ],
        token=write_token,
        check=False,
    )
    if result.returncode != 0:
        print(f"WARNING: could not fetch open issues: {result.stderr.strip()}", file=sys.stderr)
        return set()
    return set(result.stdout.strip().splitlines())


def file_issue(
    repo: str,
    shape: DriftShape,
    missing_tiers: list[str],
    write_token: str,
    dry_run: bool,
) -> None:
    """Open or print a label-drift issue for *repo* in skills."""
    title = _issue_title(repo)
    body = build_issue_body(repo, shape, missing_tiers)

    if dry_run:
        print(f"[dry-run] would file issue in {SKILLS_REPO_WRITE}:")
        print(f"  title: {title}")
        print(f"  shape: {shape.value}")
        if missing_tiers:
            print(f"  missing tiers: {missing_tiers}")
        return

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(body)
        body_path = fh.name
    try:
        result = _gh(
            [
                "issue", "create",
                "--repo", SKILLS_REPO_WRITE,
                "--title", title,
                "--body-file", body_path,
                "--label", LABEL,
            ],
            token=write_token,
        )
        url = result.stdout.strip().splitlines()[-1]
        print(f"Filed: {url}")
    finally:
        os.unlink(body_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check consumer repos' label-convention docs for drift."
    )
    parser.add_argument("--read-token", default="", help="PAT for cross-repo Contents:Read")
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
            "NOTICE: --read-token is empty. DRIFT_CHECK_TOKEN secret has not been created yet. "
            "Exiting without checking (inert no-op until the secret exists).",
            file=sys.stderr,
        )
        sys.exit(0)

    if not write_token:
        write_token = read_token  # fallback: use the same token for both

    # Ensure the label exists before we need it.
    ensure_label(write_token, args.dry_run)

    # Fetch open drift issues once (used for dedup across all repos).
    if args.dry_run:
        open_titles: set[str] = set()
    else:
        open_titles = open_issues_for_label_drift(write_token)

    any_error = False

    for repo, branch in REPOS.items():
        # Fetch both candidate label-doc files (None == absent).
        try:
            labels_md = fetch_file(repo, branch, LABELS_PATH, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {repo}/{LABELS_PATH}: {exc}", file=sys.stderr)
            any_error = True
            continue

        try:
            triage_labels_md = fetch_file(repo, branch, TRIAGE_LABELS_PATH, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {repo}/{TRIAGE_LABELS_PATH}: {exc}", file=sys.stderr)
            any_error = True
            continue

        shape = classify_drift(labels_md, triage_labels_md)

        if shape is None:
            print(f"OK:    {repo}")
            continue

        tiers = _missing_tiers(triage_labels_md) if (
            shape == DriftShape.MISSING_TIERS and triage_labels_md is not None
        ) else []

        print(f"DRIFT: {repo}: {shape.value}" + (f" (missing: {tiers})" if tiers else ""))

        title = _issue_title(repo)
        if title in open_titles:
            print(f"SKIP:  issue already open for {repo} (dedup)")
        else:
            file_issue(repo, shape, tiers, write_token, args.dry_run)

    if any_error:
        sys.exit(1)
    # Always exit 0 on drift found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
