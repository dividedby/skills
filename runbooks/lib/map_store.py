"""Map store: read/write the integration map for the self-improvement run-book.

The integration map is analysis the run-book auto-maintains (see CONTEXT.md). It
lives consumer-side in this repo, never in agent-research. This module owns only
the file I/O and the write-if-changed rule that keeps re-runs to a minimal diff;
git commit is injected by the run-book so the logic stays testable on a scratch
path.
"""

from pathlib import Path


def read_map(path):
    """Return the map's current content, or None if it does not exist yet."""
    p = Path(path)
    if not p.exists():
        return None
    return p.read_text()


def write_map(path, content):
    """Write ``content`` to ``path`` only if it differs from what's there.

    Returns True if the file was created or changed, False if it already matched
    (no write, no diff). This is what keeps a re-run from regenerating the whole
    map when nothing changed.
    """
    p = Path(path)
    if read_map(p) == content:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return True
