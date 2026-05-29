# Gap-scanner run-book — read-only scan of curated repos

You are running unattended. No user is watching. Do not ask questions — make the
call yourself. This is the **scan skeleton** (#17): you read the curated repos
read-only and exit clean. You do **not** file any issue yet — proposal logic and
the sanitizer guard arrive in #20. See ADR 0003 for why this files into a public
tracker, and the design plan's Operational notes for the runner constraint
(private repos need the non-GHA runner).

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

3. **File nothing.** There is no proposal logic in this skeleton. Confirm the
   working area is empty and exit clean.

## Rules

- Read only the allow-listed repos. No auto-discovery.
- Read-only and shallow; remove all cloned content before the run ends. Never
  retain private code.
- Zero issues filed this run.
- No questions. There is no user.
