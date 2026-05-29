"""Gap-scanner run-book orchestrator (skeleton).

Scans the curated repo-list read-only via the repo-scan seam and exits clean. No
proposal logic yet (#17): this run files zero issues. Later (#20) it will detect
recurring needs, run the sanitizer guard, then the proposal gate, and file at
most one generalized proposal. The scan is read-only and the working area is
cleaned up, so private code is never auto-discovered or retained.
"""

from runbooks.lib.repo_scan import scan


def run(repo_list, clone, file_issue=None):
    """Scan the listed repos and return a summary of the run.

    ``clone`` is the injected shallow-clone function; ``file_issue`` is the
    injected tracker (unused in this skeleton — kept so #20 can wire it without
    changing the signature). Returns ``scanned`` (repos cloned), ``filed`` (issue
    count, always 0 here), and ``workdir`` (the now-removed scratch path).
    """
    with scan(repo_list, clone) as result:
        scanned = list(result.repos)
        # No proposal logic yet — file nothing.
        workdir = result.workdir
    return {"scanned": scanned, "filed": 0, "workdir": workdir}
