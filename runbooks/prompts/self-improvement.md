# Self-improvement run-book — maintain the map, propose one refinement

> **Superseded** — retained until `apply-agent-research` lands, then removed. See
> [`docs/design/cross-repo-knowledge-application.md`](../../docs/design/cross-repo-knowledge-application.md):
> the central-push run-book is replaced by the decentralized-pull
> `apply-agent-research` skill, and the integration map referenced below is dropped.

You are running unattended. No user is watching. Do not ask questions — make the
call yourself. This run does two things: (1) build and commit the integration
map (analysis), then (2) diff that map against current reality and propose **at
most one** skill refinement by filing an issue. You **never edit or merge a
skill directly** — you propose via an issue and stop. See `CONTEXT.md` for
`integration map`, ADR 0003 for the producer/decider split, and ADR 0004 for the
helper boundary.

## Scope

- **Read (input):** the `agent-research` knowledge base — only the `knowledge/`
  subpaths in the curated allow-list `runbooks/config/kb-source.json` (never
  auto-discover subjects on disk) — and this repo's `skills/`, `CONTEXT.md`, and
  `docs/adr/`. All read-only.
- **Write (output):** the integration map, **consumer-side in this repo only**
  (e.g. `docs/design/integration-map.md`). Never write into `agent-research`.

## Task

1. Load the KB acquisition contract, then read only its configured `knowledge/`
   subpaths (the curated allow-list — never auto-discover subjects):

   ```
   python3 -c "from runbooks.lib.kb_source import load_kb_source, read_kb; \
     s = load_kb_source('runbooks/config/kb-source.json'); \
     print(read_kb('<kb-root>', s['subpaths']))"
   ```

   `<kb-root>` is the local clone of `s['kb']` on the VPS (transport is ops, out
   of scope — ADR 0003). A configured subject the KB does not yet carry is
   skipped, not fatal. Then read this repo's skills, `CONTEXT.md`, and ADRs. A
   sparse or near-empty KB is fine — the map is then valid but sparse.

2. Build the integration map: real `skill ↔ practice/artifact` mappings. A skill
   with no external counterpart is recorded as a **gap**, not omitted. Keep the
   ordering stable across runs (e.g. sort by skill name) so a re-run produces a
   minimal diff, not a reordered rewrite.

3. Write it with the map-store helper so the minimal-diff rule is mechanical, not
   a matter of judgement:

   ```
   python3 -c "from runbooks.lib.map_store import write_map; \
     print(write_map('docs/design/integration-map.md', open('/tmp/map.md').read()))"
   ```

   `write_map` returns `True` only if the content changed.

4. **Commit only if it changed.** If `write_map` reported `True`, commit the map
   (analysis/bookkeeping — this is the one auto-commit the VPS is allowed, per
   ADR 0003). If it reported `False`, there is nothing to commit.

5. **Propose at most one refinement.** Diff the committed map against the current
   skills/KB to surface refinement candidates (you may invoke
   `improve-codebase-architecture` as the analysis step). Give each candidate a
   stable `dedup_key`, a `priority`, a `title` and a generalized `body`.

   **Sanitize, then gate.** Your candidates are derived in part from the private
   `agent-research` KB, so run every draft's `title` and `body` (both get
   published) through the sanitizer, always passing the configured
   `private_markers`; drop any it blocks. The proposal gate then picks at most one
   survivor — never your own judgement on the cap:

   ```
   python3 -c "from runbooks.lib.sanitizer import check; print(check(body, private_markers=markers))"
   python3 -c "from runbooks.lib.proposal_gate import decide; print(decide(clean, open_keys, min_priority=1))"
   ```

   where `open_keys` are the dedup keys of issues already open under
   `source:self-improvement`. If `decide` returns a candidate, file exactly one
   issue with labels `source:self-improvement` and `needs-triage`; otherwise file
   nothing. Ensure the provenance label exists first, idempotently:

   ```
   gh label create source:self-improvement --description "Filed by the self-improvement run-book" || true
   ```

## Rules

- **Propose, never merge.** At most one issue per run (the gate enforces it; zero
  is fine). **No skill edits** — the only direct mutation is the committed map.
- **Never leak private KB content.** The sanitizer blocks fenced code, file
  paths, and import lines — the load-bearing structural guard (the KB may hold a
  stray secret or private path). It also over-blocks public URLs with a path, so
  **cite sources by bare domain** (`martinfowler.com`), never a full URL with a
  path. A draft that trips the sanitizer is dropped, not filed.
- The map lives in this repo, never in `agent-research` (one-way dependency).
- Re-runs update the map in place with a minimal diff — never a wholesale
  regeneration.
- No questions. There is no user.
