"""Repo-scan seam for the gap-scanner run-book.

Scans only a curated repo-list, shallow-clones each repo read-only into a scratch
working area via an injected ``clone`` function, and removes everything at end of
run. Private code is never auto-discovered (only listed repos are touched) and
never retained (the working area is cleaned up). The actual git clone is injected
so the seam is testable against local fixture directories.
"""

import json
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


def load_repo_list(path):
    """Return the curated list of repos to scan from a JSON config.

    The config is an explicit ``{"repos": [...]}`` allow-list — the scanner never
    auto-discovers repos. A missing config fails safe to an empty list (scan
    nothing), never to "everything the maintainer owns".
    """
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text()).get("repos", [])


@dataclass
class ScanResult:
    workdir: Path
    repos: dict = field(default_factory=dict)  # name -> cloned Path


@contextmanager
def scan(repo_list, clone):
    """Clone each repo named in ``repo_list`` into a temporary working area and
    yield a :class:`ScanResult`. The working area is always removed on exit.

    ``clone(name, dest)`` performs a shallow read-only clone of ``name`` into the
    path ``dest``; if it raises (e.g. an unreachable repo), that repo is skipped
    and the run continues. Repos not in ``repo_list`` are never touched.
    """
    workdir = Path(tempfile.mkdtemp(prefix="gap-scan-"))
    result = ScanResult(workdir=workdir)
    try:
        for name in repo_list:
            dest = workdir / name
            try:
                clone(name, dest)
            except Exception:
                continue
            result.repos[name] = dest
        yield result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
