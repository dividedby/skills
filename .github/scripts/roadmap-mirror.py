#!/usr/bin/env python3
"""Roadmap mirror renderer + commit-if-changed write adapter (TEMPLATE — copy
into a consumer repo via the roadmap skill's bootstrap, then wire the workflow
in `roadmap-mirror.yml`). The working-tree `roadmap.md` stays the source of
record; this renders it into a read-only, machine-owned mirror issue body so the
backlog is glanceable from the GitHub web/phone UI without a clone (ADR 0020).

Two pieces, one seam:

- `render(roadmap_text) -> str` is **pure** (stdlib only, ADR 0004): no I/O, no
  `gh`, no clock. It prepends a read-only banner to the verbatim doc.
- `update_mirror(gh, issue, roadmap_text) -> bool` is the **commit-if-changed**
  adapter. Its only I/O is through the injected `gh` object (a `_GhCli` in
  production, a fake in tests), so the suite never makes a live call. It fetches
  the current body, compares against the freshly rendered body, and PATCHes only
  on a difference — returning whether it wrote.

Run as a script in CI: `python3 roadmap-mirror.py <issue-number> [roadmap-path]`.
"""
import subprocess
import sys

# --- config (edit per repo) -------------------------------------------------
ROADMAP_PATH = "docs/plans/roadmap.md"  # where the roadmap doc lives
# ---------------------------------------------------------------------------

BANNER = (
    "> **Read-only mirror — edit the doc, not this issue.** This body is "
    "rendered from the working-tree roadmap by CI on every push (ADR 0020); "
    "any manual edit here is overwritten on the next push. To change the "
    "backlog, edit the roadmap doc and open a PR.\n\n---\n\n"
)


def render(roadmap_text: str) -> str:
    """roadmap.md text -> mirror issue body text. Pure: prepends the read-only
    banner to the verbatim doc so the census is carried through unchanged and
    stays glanceable. Trailing whitespace is normalized so a doc that gains or
    loses a trailing newline doesn't churn the mirror."""
    return BANNER + roadmap_text.rstrip() + "\n"


def update_mirror(gh, issue, roadmap_text: str) -> bool:
    """Commit-if-changed: render the doc, fetch the mirror's current body, and
    PATCH only when they differ. `gh` is the injected write seam (must expose
    `fetch_body(issue)` and `patch_body(issue, body)`). Returns True iff a write
    happened."""
    desired = render(roadmap_text)
    current = gh.fetch_body(issue)
    if (current or "").strip() == desired.strip():
        return False
    gh.patch_body(issue, desired)
    return True


class _GhCli:
    """Production gh-API seam: shells out to the `gh` CLI. Kept tiny and apart
    from the pure render so it is the only thing a fake replaces in tests."""

    def fetch_body(self, issue) -> str:
        out = subprocess.check_output(
            ["gh", "issue", "view", str(issue), "--json", "body",
             "--jq", ".body"],
            text=True)
        return out.rstrip("\n")

    def patch_body(self, issue, body: str) -> None:
        # `--body-file -` reads from stdin, avoiding argv length limits and
        # shell-escaping of the rendered markdown.
        subprocess.run(
            ["gh", "issue", "edit", str(issue), "--body-file", "-"],
            input=body, text=True, check=True)


def main(argv) -> int:
    if not argv:
        print("usage: roadmap-mirror.py <issue-number> [roadmap-path]",
              file=sys.stderr)
        return 2
    issue = argv[0]
    path = argv[1] if len(argv) > 1 else ROADMAP_PATH
    with open(path, encoding="utf-8") as fh:
        roadmap_text = fh.read()
    wrote = update_mirror(_GhCli(), issue, roadmap_text)
    print(f"mirror #{issue}: {'updated' if wrote else 'unchanged'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
