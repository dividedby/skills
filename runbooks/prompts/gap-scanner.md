# Gap-scanner run-book — scan curated repos, propose one new skill

> **Superseded** — retained until `apply-agent-research` lands, then removed. See
> [`docs/design/cross-repo-knowledge-application.md`](../../docs/design/cross-repo-knowledge-application.md):
> the gap-scanner is replaced by the decentralized `skill-request` flow.

You are running unattended. No user is watching. Do not ask questions — make the
call yourself. You read the curated private repos read-only, detect a recurring
cross-repo need, and propose **at most one** generalized new skill by filing an
issue — never leaking private code. See ADR 0003 for why this files into a public
tracker, and the design plan's Operational notes for the runner (the maintainer's
always-on VPS; authenticated `git clone`, no GitHub Actions).

## Scope

- **Read only the curated allow-list** in `runbooks/config/gap-scanner-repos.json`.
  Never auto-discover repos. A repo absent from the config is never read.
- Repos are **private**; treat everything you read as proprietary. Clone
  read-only, shallow, into a scratch area, and clean it up at end of run.

## Task

1. Load the allow-list:

   ```
   python3 -c "from runbooks.lib.repo_scan import load_repo_list; \
     print(load_repo_list('runbooks/config/gap-scanner-repos.json'))"
   ```

   An empty list (or missing config) is a clean no-op — stop.

2. Scan the listed repos with the repo-scan seam, which shallow-clones each into
   a temporary working area and removes it on exit (an unreachable repo is
   skipped, not fatal):

   ```python
   from runbooks.lib.repo_scan import scan
   with scan(repo_list, clone=shallow_clone) as result:
       for name, path in result.repos.items():
           ...  # read-only analysis
   # working area is gone here
   ```

3. **Detect a recurring need.** Across the cloned repos, judge whether the same
   need recurs (not a one-off). Draft each recurring need as a candidate with a
   stable `dedup_key`, a `priority`, a `title`, and a **generalized** `body`
   describing the need in the abstract — never paste repo content.

4. **Sanitize, then gate.** Run every draft's `title` and `body` (both get
   published) through the sanitizer, always passing the configured
   `private_markers`; drop any it blocks. The proposal gate then picks at most
   one survivor:

   ```
   python3 -c "from runbooks.lib.sanitizer import check; print(check(body, private_markers=markers))"
   python3 -c "from runbooks.lib.proposal_gate import decide; print(decide(clean, open_keys, min_priority=1))"
   ```

   where `open_keys` are the dedup keys of issues already open under
   `source:gap-scanner`. If `decide` returns a candidate, file exactly one issue
   with labels `source:gap-scanner` and `needs-triage`; otherwise file nothing.
   Ensure the provenance label exists first, idempotently:

   ```
   gh label create source:gap-scanner --description "Filed by the gap-scanner run-book" || true
   ```

## Rules

- Read only the allow-listed repos. No auto-discovery.
- Read-only and shallow; remove all cloned content before the run ends. Never
  retain private code.
- **Never paste repo content.** The sanitizer blocks fenced code, file paths, and
  import lines — the load-bearing structural guard (private repos may hold a stray
  secret). It also over-blocks public URLs with a path, so **cite sources by bare
  domain** (`martinfowler.com`), never a full URL with a path.
- **Propose, never merge.** At most one issue per run (the gate enforces it; zero
  is fine). A draft that trips the sanitizer is dropped, not filed.
- No questions. There is no user.
