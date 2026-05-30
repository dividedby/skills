"""KB-source seam for the self-improvement run-book.

Pins the acquisition contract C reads: which knowledge base, and which
``knowledge/`` subpaths within it. Like the gap-scanner's repo allow-list, the
subpaths are an explicit allow-list — the reader never auto-discovers subjects
or categories on disk. The KB root is injected (the VPS clones the KB via a
deploy key, ADR 0003), so the reader is testable against a local fixture tree.
"""

import json
from pathlib import Path


def load_kb_source(path):
    """Return the KB acquisition contract from a JSON config.

    The config names the KB (``kb``, an ``owner/name`` slug) and an explicit
    ``subpaths`` allow-list of ``knowledge/`` directories to read — never
    auto-discovered. A missing config fails safe to "read nothing" (no kb, no
    subpaths), never to "everything under the KB root".
    """
    p = Path(path)
    if not p.exists():
        return {"kb": None, "subpaths": []}
    data = json.loads(p.read_text())
    return {"kb": data.get("kb"), "subpaths": data.get("subpaths", [])}


def read_kb(root, subpaths):
    """Read the configured ``knowledge/`` subpaths under ``root`` into a stable list.

    Walks only the ``subpaths`` named in the contract (no auto-discovery): a
    directory present under ``root`` but absent from ``subpaths`` is never read.
    Each ``*.md`` note becomes a record ``{"subpath", "subject", "category",
    "name", "text"}``. ``subject``/``category`` are the two domain axes the
    integration map is built on (``skill ↔ practice/artifact``), derived from the
    ``knowledge/<subject>/<category>`` layout so consumers never re-parse the
    path; a subpath that doesn't carry both segments leaves them ``None``. The
    result is sorted by ``(subpath, name)`` so a re-run produces a minimal diff,
    not a reordered rewrite. A configured subpath missing on disk is skipped, not
    fatal (the KB may not yet carry every listed subject).
    """
    root = Path(root)
    notes = []
    for subpath in subpaths:
        d = root / subpath
        if not d.is_dir():
            continue
        parts = subpath.strip("/").split("/")
        category = parts[-1] if parts else None
        subject = parts[-2] if len(parts) >= 2 else None
        for f in d.glob("*.md"):
            notes.append(
                {
                    "subpath": subpath,
                    "subject": subject,
                    "category": category,
                    "name": f.name,
                    "text": f.read_text(),
                }
            )
    notes.sort(key=lambda n: (n["subpath"], n["name"]))
    return notes
