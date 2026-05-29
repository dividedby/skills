"""Self-improvement run-book orchestrator.

Reads the agent-research knowledge base and this repo, asks an injected
``build_map`` step (the agent's analysis) to produce the integration map, and
writes/commits it consumer-side. It may then run a proposal step: an injected
``find_refinements`` analysis diffs the committed map against current reality,
the *real* proposal gate picks at most one, and that one is filed through the
injected tracker seam under the ``source:self-improvement`` provenance label.

The producer/decider split (ADR 0003) is structural: the only mutations this
orchestrator can make are the committed map (analysis/bookkeeping) and a filed
issue. It has no skill-write seam, so it can never edit or merge a skill — it
proposes via an issue and stops. All I/O (reading, map store path, git commit,
tracker) is injected so the whole workflow is testable on fixtures + fakes.
"""

from runbooks.lib.map_store import write_map
from runbooks.lib.proposal_gate import decide

#: Provenance label this run-book files under and reads back to dedup. Distinct
#: from the triage roles in docs/agents/triage-labels.md; follows the
#: ``source:architecture-review`` convention. Created idempotently by the runner.
SOURCE_LABEL = "source:self-improvement"
#: Triage role applied so a freshly filed proposal enters the triage state machine.
TRIAGE_LABEL = "needs-triage"


def run(
    kb_reader,
    repo_reader,
    build_map,
    map_path,
    commit,
    find_refinements=None,
    open_issues=None,
    file_issue=None,
    min_priority=1,
):
    """Build/refresh the integration map, then optionally file one refinement.

    The analysis half (``build_map`` → ``write_map`` → ``commit`` if changed) is
    always run. The proposal half runs only when both ``find_refinements`` and
    ``file_issue`` are supplied; without them this is the #16 analysis-only run.

    ``find_refinements(map_content, kb, repo)`` is the agent's analysis step (it
    may delegate to ``improve-codebase-architecture``); it returns candidate dicts
    carrying ``dedup_key``, ``priority``, ``title`` and ``body``. ``open_issues()``
    returns dedup keys already open under :data:`SOURCE_LABEL`. The real proposal
    gate picks at most one; it is filed via ``file_issue(payload)`` with both the
    provenance and triage labels attached.

    Returns ``{"changed": bool, "filed": int}`` — ``filed`` is 0 or 1.
    """
    kb = kb_reader()
    repo = repo_reader()
    content = build_map(kb, repo)
    changed = write_map(map_path, content)
    if changed:
        commit(map_path)

    filed = 0
    if find_refinements is not None and file_issue is not None:
        candidates = find_refinements(content, kb, repo)
        open_keys = open_issues() if open_issues is not None else []
        chosen = decide(candidates, open_keys, min_priority=min_priority)["file"]
        if chosen is not None:
            file_issue(
                {
                    "title": chosen["title"],
                    "body": chosen["body"],
                    "labels": [SOURCE_LABEL, TRIAGE_LABEL],
                }
            )
            filed = 1

    return {"changed": changed, "filed": filed}
