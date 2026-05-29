"""Gap-scanner run-book orchestrator.

Scans the curated repo-list read-only via the repo-scan seam, asks an injected
``find_needs`` analysis step to surface recurring cross-repo needs, runs the
*real* sanitizer guard then the *real* proposal gate, and files at most one
generalized new-skill proposal under the ``source:gap-scanner`` provenance label.

Two structural guarantees: the scan is read-only and the scratch area is removed
on exit (private code is never auto-discovered or retained), and the sanitizer
runs *before* the gate so a draft carrying private content is dropped before it
can be filed. All I/O (clone, tracker) is injected so the workflow is testable on
fixture repos + fakes; the clone targets the VPS runner in production (ADR 0003).
"""

from runbooks.lib.proposal_gate import decide
from runbooks.lib.repo_scan import scan
from runbooks.lib.sanitizer import check

#: Provenance label this run-book files under and reads back to dedup. Distinct
#: from the triage roles in docs/agents/triage-labels.md; follows the
#: ``source:architecture-review`` convention. Created idempotently by the runner.
SOURCE_LABEL = "source:gap-scanner"
#: Triage role applied so a freshly filed proposal enters the triage state machine.
TRIAGE_LABEL = "needs-triage"


def run(
    repo_list,
    clone,
    find_needs=None,
    open_issues=None,
    file_issue=None,
    private_markers=(),
    min_priority=1,
):
    """Scan the listed repos, then optionally file one generalized proposal.

    The scan half (shallow-clone each repo into a scratch area, clean up on exit)
    always runs. The proposal half runs only when both ``find_needs`` and
    ``file_issue`` are supplied; without them this is the #17 scan-only skeleton.

    ``find_needs(repos)`` is the agent's analysis step — ``repos`` maps repo name
    to its cloned path (read-only); it judges recurrence and returns candidate
    dicts carrying ``dedup_key``, ``priority``, ``title`` and ``body``. A
    candidate's ``title`` and ``body`` (both published) are run together through
    the *real* sanitizer (``private_markers`` always supplied); any that leaks
    private content is dropped before the gate sees it.
    The *real* proposal gate then picks at most one of the survivors, filed via
    ``file_issue(payload)`` with the provenance and triage labels attached.

    Returns ``{"scanned": [...], "filed": int, "workdir": Path}`` — ``filed`` is
    0 or 1, ``workdir`` is the now-removed scratch path.
    """
    filed = 0
    with scan(repo_list, clone) as result:
        scanned = list(result.repos)
        if find_needs is not None and file_issue is not None:
            candidates = find_needs(result.repos)
            # Sanitizer first: drop any draft that leaks private content, so the
            # gate only ever chooses among drafts safe to file publicly. Both the
            # title and the body are published, so both must clear the guard.
            clean = [
                c
                for c in candidates
                if check(
                    f"{c['title']}\n{c['body']}", private_markers=private_markers
                )["allowed"]
            ]
            open_keys = open_issues() if open_issues is not None else []
            chosen = decide(clean, open_keys, min_priority=min_priority)["file"]
            if chosen is not None:
                file_issue(
                    {
                        "title": chosen["title"],
                        "body": chosen["body"],
                        "labels": [SOURCE_LABEL, TRIAGE_LABEL],
                    }
                )
                filed = 1
        workdir = result.workdir
    return {"scanned": scanned, "filed": filed, "workdir": workdir}
