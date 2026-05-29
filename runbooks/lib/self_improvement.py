"""Self-improvement run-book orchestrator.

Reads the agent-research knowledge base and this repo, asks an injected
``build_map`` step (the agent's analysis) to produce the integration map, and
writes/commits it consumer-side. Analysis only: this orchestrator has no tracker
seam, so it can never file an issue or change a skill — the producer/decider
split (ADR 0003) is structural here. All I/O (reading, the map store path, git
commit) is injected so the orchestration is testable on fixtures + a scratch
path.
"""

from runbooks.lib.map_store import write_map


def run(kb_reader, repo_reader, build_map, map_path, commit):
    """Build/refresh the integration map for one run.

    Returns ``{"changed": bool}`` — True when the map was created or updated
    (and therefore committed), False when a re-run produced an identical map.
    """
    kb = kb_reader()
    repo = repo_reader()
    content = build_map(kb, repo)
    changed = write_map(map_path, content)
    if changed:
        commit(map_path)
    return {"changed": changed}
