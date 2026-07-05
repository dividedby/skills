"""Divergence-detection guard for vendored Claude-powered workflow files.

Reads each consumer repo's vendored workflow files via the GitHub API and
checks each against a set of required structural anchors. Also resolves the
``claude-loops-v1`` tag and diffs both the reusable bodies (tag vs main) and
each consumer's own resolved pin (vs main) for content drift (#524). Opens a
single ``workflow-drift`` issue in dividedby/skills per drifted repo, plus one
shared issue for tag-vs-main drift. Report only — never a hard CI gate, never
auto-fix.

Prerequisites
-------------
- ISSUES_TOKEN: fine-grained PAT, owner dividedby, all repositories,
  Contents:Read + Issues:Write. Passed as --read-token.
  Until the secret is created the job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_workflow_drift.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
import difflib
import os
import re
import sys
from datetime import datetime, timezone

try:
    from tools._drift_common import ensure_label, fetch_file, open_issues, resolve_tag_sha
    from tools._drift_common import file_issue as _file_issue_io
except ImportError:
    from _drift_common import ensure_label, fetch_file, open_issues, resolve_tag_sha
    from _drift_common import file_issue as _file_issue_io

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

# The skills repo itself (used as a local-read canary; not in REPOS because
# skills' own caller stubs use a local `./` ref, not `@claude-loops-v1`).
SKILLS_REPO = "dividedby/skills"
SKILLS_BRANCH = "main"

# Workflow paths relative to repo root.
APPLY_PATH = ".github/workflows/apply-agent-research.yml"
ARCH_PATH = ".github/workflows/improve-codebase-architecture.yml"
STALE_PATH = ".github/workflows/staleness-review.yml"

# Reusable body paths (local to skills; not vendored to consumers).
ARCH_BODY_PATH = ".github/workflows/improve-codebase-architecture-reusable.yml"
STALE_BODY_PATH = ".github/workflows/staleness-review-reusable.yml"
APPLY_BODY_PATH = ".github/workflows/apply-agent-research-reusable.yml"

# Anchor sets: substrings that MUST appear in every non-missing file.
#
# apply-agent-research.yml (thin caller stubs — consumer repos + skills canary):
#   - "permissions:" + "issues: write" → missing == #384 startup-fail class
#   - "@claude-loops-v1" → missing == stub points at wrong ref or is full-copy OLD-gen
#     (skipped for skills canary via SKILLS_SKIP_ANCHORS — it uses local `./` ref)
#   - "CLAUDE_CODE_OAUTH_TOKEN" → missing == token not passed through
#
# improve-codebase-architecture.yml (consumer stubs only, not skills canary):
#   - "permissions:" + "issues: write" → startup-fail class (#384)
#   - "@claude-loops-v1" → missing == stub points at wrong ref or is full-copy OLD-gen
#   - "CLAUDE_CODE_OAUTH_TOKEN" → missing == token not passed through
#
# staleness-review.yml (consumer stubs only, not skills canary):
#   same as improve-codebase-architecture stubs

ANCHORS: dict[str, list[str]] = {
    APPLY_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
    ARCH_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
    STALE_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
}

# Anchors for the reusable body files (local to skills; hardened form — C-1/C-2/C-3).
#
# C-1 — SHA-pinned actions: no movable tag (actions/checkout@v + digit is the old form).
# C-2 — acceptEdits absent: proposal loops must not carry --permission-mode acceptEdits.
# C-3 — scoped allowedTools: no bare Bash(git:*) or Bash(python3:*) wildcard.
#   - "Bash(git log:*)" is the narrowest read-only git anchor present in both bodies.
#   - "Bash(python3 $SKILL_DIR" is present only in staleness-review (scoped to lib/).
#     arch-review has no python3 tool grant — its absence is verified by asserting
#     "Bash(python3:*)" does NOT appear (checked as a "must-not" anchor separately below).
BODY_ANCHORS: dict[str, list[str]] = {
    ARCH_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout (40-char hex after @).
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git (at least one specific read-only subcommand present).
        "Bash(git log:*)",
    ],
    STALE_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout.
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git and scoped python3.
        "Bash(git log:*)",
        "Bash(python3 $SKILL_DIR/lib/:*)",
    ],
    APPLY_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout (40-char hex after @).
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git (at least one specific read-only subcommand present).
        "Bash(git log:*)",
        # C-3: scoped python3 (skill's own cli.py).
        "Bash(python3 $SKILL_DIR/lib/cli.py:*)",
        # Harness prompt fetched fresh from the skills clone (not from local checkout).
        # The file uses $HARNESS/prompts/apply-agent-research.md — match the path suffix.
        "prompts/apply-agent-research.md",
    ],
}

# Must-NOT-appear anchors for the reusable bodies (hardened form violations).
BODY_FORBIDDEN: dict[str, list[str]] = {
    ARCH_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits in propose-only loop
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: arch-review has no python3 grant
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh search:*)",             # C-3: prompt uses only gh issue list/view; search not needed
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
    STALE_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits in propose-only loop
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: bare python3 wildcard replaced by scoped path
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh search:*)",             # C-3: prompt uses only gh issue list/view; search not needed
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
    APPLY_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits — loop files via guarded cli.py shim
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: bare python3 wildcard replaced by scoped path
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
}

# Anchors to skip when checking skills' OWN caller stubs.  Skills uses a local
# `./` ref by design (canary — always runs the latest body) rather than
# @claude-loops-v1, so that tag is not expected there.
SKILLS_SKIP_ANCHORS: set[str] = {"@claude-loops-v1"}

# Per-CONSUMER-repo anchor skips (distinct from SKILLS_SKIP_ANCHORS above, which
# is for skills' own canary stubs). Currently empty: every consumer — including
# agent-research, which floated its pin off the #470 SHA back to the
# `@claude-loops-v1` tag literal (goodreads-bot#668 follow-on) — now carries the
# tag literal, so no repo needs an anchor waived. The pin-drift lane below
# (extract_pin/resolve_effective_ref) still catches a stray SHA pin's drift if
# one is ever reintroduced.
REPO_SKIP_ANCHORS: dict[str, set[str]] = {}

# The reusable-rail tag consumers pin against (ADR 0029). A SHA-hex pin (with a
# trailing `# claude-loops-v1` comment) resolves to itself; a literal tag pin
# resolves to whatever commit the tag currently points at.
TAG_NAME = "claude-loops-v1"
SHA_RE = re.compile(r"[0-9a-f]{40}")

# Reusable body each caller stub's `uses:` line points at — used by the
# pin-drift lane to know which body to diff a resolved pin against.
STUB_TO_BODY: dict[str, str] = {
    APPLY_PATH: APPLY_BODY_PATH,
    ARCH_PATH: ARCH_BODY_PATH,
    STALE_PATH: STALE_BODY_PATH,
}

LABEL = "workflow-drift"
LABEL_COLOR = "E11D48"  # red-ish; distinct from the purple proposal labels
LABEL_DESCRIPTION = "Vendored workflow has drifted from required structural anchors"
SKILLS_REPO_WRITE = SKILLS_REPO  # issues are always filed here

# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no I/O)
# ---------------------------------------------------------------------------


def check_file(content: str, anchors: list[str], skip: set[str] | None = None) -> list[str]:
    """Return the list of anchors missing from *content*.

    Args:
        content: The decoded text of the workflow file.
        anchors: Required substrings.
        skip:    Anchors to ignore (used for the skills canary stubs).

    Returns:
        Ordered list of missing anchors (empty == clean).
    """
    skip = skip or set()
    return [a for a in anchors if a not in skip and a not in content]


def check_forbidden(content: str, forbidden: list[str]) -> list[str]:
    """Return the list of forbidden substrings that ARE present in *content*.

    Used to enforce hardened-form must-not-appear rules (C-2, C-3).

    Args:
        content:   The decoded text of the workflow file.
        forbidden: Substrings that must NOT appear.

    Returns:
        Ordered list of violated (present) forbidden substrings (empty == clean).
    """
    return [f for f in forbidden if f in content]


def extract_pin(stub_content: str, body_filename: str) -> str | None:
    """Extract a caller stub's `uses:` ref pin for *body_filename*, or ``None``.

    Matches ``uses: dividedby/skills/.github/workflows/<body_filename>@<pin>``.
    A trailing ``# comment`` (e.g. ``# claude-loops-v1``) is not captured — only
    the pin itself (a tag literal or a 40-char SHA) is returned. ``None`` means
    no matching `uses:` line was found for *body_filename* specifically.
    """
    pattern = rf"uses:\s*dividedby/skills/\.github/workflows/{re.escape(body_filename)}@(\S+)"
    match = re.search(pattern, stub_content)
    return match.group(1) if match else None


def is_sha_pin(pin: str) -> bool:
    """True if *pin* is a full 40-char hex SHA rather than the movable tag literal."""
    return bool(SHA_RE.fullmatch(pin))


def resolve_effective_ref(pin: str, tag_sha: str) -> str | None:
    """Resolve a stub's pin to the commit SHA its body is actually fetched at.

    A SHA pin resolves to itself; the exact tag literal resolves to *tag_sha*.
    Any other pin (a different tag, a typo, uppercase hex) is unexpected and
    returns ``None`` — the caller raises a loud "(unexpected pin)" finding
    rather than silently treating it as the tag, which would mask a wrong pin.
    """
    if is_sha_pin(pin):
        return pin
    if pin == TAG_NAME:
        return tag_sha
    return None


def tag_age_days(commit_iso_date: str, now: datetime | None = None) -> int:
    """Days between *commit_iso_date* (ISO 8601, ``Z``-suffixed) and *now*.

    *now* is injectable for deterministic tests; defaults to the current UTC time.
    """
    commit_dt = datetime.fromisoformat(commit_iso_date.replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    return (now - commit_dt).days


def body_diff(
    main_content: str, other_content: str, path: str, other_label: str = TAG_NAME
) -> str:
    """Unified diff of *other_content* against *main_content*; "" if identical.

    *other_label* names the non-main side in the diff header (defaults to the
    tag name; pass the resolved ref for a consumer-pin diff so a non-tag SHA
    isn't mislabeled as the tag).
    """
    if main_content == other_content:
        return ""
    diff = difflib.unified_diff(
        main_content.splitlines(keepends=True),
        other_content.splitlines(keepends=True),
        fromfile=f"main:{path}",
        tofile=f"{other_label}:{path}",
    )
    return "".join(diff)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
#
# fetch_file, ensure_label, open_issues are shared with check_label_drift.py
# and check_idea_inbox_drift.py — see tools/_drift_common.py (#526).


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a drifted repo (used for dedup and create)."""
    short = repo.split("/")[-1]
    return f"[workflow-drift] {short}: vendored workflows have diverged"


def build_issue_body(repo: str, drifted: dict[str, list[str]]) -> str:
    """Build the markdown body for a workflow-drift issue.

    *drifted* maps filename → list of missing anchors.
    """
    lines = [
        f"## Workflow drift detected in `{repo}`",
        "",
        "The following vendored workflow files have drifted — missing required",
        "structural anchors and/or a `uses:` pin that no longer resolves to `main`.",
        "This is an automated report from the weekly `check-workflow-drift` job",
        "([`tools/check_workflow_drift.py`](../../tools/check_workflow_drift.py)).",
        "",
    ]
    for path, missing in sorted(drifted.items()):
        lines.append(f"### `{path}`")
        lines.append("")
        lines.append("Findings:")
        for anchor in missing:
            lines.append(f"- `{anchor}`")
        lines.append("")
    lines += [
        "### What to do",
        "",
        "1. Open the file in the repo and compare it against the canonical version in `dividedby/skills`.",
        "2. Restore any missing anchors (or confirm they were intentionally removed and update the anchor set).",
        "3. Close this issue once the file is clean.",
        "",
        "Reference: [`docs/agents/vendored-workflows.md`](../../docs/agents/vendored-workflows.md),",
        "[ADR 0014](../../docs/adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md).",
    ]
    return "\n".join(lines)


def file_issue(
    repo: str, drifted: dict[str, list[str]], write_token: str, dry_run: bool
) -> None:
    """Open or print a drift issue for *repo* in skills.

    *drifted* maps filename → list of missing anchors.
    """
    title = _issue_title(repo)
    body = build_issue_body(repo, drifted)
    dry_run_extra = [
        f"  {path}: missing {missing}" for path, missing in sorted(drifted.items())
    ]
    _file_issue_io(
        SKILLS_REPO_WRITE, title, body, LABEL, write_token, dry_run, dry_run_extra
    )


def _tag_issue_title() -> str:
    """Deterministic issue title for tag-vs-main drift (used for dedup and create)."""
    return f"[workflow-drift] {TAG_NAME} tag: reusable body has diverged from main"


def build_tag_issue_body(tag_sha: str, tag_age: int, body_diffs: dict[str, str]) -> str:
    """Build the markdown body for the single tag-vs-main drift issue.

    *body_diffs* maps reusable-body path → unified diff text (main vs the
    commit `tag_sha` points at).
    """
    lines = [
        f"## `{TAG_NAME}` tag has diverged from `main`",
        "",
        f"The `{TAG_NAME}` tag (currently `{tag_sha}`, {tag_age} days old) points at a "
        "commit whose reusable-body content no longer matches `main`. Consumers pinned to "
        "the tag are running the OLD body until it's moved.",
        "This is an automated report from the weekly `check-workflow-drift` job",
        "([`tools/check_workflow_drift.py`](../../tools/check_workflow_drift.py)).",
        "",
    ]
    for path, diff in sorted(body_diffs.items()):
        lines.append(f"### `{path}`")
        lines.append("")
        lines.append("```diff")
        lines.append(diff.rstrip("\n"))
        lines.append("```")
        lines.append("")
    lines += [
        "### What to do",
        "",
        "1. Confirm the drifted content on `main` is intentional and ready to ship to consumers.",
        f"2. Move the `{TAG_NAME}` tag per the tag-move process under the reusable-rail epic (#516).",
        "3. Close this issue once the tag has moved and this check reports clean.",
    ]
    return "\n".join(lines)


def file_tag_issue(
    tag_sha: str,
    tag_age: int,
    body_diffs: dict[str, str],
    write_token: str,
    dry_run: bool,
) -> None:
    """Open or print the single tag-vs-main drift issue.

    *body_diffs* maps reusable-body path → unified diff text.
    """
    title = _tag_issue_title()
    body = build_tag_issue_body(tag_sha, tag_age, body_diffs)
    dry_run_extra = [f"  {path}: diverged from main" for path in sorted(body_diffs)]
    _file_issue_io(
        SKILLS_REPO_WRITE, title, body, LABEL, write_token, dry_run, dry_run_extra
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check vendored Claude workflow files for structural drift."
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
            "NOTICE: --read-token empty/absent. Exiting without checking (inert no-op until the secret exists).",
            file=sys.stderr,
        )
        sys.exit(0)

    if not write_token:
        write_token = read_token  # fallback: use the same token for both

    # Ensure the label exists before we need it.
    ensure_label(LABEL, LABEL_COLOR, LABEL_DESCRIPTION, write_token, args.dry_run)

    # Fetch open drift issues once (used for dedup across all repos).
    if args.dry_run:
        open_titles: set[str] = set()
    else:
        open_titles = open_issues(LABEL, write_token)

    any_error = False
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Resolve the claude-loops-v1 tag once, up front — both the pin-drift lane
    # (per-consumer, below) and the tag-vs-main lane (after the REPOS loop)
    # need it. A resolution failure disables both lanes for this run but does
    # not block the anchor checks.
    tag_sha: str | None = None
    tag_iso_date = ""
    try:
        tag_sha, tag_iso_date = resolve_tag_sha(SKILLS_REPO, TAG_NAME, read_token)
    except (RuntimeError, OSError) as exc:
        print(f"ERROR resolving tag {TAG_NAME}: {exc}", file=sys.stderr)
        any_error = True

    # Main's copy of each reusable body, read from the local checkout (same
    # source the BODY_ANCHORS block below reads) — no extra fetch for "main".
    main_bodies: dict[str, str] = {}
    for body_path in (ARCH_BODY_PATH, STALE_BODY_PATH, APPLY_BODY_PATH):
        try:
            with open(os.path.join(repo_root, body_path), encoding="utf-8") as fh:
                main_bodies[body_path] = fh.read()
        except OSError as exc:
            print(f"ERROR reading local {body_path}: {exc}", file=sys.stderr)
            any_error = True

    # Each reusable body's content at the tag's commit, fetched once and reused
    # by every consumer whose pin resolves to the tag (the common case).
    # tag_fetch_failed tracks body paths whose tag-commit content this run
    # couldn't establish (transient gh failure, or a genuine 404 at the tag
    # commit itself) — distinct from a *consumer's own* pin being broken.
    tag_bodies: dict[str, str] = {}
    tag_body_diffs: dict[str, str] = {}
    tag_fetch_failed: set[str] = set()
    if tag_sha:
        for body_path, main_content in main_bodies.items():
            try:
                tag_content = fetch_file(SKILLS_REPO, tag_sha, body_path, read_token)
            except RuntimeError as exc:
                print(
                    f"ERROR fetching {SKILLS_REPO}/{body_path}@{tag_sha}: {exc}",
                    file=sys.stderr,
                )
                any_error = True
                tag_fetch_failed.add(body_path)
                continue
            if tag_content is None:
                print(f"WARN: {SKILLS_REPO}/{body_path}@{tag_sha} not found")
                tag_fetch_failed.add(body_path)
                continue
            tag_bodies[body_path] = tag_content
            diff = body_diff(main_content, tag_content, body_path)
            if diff:
                tag_body_diffs[body_path] = diff

    # Check consumer repos.
    for repo, branch in REPOS.items():
        drifted: dict[str, list[str]] = {}
        for path, anchors in ANCHORS.items():
            try:
                content = fetch_file(repo, branch, path, read_token)
            except RuntimeError as exc:
                print(f"ERROR fetching {repo}/{path}: {exc}", file=sys.stderr)
                any_error = True
                continue

            if content is None:
                print(f"WARN: {repo}/{path} not found (missing file is drift)")
                drifted[path] = [f"<file missing — expected at {path}>"]
                continue

            findings = check_file(content, anchors, skip=REPO_SKIP_ANCHORS.get(repo, set()))

            # Pin-drift lane: does this stub's `uses:` pin actually resolve to
            # content matching main? (Separate from the anchor check above,
            # which only looks for the literal tag substring.)
            body_path = STUB_TO_BODY[path]
            pin = extract_pin(content, os.path.basename(body_path))
            if pin is None:
                findings.append(f"{body_path} (pin unparsable)")
            elif tag_sha is None or body_path not in main_bodies:
                print(
                    f"WARN: {repo}/{path}: tag/main body unresolved, "
                    "skipping pin-drift check"
                )
            else:
                effective_ref = resolve_effective_ref(pin, tag_sha)
                if effective_ref is None:
                    # Neither the tag literal nor a SHA — e.g. claude-loops-v10,
                    # uppercase hex, a typo. Never silently fall back to the tag.
                    findings.append(f"{body_path} (unexpected pin: {pin})")
                elif effective_ref == tag_sha:
                    if body_path in tag_fetch_failed:
                        # Tag-commit content unavailable THIS RUN (transient gh
                        # failure or a 404 on the tag commit itself) — not this
                        # consumer's fault, so no finding; try again next run.
                        print(
                            f"WARN: {repo}/{path}: tag body for {body_path} unavailable "
                            "this run, skipping pin comparison"
                        )
                    else:
                        pinned_content = tag_bodies[body_path]
                        short_ref = effective_ref[:7]
                        diff = body_diff(
                            main_bodies[body_path], pinned_content, body_path, short_ref
                        )
                        if diff:
                            findings.append(
                                f"{body_path} (pin drift: resolved {short_ref})"
                            )
                else:
                    try:
                        pinned_content = fetch_file(
                            SKILLS_REPO, effective_ref, body_path, read_token
                        )
                    except RuntimeError as exc:
                        print(
                            f"ERROR fetching {SKILLS_REPO}/{body_path}"
                            f"@{effective_ref}: {exc}",
                            file=sys.stderr,
                        )
                        any_error = True
                        pinned_content = None

                    short_ref = effective_ref[:7]
                    if pinned_content is None:
                        findings.append(
                            f"{body_path} (broken pin: {effective_ref[:12]} not found)"
                        )
                    else:
                        diff = body_diff(
                            main_bodies[body_path], pinned_content, body_path, short_ref
                        )
                        if diff:
                            findings.append(
                                f"{body_path} (pin drift: resolved {short_ref})"
                            )

            if findings:
                print(f"DRIFT: {repo}/{path}: {findings}")
                drifted[path] = findings
            else:
                print(f"OK:    {repo}/{path}")

        if drifted:
            title = _issue_title(repo)
            if title in open_titles:
                print(f"SKIP:  issue already open for {repo} (dedup)")
            else:
                file_issue(repo, drifted, write_token, args.dry_run)

    # Tag-vs-main: one issue total, not per-repo (the tag is fleet-shared).
    if tag_body_diffs:
        # tag_body_diffs is only ever populated inside `if tag_sha:` above.
        assert tag_sha is not None
        tag_title = _tag_issue_title()
        if tag_title in open_titles:
            print(f"SKIP:  issue already open for {TAG_NAME} tag-vs-main drift (dedup)")
        else:
            file_tag_issue(
                tag_sha,
                tag_age_days(tag_iso_date),
                tag_body_diffs,
                write_token,
                args.dry_run,
            )
    elif tag_sha:
        print(f"OK:    {TAG_NAME} tag matches main")

    # Check skills' own caller stubs (canary; skip @claude-loops-v1 anchor).
    # APPLY_PATH is included here: it's a thin local-`./` caller (ADR 0029), so
    # @claude-loops-v1 is not expected and is skipped via SKILLS_SKIP_ANCHORS.
    for path in (ARCH_PATH, STALE_PATH, APPLY_PATH):
        anchors = ANCHORS[path]
        try:
            content = fetch_file(SKILLS_REPO, SKILLS_BRANCH, path, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {SKILLS_REPO}/{path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        if content is None:
            print(f"WARN: {SKILLS_REPO}/{path} not found")
            continue

        missing = check_file(content, anchors, skip=SKILLS_SKIP_ANCHORS)
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{path}: missing {missing}")
        else:
            print(f"OK:    {SKILLS_REPO}/{path}")

    # skills' own apply-agent-research.yml — also verify local file (canary).
    local_apply = os.path.join(repo_root, APPLY_PATH)
    try:
        with open(local_apply, encoding="utf-8") as fh:
            skills_apply_content = fh.read()
        missing = check_file(skills_apply_content, ANCHORS[APPLY_PATH], skip=SKILLS_SKIP_ANCHORS)
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{APPLY_PATH} (local): missing {missing}")
        else:
            print(f"OK:    {SKILLS_REPO}/{APPLY_PATH} (local)")
    except OSError as exc:
        print(f"ERROR reading local {APPLY_PATH}: {exc}", file=sys.stderr)
        any_error = True

    # skills' own reusable bodies — check hardened form (C-1/C-2/C-3 anchors).
    for body_path in (ARCH_BODY_PATH, STALE_BODY_PATH, APPLY_BODY_PATH):
        local_body = os.path.join(repo_root, body_path)
        try:
            with open(local_body, encoding="utf-8") as fh:
                body_content = fh.read()
        except OSError as exc:
            print(f"ERROR reading local {body_path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        missing = check_file(body_content, BODY_ANCHORS[body_path])
        present_forbidden = check_forbidden(body_content, BODY_FORBIDDEN[body_path])
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{body_path}: missing required anchors {missing}")
        if present_forbidden:
            print(f"DRIFT: {SKILLS_REPO}/{body_path}: forbidden patterns present {present_forbidden}")
        if not missing and not present_forbidden:
            print(f"OK:    {SKILLS_REPO}/{body_path}")

    if any_error:
        sys.exit(1)
    # Always exit 0 on drift found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
