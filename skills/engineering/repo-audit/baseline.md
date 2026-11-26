# Repo Audit — Baseline

The one home for the deterministic baseline: the tools and commands the main
session runs in Stage 2, before the lenses launch, so that what a tool answers
exactly is not left to a lens to find by reading. [Stage 2](./stages/2-capture.md) and
`briefs.md` cite this file and do not restate it. The baseline measures and
judges nothing; the lenses judge. It runs under the
[Execution boundary](./SKILL.md#execution-boundary).

Commands here are sketches of the principle: use the repo's own versions and
flags where they differ, and say so in the digest. The stack list is not closed:
a stack with no section gets the [universal tools](#1-universal-tools) and a
digest line that says so, as [`types.md`](./types.md) directs for a fallback
profile.

## Setup

Everything the baseline writes goes under one scratchpad folder, `$B`
(the one exception is a short symlink to `$B/tmp`, see the `TMPDIR` bullet):
`tools/` (binaries and venvs), `raw/` (raw output, one file per command), `cache/`,
`home/`, `tmp/`, `clone/` (a scratch clone, only when needed) and `digest.md`,
`commands.md` (below).

### Installs

- **Install only into `$B/tools`.** A scratch venv (`uv venv $B/tools/venv`, then
  `uv pip install --python $B/tools/venv/bin/python <tool>`; `python -m venv` and
  `pip` also work), `pnpm dlx <tool>`, `go install` (see Go), or a release binary
  (`gh release download -R <owner>/<repo> -p <asset> -D $B/dl/<tool>`, each
  download in its own empty directory; verify the checksum when the release
  publishes one; copy the binary to `$B/tools/bin`). Never install into the
  repo, and never into a global location: pass `--no-bin` to
  `uv python install`, and set the wrapper's redirects below as plain variables
  for the install too (except `gh release download`, below), since `uv`, pnpm
  and `go install` write global caches by default. Pin the version the repo's
  CI pins; otherwise record the version used.
- **Run every install and download from a directory under `$B`**, never the repo
  (`cd "$B/dl/<tool>"` first, or the tool's own directory flag), and never with
  `HOME` unset or empty: a tool with no home writes its state relative to the
  working directory, into the repo. `gh release download` needs the host's
  login, so it keeps the host `HOME` and gets `XDG_STATE_HOME="$B/state"` and
  `XDG_CACHE_HOME="$B/cache"`, never the wrapper's scratch `HOME` or a
  redirected `XDG_CONFIG_HOME`. A `pnpm dlx` run that must read the repo (a
  linter from the repo root) is the one exception to the directory rule; its
  redirects still apply.
- **A refused or unavailable install.** The session's permission layer can
  refuse a release download. Take the next route, in this order: the tool
  already on the host from a package manager (used as is, nothing installed,
  version recorded); `pnpm dlx` or `uv` (`uvx <tool>`, or
  `UV_TOOL_DIR=$B/tools/uv UV_TOOL_BIN_DIR=$B/tools/bin uv tool install <tool>`);
  `go install` into `$B/tools/bin`; otherwise "Tool unavailable: name" in the
  Not run table, with the refusal noted in the detail. A refusal is not routed
  around any other way.

### Environment

- **Run the repo's code through the wrapper `$B/run`**, which is what "the
  scrubbed environment" means everywhere in this skill. It is a POSIX `sh`
  script written once at setup with the values expanded
  (`chmod +x "$B/run"`; `mkdir -p` the directories it names), and it is the one
  home of the redirect list:

  ```sh
  #!/bin/sh
  exec env -i PATH="$B/tools/bin:$B/tools/venv/bin:<the host's tool directories>" \
    HOME="$B/home" TMPDIR="$T" XDG_CACHE_HOME="$B/cache" \
    PYTHONPYCACHEPREFIX="$B/cache/pyc" \
    UV_CACHE_DIR="$B/cache/uv" UV_PYTHON_INSTALL_DIR="$B/tools/python" \
    PIP_CACHE_DIR="$B/cache/pip" \
    pnpm_config_store_dir="$B/cache/pnpm-store" pnpm_config_cache_dir="$B/cache/pnpm" \
    npm_config_store_dir="$B/cache/pnpm-store" npm_config_cache="$B/cache/pnpm" \
    GOPATH="$B/go" GOMODCACHE="$B/go/pkg/mod" GOCACHE="$B/cache/go" GOBIN="$B/tools/bin" \
    CARGO_HOME="$B/cache/cargo" RUSTUP_HOME="$B/tools/rustup" CARGO_TARGET_DIR="$B/cache/cargo-target" \
    LLVM_PROFILE_FILE="$B/cache/profraw/%p-%m.profraw" \
    GOCOVERDIR="$B/cache/gocov" NODE_V8_COVERAGE="$B/cache/v8" \
    <demo variables from the profile> "$@"
  ```

  The `<demo variables from the profile>` slot is mandatory. Every demo or
  data-folder variable the Stage 1 profile names (the "environment variables the
  demo or sample mode needs" row) is written into the wrapper with a scratch
  value under `$B`, for example `<APP>_HOME="$B/data"`.

  **Self-test, right after writing the wrapper and before any repo code runs:**
  for each variable the profile names, `$B/run env | grep "^<VAR>="` must print
  it with its scratch value (a path under `$B` for a data folder). A missing one stops the run from starting any repo
  binary until the wrapper is fixed. The result is a `commands.md` row.

  A variable goes after the wrapper, `$B/run env VAR=value <command>`, never
  before it (`VAR=value $B/run …`), because `env -i` strips it.

  `$T` is the short temp path from the `TMPDIR` bullet below. Drop only the
  lines for a stack the repo does not use; a stack with no
  section here still gets its package manager's redirect, and the stack
  sections add the tool-specific flags. Every repo-code command is
  `$B/run timeout 600 <command>`; macOS ships no `timeout`, so use `gtimeout`
  from coreutils or the `perl` form in [Time-box](#run-rules) there, and check
  that the one you use is on the wrapper's `PATH`.

  What the less obvious lines are for:
  - **pnpm:** pnpm 11 reads only the `pnpm_config_*` names, and pnpm 10 and older
    only the `npm_config_*` ones; check with `$B/run pnpm store path` and
    `$B/run uv cache dir`, **run from `$B/tmp`**, never the repo folder: pnpm
    creates and removes a probe file in its working directory, which moves that
    folder's mtime. The same goes for any main-session probe command that is not
    a gate. Otherwise pnpm picks its store by volume, which can be a folder at the
    repo's volume root. A direct `pnpm install` or `pnpm add` also takes
    `--store-dir $B/cache/pnpm-store`.
  - **Coverage:** an instrumented binary writes its profile to the working
    directory by default: `default.profraw` from Swift, Clang and Rust builds,
    and Go binaries built with `-cover` write to `GOCOVERDIR`.
  - **The environment is built inside the script**, not in a shell variable:
    zsh does not word-split a string variable, so an `env -i $ENV <command>`
    line breaks there.
  - **The host's tool directories** are wherever `git`, the toolchains and the
    package managers live (for example `/usr/bin:/bin`, plus Homebrew's or the
    version manager's directory). `HOME` in the scratchpad also redirects most
    tools' caches and stores.
  - **`HOME` does not redirect a native binary's home lookup:** macOS
    `NSHomeDirectory()` and `getpwuid` ignore `$HOME`. A CLI or native app with a
    data folder needs its own variable in the wrapper (or a scratch user) before
    any probe or lens runs it. With neither, it is not run, reason "Needs X: an
    isolated data mode".

  Tools the baseline installs and reads (`osv-scanner`, `gitleaks`, `scc`,
  `git log`) scan files; they do not run the repo's code and need no
  scrubbing. The wrapper holds no host credential, so `gh release download`
  runs outside it, from `$B/dl/<tool>`, with the host `HOME` and the state and
  cache redirects in [Installs](#installs).

- **`TMPDIR` is short.** macOS limits a Unix socket path to 104 bytes, and Go
  plugin tools (`tofu`, `terraform`) put a socket under `TMPDIR`, so a long
  scratchpad path breaks them. When `$B/tmp` is longer than about 60 bytes, `$T`
  is a short symlink to it (`T=$(mktemp -u /tmp/ra.XXXXXX); ln -s "$B/tmp" "$T"`);
  otherwise `$T` is `$B/tmp`. Only the path is short: every byte written still
  lands in `$B/tmp`, and the symlink is the one thing outside `$B`. The first
  row of `commands.md` records which, and the run removes the symlink (not
  `$B/tmp`) after the last command that ran repo code.
- **Built binaries never run with the repo as the working directory.** A test
  binary, a CLI probe build or a demo run (anything the run built, not the
  repo's own gate runner) starts from `$B/tmp` or the scratch clone, by absolute
  path. Instrumented and debug binaries write to the working directory (a
  profile, a database, a log). A gate runner that picks its own directory
  (`swift test`, `go test`) starts in the repo's package folder; the wrapper's
  redirects and the [check after each gate](#keeping-the-repo-unchanged) cover
  it, and one that still writes there runs in the scratch clone.

### Keeping the repo unchanged

- **Stage 1 saves the baseline of the check** in `$B/proof/`: `HEAD`
  (`git rev-parse HEAD`), `status-stage1.txt`
  (`git --no-optional-locks status --porcelain --ignored`), `marker`,
  `paths-stage1.txt` (every path in the repo, `.git` and nested worktrees
  pruned, from `find … -print | sort`) and `worktrees.txt` (the nested
  worktrees: the paths in `git -C <repo> worktree list --porcelain` that lie
  inside the repo folder, other than the audited checkout itself; compare them
  with the repo path resolved by `pwd -P`, since on macOS `/tmp` is really
  `/private/tmp`). Every marker
  lives in `$B/proof/`: `marker` (Stage 1's), `marker-<gate>` (one per check),
  `marker-return-<lens>` (the main session's check at a lens's return) and
  `<lens>/marker-<n>` (a lens's own).
- **Check the repo after each gate or scan that runs repo code**, not only at
  Stage 6. Each check does, in order:
  1. **HEAD** equals the pin. The run never moves it, so a different `HEAD` is
     an outside change (for example a `git pull` in another terminal). Still run
     the checks from **Worktrees** to **Directory mtime only** against the previous check before re-snapshotting. Only the
     paths in `git diff --name-only --no-renames <old> <new>` (the outside
     change) are not a
     breach of the gate that just ran; any other difference is. Then log a
     `HEAD moved` row (old and new commit, the time, the check that saw it) and
     a Stages row, re-pin to the new `HEAD`, take a fresh Stage 1 snapshot
     (every item above) and restart Stage 1. Work done against the old commit is
     redone. The new snapshot replaces the Stage 1 files in `$B/proof/`; the old
     ones are kept as `<name>-<oldsha>`. Stage 1 compares `HEAD` once more at its
     end, with the pin taken at its start.
  2. **Worktrees.** Re-read `git worktree list --porcelain`. Each nested
     worktree is pruned from the `find`
     (`find <repo> \( -path <repo>/.git -o -path <worktree> … \) -prune -o …`),
     and the proof names each one in a `nested worktrees excluded` row,
     updated when the list changes. Writes inside them belong to another
     session, not to this run.
  3. **Status** equals the previous check's saved output.
  4. **Paths and times.** The path list equals the previous check's, and
     `find <repo> … ! -type d -newer <marker> -print` lists nothing. An added,
     removed or newer non-directory path is a breach.
  5. **Directory mtime only.** A directory newer than the marker
     (`find <repo> … -type d -newer <marker> -print`), when **Status**
     and **Paths and times** found nothing (same status, same path list, no newer file), is
     reported apart as `mtime only: <dir>`, with the gate. It is not a changed
     repo and not a failure: no path was added, removed or written, and a tool
     made and removed a temporary entry. There is nothing for the maintainer to
     remove. The row names the command, so the next run starts it from `$B/tmp`.

  A main-session probe that runs in the repo folder (anything that is not a gate
  and is not run from `$B/tmp`) gets the same check. The first check compares
  with the Stage 1 snapshot and marker
  ([`SKILL.md`](./SKILL.md#execution-boundary)). After each check, save its
  status output and path list and `touch` a fresh marker
  (`$B/proof/marker-<gate>`, never overwriting the Stage 1 snapshot and marker,
  except by a re-pin) before the next command runs, so a breach is blamed on one
  gate and not on every later one. Stage 6
  still compares with Stage 1.

- **One gate per check.** A check runs after each gate, never after a batch of
  gates: run the gates one per command. A check after a group does not count as
  each gate's row.
- **Lenses.** A lens that runs repo code does the same check after each such
  command. Before its first repo-code command it saves status and the path list
  and touches its own marker under `$B/proof/<lens>/`, and its first check
  compares with that baseline, not with Stage 1. It lists each check in its
  report ([`briefs.md`](./briefs.md) shared header). The
  main session also runs the check at each lens's return, against its own
  previous main-session check, as a backstop, and copies the lens's checks into
  the proof as `after gate: <lens>: <command>` rows. The backstop check's marker
  is `$B/proof/marker-return-<lens>`. A lens that sees `HEAD` move stops its
  repo-code commands and reports it; the main session re-pins and restarts.
  Lenses run concurrently, so a breach first seen by the backstop names every
  lens that ran since the previous check, and a lens's own row can include
  writes by another lens running at the same time.
- **A new difference is a breach caused by that gate.** (`mtime only` and
  nested-worktree rows are not breaches.) Record the gate and each
  path in that gate's `commands.md` row and as a row in the run log's read-only
  proof, and rerun that tool, if at all, in the scratch clone. The run does not
  delete or revert the file: it left the repo changed, which
  [`SKILL.md`](./SKILL.md#failure-conditions) counts as a failed run, so the
  closing message names the path for the maintainer to remove.
- **A command that would write tracked files** (a formatter's write mode, a
  generator, a test that rewrites snapshots), or a gate that needs the repo's
  dependencies installed when its checkout has none, runs in a scratch clone of
  the pinned commit (`git clone --no-hardlinks <repo> $B/clone`, then
  `git -C $B/clone checkout --detach <commit>`), not in the repo. Say "ran in
  scratch clone" in the digest. A clone has none of the repo's ignored files, so
  a gate that needs one is "not run (needs X)".
- **In-repo caches.** Many tools write a cache or state file into the repo
  folder or its `node_modules` by default (`.pytest_cache`, `__pycache__`,
  `.ruff_cache`, `.mypy_cache`, `.hypothesis`, a default `.coverage`,
  `node_modules/.vite` and `node_modules/.cache`, Jest's cache, `.eslintcache`,
  `*.tsbuildinfo`, `.turbo`, `.nx`, `.build`, `.terraform`). Each stack section
  below lists the redirect for the tools it names. A tool with no redirect, or
  one this file does not name, runs in the scratch clone, and the check after
  each gate confirms nothing in the repo changed.

### Run rules

- **Untrusted repo.** The execute answer from Stage 1
  ([Stage 1](./stages/1-scope.md) **Ownership and trust**) decides what
  runs. Every gate, test, build, installation of the repo's dependencies, and
  any command this file marks as running repo code follows it, and on No is
  "not run (untrusted not run)". The tools that read files without executing
  the repo's code (`osv-scanner`, `gitleaks`, `scc`, `git log` and the like)
  run either way.
- **Time-box:** 10 minutes per gate or scan by default (`timeout 600`; `gtimeout`
  from coreutils on macOS, or `perl -e 'alarm 600; exec @ARGV' -- <command>`). A
  timed-out command is stopped, keeps its partial output and is reported as "not
  completed (time-box)", reason Depth. For a suite that cannot finish in the
  time-box, the fallback is CI's latest result for the same check on the pinned
  commit, or on the default branch when that commit has none
  (`gh api repos/$GH/actions/runs?head_sha=<commit>` or `?branch=<default>`, then
  the run's jobs): the conclusion and duration, cited with the run URL and
  labelled as CI's, not measured here, reason Depth. With no such run, or no
  GitHub remote, it stays "not completed (time-box)".
- **Never run bare `pip-audit`, `npm ls` or the like where the tool inspects
  the environment it runs in**: it audits the scratch venv, not the repo. Give
  it the repo's manifest.
- **`commands.md`:** one row per command: the command as run, exit code and wall
  time. The run log keeps only the rows `SKILL.md` names (failed or over 30 s).
- **A tool or gate that did not run** gets one reason from the closed list in
  [`rubric.md`](./rubric.md#not-assessed-reasons), with the area it feeds, in the
  digest's Not run table:

  | Situation                                                         | Reason                  |
  | ----------------------------------------------------------------- | ----------------------- |
  | the stack or fact it needs is absent (no manifest, no UI)         | Not applicable (fact)   |
  | the tool could not be installed or has no build for the platform  | Tool unavailable: name  |
  | Docker, a database, credentials, a device or a service is missing | Needs X: name it        |
  | the repo is untrusted and the execute answer is not yes           | Untrusted not run       |
  | the 10-minute time-box or a sampled scan stopped it               | Depth: what was reached |
  | the user limited the run to named packages                        | Not selected            |

  The area follows the tool: vulnerability, currency, licence and supply-chain
  scans feed `tech-stack`; secret scans `security`; dead code and complexity
  `code-quality`; gates, durations and coverage `tests`; documented-versus-actual
  gates `agent-readiness`; the cruft digest `repo-hygiene`. Stage 6 copies each
  row into that area's `skipped_methods`.

## 1. Universal tools

Run on every repo, whatever the stack. Each result is a file in `$B/raw/`.

**Nested worktrees.** The paths in `worktrees.txt` (see
[Keeping the repo unchanged](#keeping-the-repo-unchanged)) are other checkouts
of the same repo, often on another branch, and a recursive scan reads them as
extra copies. A tool with an exclude flag skips them. Otherwise the digest
counts only the hits outside them and lists the hits inside them apart, one line
per worktree with its count: `osv-scanner` lockfiles, `gitleaks dir` hits, and
`scc` too when it reads them. The split in the digest is the rule that holds,
whichever flag the installed version has.

- **Dependency vulnerabilities, all ecosystems:**
  `osv-scanner scan source --recursive --format json --output-file $B/raw/osv.json <repo>`
  (reads lockfiles and manifests; exit 1 means vulnerabilities were found, not
  that the tool failed). A repo with no lockfile reports "0 packages found",
  which the digest says in those words. When it reports 0 packages but the repo
  tracks a lockfile (`git ls-files` shows `pnpm-lock.yaml`, `package-lock.json`,
  `Package.resolved`, `uv.lock` and the like), the lockfile was not parsed (for
  example pnpm 11's `pnpm-lock.yaml`). The digest does not say "0 packages
  found": it adds a Not run row "Tool unavailable: osv-scanner does not parse
  `<lockfile and format>`" (area `tech-stack`), and the stack's own audit (Node:
  `pnpm audit`, see [Node and pnpm](#node-and-pnpm)) covers that ecosystem.
  With range manifests and no lockfile, osv-scanner resolves its own transitive
  versions, which the installed environment may not have: label those rows
  "resolved by the tool" and pair each with the installed version (the Node
  install, the Python scratch venv's package list) before a lens reads it. A
  row with no installed version to pair is a lead, not a finding.
- **Secrets, tree and history:**
  `gitleaks dir --no-banner --redact --report-format json --report-path $B/raw/gitleaks-tree.json <repo>`
  and `gitleaks git --no-banner --redact --report-format json --report-path $B/raw/gitleaks-history.json <repo>`
  (exit 1 means leaks were found). **Presence and location only:** the digest
  carries rule id, path, line, commit and whether the path is still tracked
  (`git ls-files --error-unmatch <path>`), and never the `Secret`, `Match`,
  `Fingerprint`, `Author`, `Email` or `Message` fields; read the report through
  a filter that selects only the fields it needs
  (`jq -r '.[] | [.RuleID, .File, .StartLine, .Commit[0:8]] | @tsv'`). `dir` scans ignored files too, so a hit in an ignored path is a
  secret on disk, not in git; the digest says which.
- **Secrets, all refs (private repos, `standard` only).** A conditional step that
  runs only when the profile says the repo is private
  (`gh api repos/$GH --jq .private`) and the go-public feasibility check runs
  ([`briefs.md`](./briefs.md#security-privacy-and-data) Security, privacy and data, **Go-public feasibility**); a public repo,
  a repo with no GitHub remote and a `quick` run skip it, and the digest says
  which. It extends the history scan above and keeps its presence-and-location
  rule: first `git -C <repo> rev-parse --is-shallow-repository`. `true` means no
  scan and "Needs X: full git history" in the Not run table (a shallow clone
  holds only part of the history); otherwise
  `gitleaks git --no-banner --redact --log-opts="--all" --report-format json --report-path $B/raw/gitleaks-history-all.json <repo>`,
  which scans every ref, not only the checked-out branch. Read it through the
  same filter, and for each hit add whether the commit is on the checked-out
  branch (`git merge-base --is-ancestor <commit> HEAD`) or only on another ref.
  The digest reports it as its own `gitleaks (all refs)` row.
- **Size:** `scc --by-file --format json --output $B/raw/scc.json <repo>` (honours
  `.gitignore`; `tokei`, or `git ls-files | xargs wc -l`, when `scc` is not
  available). Per-language lines feed the profile and the test digest.
- **Churn hotspots:**
  `git --no-optional-locks log --since="1 year ago" --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | head -10`
  (widen the window for a repo with little recent history; the digest's churn
  row states the window it used). This is the churn method
  [`types.md`](./types.md) refers to for large-tier sampling.
- **Optional:** `scorecard --local` (OpenSSF Scorecard) when installed.

## 2. The repo's own gates

A gate is a command the repo expects to pass before a change lands: lint,
format check, typecheck, tests, build, schema or link check.

1. **Discover** them from `CLAUDE.md` and `AGENTS.md`, the README and
   contributing docs, the CI config (each workflow step that runs a check, or
   another provider's equivalent), `Makefile`, `justfile`, `tox.ini` or
   `noxfile.py`, `package.json` scripts, and `scripts/check*`. Record each with
   the `file:line` that documents it.
2. **Run each once**, sequentially, under the [setup](#setup) rules and the
   stack's redirect flags below, with the repo's own flags (add a flag only to
   keep output out of the repo, and record the addition). Record pass or fail,
   counts (tests, files checked, errors) and wall time. Do not retry a failure the
   repo causes (a test, lint or type error). A failure the environment causes
   is fixed in the environment, then the gate runs once more; both runs get a
   row in `commands.md`, and the digest reports the second, naming the fix.
   Environment causes include:
   - a socket path over the length limit;
   - a macOS BSD tool given a GNU flag;
   - a cache or output path the redirects missed;
   - an ignored file the CI checkout does not have, such as a formatter or
     linter walking `node_modules`: rerun in the scratch clone, which has none;
   - a test that finds a built product at the default output path (see
     [Swift](#swift)).

   When the gate cannot run twice within the time-box, rerun only the parts that
   failed for the environment reason (the stack's filter flag), with both runs
   in `commands.md`.

3. **Record documented versus actual** for every gate, one of:
   - ran as written;
   - ran with a change (say what: a tool taken from the scratch venv instead of
     `pipx`, a flag added to redirect a cache, a scratch clone);
   - failed as written (the output line);
   - in CI but not documented, or documented but not in CI (compare the two
     lists).

   This table feeds Agent readiness; the baseline records it and does not judge
   it.

4. A gate that needs Docker, a database, credentials, a device or a running
   service is "not run (needs X)", naming X. A gate the run may not execute is
   "not run (untrusted not run)".
5. Tests run in the scrubbed environment. A test that reaches a live service is
   recorded as evidence (the test, the service, its time) and is not blocked; it
   never gets credentials.
6. The build's wall time is recorded even when no doc names a build gate, and
   so are the sizes of the state or output files the app writes (from the
   build output or a demo run, both in the scratchpad), for the code lens.

## 3. Stack scanners

Stage 1's profile lists each language with tracked source beyond a stray script.
Run the section of each detected stack, and the universal tools for any other.
Each stack section answers the same questions, where they apply: dependency
vulnerabilities, currency (outdated packages, and runtime and framework end of
life against the declared minimum), the declared minimum runtime, dead code,
complexity (top 10), lint or type errors the repo does not already gate on, test
durations and coverage. A question that does not apply is not run, with its
reason.

**Runtime end of life** is the same method in every stack: read the declared
floor from the manifest, CI matrix and tool config (`requires-python`,
`engines`, the `go` directive, `swift-tools-version`, `required_version`, a
formatter's `target-version`), then read the vendor's support dates from
`https://endoflife.date/api/<product>.json` (for example `python`, `nodejs`,
`go`, `terraform`), and record the floor, its end-of-life date and the date read.
**The declared minimum runtime** is then run, not assumed: install the floor
version into `$B/tools` and run the suite on it when the repo's dependencies
install there, or at least a compile and import check of every tracked source
file. A floor that cannot be installed is "not run (tool unavailable: version)".

### Python

- **Install:** `uv venv $B/tools/venv`;
  `uv pip install --python $B/tools/venv/bin/python pip-audit vulture radon coverage pytest-cov`
  (add `ruff`, `mypy` or `pyright` at the repo's pinned versions only to run a
  gate the repo documents).
- **Vulnerabilities:** `pip-audit -r requirements.txt --cache-dir $B/cache/pip-audit`
  (or `pip-audit <repo>` for a `pyproject.toml`, which builds the project and so
  runs repo code: run it under the scrubbed environment; for a `uv.lock` or
  `poetry.lock`, export to a requirements file in `$B/tmp` first, and
  `osv-scanner` reads the lockfile directly). A range manifest with no lock
  gives `osv-scanner` its own resolution: label its rows "resolved by the
  tool" and pair each with the scratch venv's installed version (see
  [Universal tools](#1-universal-tools)). With no manifest, look at the
  imports: stdlib only means "not run (not applicable: no dependency
  manifest)"; third-party imports with no manifest is itself a fact for the
  digest.
- **Currency:** install the declared dependencies into a scratch venv
  (`uv venv --python <floor> $B/tools/venv-floor`; `uv pip install -r ...`),
  then `uv pip list --outdated --python <venv>`. Runtime end of life as above.
- **Minimum runtime:** `UV_PYTHON_INSTALL_DIR=$B/tools/python uv python install --no-bin <floor>`,
  then run the tests with that interpreter, or
  `<python> -c 'import sys; [compile(open(f).read(), f, "exec") for f in sys.argv[1:]]' $(git ls-files '*.py')`
  (compiles without writing bytecode).
- **Dead code:** `vulture --min-confidence 60 <tracked source files>`, with the
  test files excluded: framework entry points (test methods, route handlers,
  fixtures) read as unused. Report the count and the top 10 as candidates.
- **Complexity:** `radon cc -s -j <files>`, sorted by complexity, top 10;
  `radon mi -s <files>` for the maintainability index.
- **Durations and coverage:** `pytest --durations=10 -p no:cacheprovider`;
  `unittest` on 3.12 or later takes `--durations 10`; a script-style test runs
  per file with its wall time recorded. Coverage:
  `COVERAGE_FILE=$B/cache/.coverage coverage run -a --source=<dirs> <test>` per
  test script, or `COVERAGE_FILE=... pytest --cov=<pkg> --cov-report=term`
  (never `--cov-report=html` in the repo). Code a test runs in a subprocess
  reads as 0%; say so instead of reporting it as untested.
- **Redirects:** `PYTHONPYCACHEPREFIX=$B/cache/pyc` (or `python -B`),
  `-p no:cacheprovider`, `COVERAGE_FILE`, `ruff --no-cache` (or
  `RUFF_CACHE_DIR`), `mypy --cache-dir=$B/cache/mypy`,
  `HYPOTHESIS_STORAGE_DIRECTORY`, `UV_CACHE_DIR`.

### Node and pnpm

- **Vulnerabilities:** the repo's own manager's audit, read-only: `pnpm audit --prod`
  and `pnpm audit` for dev dependencies (`npm audit --omit=dev` or
  `yarn npm audit` for the others); `osv-scanner` covers the lockfile when it
  parses it (see [Universal tools](#1-universal-tools)).
- **Currency:** `pnpm outdated` (exit 1 means something is outdated); runtime
  end of life against `engines.node`, `.nvmrc` and the CI `node-version`.
- **Minimum runtime:** `pnpm dlx node@<floor> <script>` runs a script on that
  Node version from the dlx cache; then the repo's test command or a
  `node --check` per file.
- **Dead code:** `pnpm dlx knip` (needs the repo's dependencies installed: run it
  where they are, or in a scratch clone after `pnpm install --frozen-lockfile`).
- **Complexity:** ESLint's `complexity` rule at 10 with `-f json`, top 10 by the
  number in "has a complexity of N"; the config is the scratch config below when
  the repo has none.
- **Durations and coverage:** the test runner's own (`vitest run --reporter=verbose`,
  `jest --verbose`, `node --test`); coverage output only to `$B`:
  `jest --cacheDirectory=$B/cache/jest --coverageDirectory=$B/cache/cov`,
  `vitest run --coverage.reportsDirectory=$B/cache/cov` with a config in `$B/cfg`
  that sets `cacheDir: "$B/cache/vite"` (pass it with `--config`; Vite and Vitest
  otherwise write `node_modules/.vite`),
  `c8 --temp-directory $B/cache/c8 --reports-dir $B/cache/cov`,
  `NODE_V8_COVERAGE=$B/cache/v8`.
- **Redirects:** any runner that writes into `node_modules` or the repo (Vitest
  and Vite, Jest, bundlers, `.turbo`, `.nx`, `node_modules/.cache`) either has
  its cache redirected as above (`TURBO_CACHE_DIR`, `NX_CACHE_DIRECTORY` and
  similar variables for monorepo runners) or runs in the scratch clone. `HOME`,
  `XDG_CACHE_HOME` and `pnpm_config_store_dir` in `$B` cover pnpm's store and dlx
  cache. TypeScript:
  `tsc --noEmit --incremental false`, or `--tsBuildInfoFile $B/cache/tsbuildinfo`
  for a `composite` project (which rejects `--incremental false`). ESLint and
  Prettier write no cache unless `--cache` is passed.
- **Installing the repo's dependencies in the repo** creates or changes
  `node_modules` (ignored, but its mtimes change): run the install in a scratch
  clone.

### Browser JS with no manifest

Detect tracked `*.js` or `*.mjs` files that no `package.json` covers, usually
loaded by `<script src>` from HTML. The Node rows do not apply, so run these:

- **Lint and complexity:** write a default flat config to
  `$B/cfg/eslint.config.mjs` with no imports, so it resolves from the
  scratchpad. It covers `*.js` and `*.mjs` at the latest ECMAScript version,
  as scripts or modules the way the HTML loads them, declares browser
  globals such as `window`, `document`, `fetch` and `console`,
  and turns on `no-undef`, `no-unused-vars`, `eqeqeq`, `no-empty` and
  `complexity` at 10;
  then, from the repo root, `pnpm dlx eslint -c $B/cfg/eslint.config.mjs -f json $(git ls-files '*.js' '*.mjs')`
  under the scrubbed environment. Add the globals the code uses (check what
  `no-undef` reports before counting it). Top 10 by complexity and the counts by
  rule go in the digest.

- **Coverage:** when the repo has browser JS and UI tests, collect JS coverage
  from Chromium with Playwright's coverage API in a scratch script outside the
  repo (the scratch install of [`probe.md`](./probe.md)):
  `page.coverage.startJSCoverage()`, drive the UI tests' flows (or the probe's
  screen walk) against the primary instance
  ([Stage 2](./stages/2-capture.md)), `stopJSCoverage()`, and report used
  bytes over total bytes per script. Say which drove it; a screen walk is not the
  test suite. Without UI tests, a browser, or a way to start the instance:
  **"JS coverage: not measured (reason)"**, with the reason from the closed list.

### Swift

- **Toolchain:** the installed one; no install. A coverage-instrumented binary
  (`--enable-code-coverage`) writes `default.profraw` into its working directory
  unless `LLVM_PROFILE_FILE` points into `$B` (the wrapper sets it), and a built
  binary never runs with the repo as its working directory. Point build output at
  the scratchpad: `swift build --scratch-path $B/cache/swift` and
  `swift test --scratch-path $B/cache/swift --enable-code-coverage`
  (`swift test --show-codecov-path` prints the profile path);
  `xcodebuild -derivedDataPath $B/cache/dd -clonedSourcePackagesDirPath $B/cache/spm`
  for a project file. `--scratch-path` does not stop dependency resolution from
  writing `Package.resolved`, and it may write `.swiftpm/`, in the package root: when
  `Package.resolved` is tracked, add `--only-use-versions-from-resolved-file`
  (and `-disableAutomaticPackageResolution` to `xcodebuild`, after resolving in
  the clone); otherwise run in a scratch clone. Build only:
  [`types.md`](./types.md)'s native-app "Never" list stands (no device install,
  no signing identity).
- **Tests that find the built product under `.build`** (next to the `.xctest`
  bundle, or at `<repo>/.build/debug/<name>`) fail under `--scratch-path` for an
  environment reason. Fix: run the gate in the scratch clone with `.build`
  symlinked to the scratch path (`ln -s $B/cache/swift $B/clone/.build`). When
  the full suite cannot run twice in the time-box, the partial rerun of
  [**Run each once**](#2-the-repos-own-gates) in The repo's own gates uses `swift test --filter <suite>` for the
  suites that failed for that reason; the digest reports the first run's result
  for the rest and the filtered rerun for those suites, naming the fix.
- **Vulnerabilities and currency:** `osv-scanner` reads `Package.resolved`;
  compare each pin with its latest tag (`git ls-remote --tags <url>`). Floor:
  `swift-tools-version` and the `platforms:` deployment target against the CI
  runner's image; an older OS cannot be installed: "not run (needs X: older
  OS)".
- **Dead code:** `periphery scan` when installed (it needs an index build in
  `$B`), otherwise "not run (tool unavailable: periphery)".
- **Complexity and lint:** `swiftlint lint --no-cache --reporter json` with a
  config in `$B/cfg` that enables `cyclomatic_complexity`, `function_body_length`
  and `file_length` only (unless the repo's config is the gate); `swift format lint -r <dirs>`
  for format.
- **Durations:** XCTest prints `Test Case ... (N seconds)` lines; sort them, top 10. Swift Testing prints per-test times with `--verbose`.

### Go

- **Install:** the Go toolchain; tools with
  `GOBIN=$B/tools/bin GOPATH=$B/go GOCACHE=$B/cache/go go install <module>@<version>`
  (`golang.org/x/vuln/cmd/govulncheck`, `honnef.co/go/tools/cmd/staticcheck`,
  `github.com/fzipp/gocyclo/cmd/gocyclo`, `golang.org/x/tools/cmd/deadcode`). Use `-mod=readonly` (the default) so
  nothing rewrites `go.mod`.
- **Vulnerabilities:** `govulncheck ./...` (reports reachable ones separately);
  `osv-scanner` reads `go.mod`.
- **Currency:** `go list -m -u -json all`; the `go` directive against
  `endoflife.date/api/go.json`.
- **Minimum runtime:** `GOTOOLCHAIN=go<floor> GOMODCACHE=$B/go/pkg/mod go test ./...`
  (the toolchain downloads into the module cache; from Go 1.21 on the floor
  takes the full form, such as `go1.21.0`).
- **Dead code:** `staticcheck -checks U1000 ./...` or `deadcode ./...`.
- **Complexity:** `gocyclo -top 10 .`; `go vet ./...` for the rest.
- **Durations and coverage:** `go test -count=1 -json -cover -coverprofile=$B/cache/cover.out ./...`;
  sort the `elapsed` of each `pass` event for the 10 slowest;
  `go tool cover -func=$B/cache/cover.out | tail -1` for the total.
- **Redirects:** `GOCACHE`, `GOMODCACHE`, `GOPATH`, `GOCOVERDIR` (a binary built
  with `-cover`), `-coverprofile`, and `-o` for any `go build` output.

### Terraform and OpenTofu

[`types.md`](./types.md)'s infra entry sets the boundary: `validate` only; never
`plan`, `apply` or anything that contacts a provider with credentials.

- **Validate:** `terraform fmt -check -recursive -diff`, then
  `terraform init -backend=false -lockfile=readonly` and `terraform validate`
  (`tofu` for OpenTofu), both through `$B/run` with
  `TF_DATA_DIR=$B/cache/tf` and `TF_PLUGIN_CACHE_DIR=$B/cache/tf-plugins` added to
  its variables (`validate` reads the same data directory), so no `TF_VAR_*` or
  provider credential is visible. Both need the short `TMPDIR` from
  [Setup](#setup). `init` downloads
  providers (network allowed); if it needs to write `.terraform.lock.hcl`, run it
  in a scratch copy of the module (`git archive <commit> <dir> | tar -x -C $B/clone`).
- **OpenTofu state encryption:** a config with an `encryption` block inside
  the top-level `terraform {}` block (`git grep -nE '^[[:space:]]*encryption[[:space:]]*\{'`
  finds candidates; read each hit's context, since a nested block of that name
  elsewhere, such as in a `resource`, does not count), or encryption set
  through the `TF_ENCRYPTION` environment variable, which leaves no block in any
  file (`git grep -n TF_ENCRYPTION` over the CI config, docs, `.env*` files and
  scripts), needs a key or passphrase for `init` and `validate` to evaluate it,
  and a key provider can reach a KMS or run an external program. No key is
  supplied and no demo passphrase is tried:
  `init` and `validate` are "not run (needs X: state encryption key)", while
  `fmt -check` still runs because it reads no key.
- **State files:** `git ls-files | grep -E '\.tfstate'` and
  `git check-ignore -v` on any found path; report the path and whether it is
  tracked, never its contents.
- **IaC misconfiguration:** `trivy config --cache-dir $B/cache/trivy --format json --output $B/raw/trivy-config.json <repo>`
  (see [Supply chain](#4-supply-chain)); `tflint` with `TFLINT_PLUGIN_DIR=$B/cache/tflint`
  when installed.
- **Currency:** the providers and versions in `.terraform.lock.hcl` and
  `required_providers` against the registry's latest, read from the registry's
  page; `required_version` against the vendor's support page.
- **Provider vulnerabilities are not scanned.** `osv-scanner` does not read
  `.terraform.lock.hcl`, so the pinned providers have no vulnerability check
  from [Universal tools](#1-universal-tools). The digest says so in the Not run
  table: tool "osv-scanner (Terraform providers)", area `tech-stack`, reason
  "Tool unavailable: no osv-scanner support for Terraform providers", with
  the currency check above as the only provider check.

### Shell

- **Install:** `shellcheck` and `shfmt` as release binaries in `$B/tools/bin`
  (or from a package manager if already installed).
- **Lint:** `shellcheck -f json $(git ls-files '*.sh')` plus files with a shell
  shebang (`git grep -lE '^#!.*(/|env )(ba|da|k)?sh( |$)'`); `-s sh` for a POSIX
  shebang. `shellcheck` does not support zsh: a zsh script is "not run (tool
  unavailable: no zsh support in shellcheck)".
- **Format:** run `shfmt` the way the repo runs it: find the invocation in the CI
  config, `Makefile`, pre-commit config and docs (`git grep -n shfmt`), use its
  flags and file list, and swap any write mode (`-w`) for `-d`, which shows the
  diff and never rewrites. When the repo has an `.editorconfig` that sets shell
  style, `shfmt` reads it, so pass no style flags (`-i`, `-ci`, `-bn`) of ours.
  Bare `shfmt -d` over the tracked shell files, with shfmt's defaults, is only
  for a repo that documents no invocation and has no `.editorconfig`; the digest
  says which case applied. CI often runs `shfmt` before installing dependencies,
  so locally an ignored `node_modules` is diffed (its `.bin` shims); that is an
  environment failure per [**Run each once**](#2-the-repos-own-gates) in The repo's own gates: rerun in the scratch
  clone.
- **Tests:** a `bats` suite runs with `bats --timing --tap <dir>` and
  `BATS_TMPDIR=$B/tmp` under the scrubbed environment; a script-style test is
  run per file with its wall time recorded.
- **Dead code and complexity:** `shellcheck`'s unused-variable findings are the
  dead-code signal; size is the complexity signal: lines per script and per
  function, top 10, from `scc --by-file`.
- **Minimum runtime:** the interpreter the shebang names, and the oldest one the
  docs claim (macOS ships bash 3.2): `shellcheck -s bash` flags later features;
  a script that declares POSIX `sh` is checked with `-s sh`.

## 4. Supply chain

- **CI workflows:** `actionlint -no-color` (syntax and expression errors) and
  `zizmor --offline --no-progress --format json-v1 .github/workflows`: unpinned
  actions (pinned by SHA?), `permissions:` scope, `pull_request_target` and
  template injection. `--offline` because the online audits need a token the
  scrubbed environment does not have; say so. `zizmor` exits 10 to 14 for
  findings by severity; that is a result, not a failure. Another provider's CI
  config is read, not scanned, and the digest says so.
- **Containers and IaC:** `hadolint --format json <Dockerfile>` for each
  Dockerfile; `trivy config --cache-dir $B/cache/trivy --format json --output $B/raw/trivy-config.json <repo>`
  for Dockerfiles, compose files, Kubernetes and Terraform: image tags that are
  not digests, root users, open ports, missing health checks.
- **Dependency update automation** (`dependabot.yml`, `renovate.json`) is noted
  as present or absent; judging it is the lens's job.

## 5. Licences

- **The repo's own:** the `LICENSE` file, the manifest `license` field and any
  SPDX headers, and whether they agree.
- **Dependencies:** `osv-scanner scan source --licenses --format table <lockfile>`
  (one table of licence by package count), or the stack's tool where the
  lockfile is not enough: `pnpm licenses list`, `pip-licenses` in a scratch venv
  with the dependencies installed, `go-licenses report ./...`.
- **Assets:** fonts, icons, images, audio and other binaries the repo tracks
  (`git ls-files --eol | grep -- '-text'`, and by extension), each with the
  licence or attribution file near it, or "none found".
- The digest gives counts by licence, any copyleft (GPL, AGPL, LGPL, SSPL) or
  unknown or missing licence by name, and each asset with no attribution.
  Whether a licence fits the repo's is the lens's call.

## 6. Cruft digest

Tracked files that do not belong in the tree, from `git ls-files` and `git ls-tree`
(no tool needed):

- the 5 largest tracked files (`git ls-tree -r -l HEAD | sort -k4 -n -r | head -5`);
- tracked binaries (`git ls-files --eol | grep -c 'i/-text'`) and each one's
  size;
- tracked generated, vendored or build output: dependency trees, `dist/`,
  `build/`, minified files, source maps, bytecode, and files with a generated
  marker; lockfiles are listed apart, as expected;
- tracked files an ignore rule matches (`git ls-files -ci --exclude-standard`);
- history size (`git count-objects -vH`).

The digest gives counts and the top 10 with sizes. The same exclusions feed
Stage 1's size tier.

## 7. Test digest

- **Three numbers, never one ratio:** test code lines, fixture lines and source
  lines. Test code is files in test directories or named as tests; fixtures are
  recorded responses, snapshots, test data and cassettes
  (`fixtures/`, `testdata/`, `__snapshots__/`, `cassettes/`); source is the rest of
  the programming and markup languages `scc` reports, not Markdown, config or
  data files. Count with `scc --by-file` or `git ls-files | xargs wc -l` per group.
  Also give test code over source as one figure, and fixtures as a share of
  all test-side lines. A ratio with fixtures folded in reads as bloat that the
  code does not have.
- **Suite:** command, pass, fail and skip counts, and wall time. Coverage total
  where the stack gives it, from the redirected run, with what it does not see
  (subprocesses, browser code).
- **The 10 slowest tests** with their times (the stack's `--durations` or
  equivalent above), and the share of the suite each of the top three takes.
  For a test that is slow because it reaches a live service, say which service.
- **Fixed waits:** a count and the top files, by
  `git grep -cE 'sleep\(|sleep [0-9]|waitForTimeout|wait_for_timeout|setTimeout|Thread.sleep' -- <test paths>`;
  time-based waits only, not condition waits.
- **JS coverage:** a figure from [Browser JS](#browser-js-with-no-manifest), or
  "JS coverage: not measured (reason)". A repo with no browser JS says "not
  applicable (no browser JS)".

## 8. The digest

Write `$B/digest.md`, short enough that a lens reads it whole: top 10 and
counts, with the raw file's path for anything longer. No secret values, no
personal data, and no command output pasted in.

```text
## Run
pinned commit | stacks detected | date | $B path
tools         | name version (source), one per tool used

## Universal
osv-scanner   | N vulnerable packages across M packages   | raw/osv.json
gitleaks      | tree N, history M: rule | path:line | commit | still tracked
gitleaks (all refs) | private repo only: N hits: rule | path:line | commit | on HEAD or other ref; or the skip reason
size          | lines per language (scc)                  | raw/scc.json
churn         | window (since <date or "1 year ago">), top 10: count | path
nested worktrees | one line each: path, osv lockfiles N, gitleaks hits M (not in the counts above)

## Gates (documented vs actual)
gate | documented at (file:line) | in CI | as written? | result | counts | time

## Stack scanners
tool | question (vuln, currency, min runtime, dead code, complexity) | result | top 10 | raw path

## Supply chain, licences, cruft
tool or check | counts | top findings | raw path

## Tests
test code | fixtures | source lines (three numbers), ratio
suite | command, counts, wall time, coverage
10 slowest | time | test
fixed waits | count | top files
JS coverage | figure, or not measured (reason)

## Not run
tool or gate | area | reason from the closed list | detail
```

- The evidence pack for every lens is `digest.md` and the `raw/` folder's path
  ([Stage 3](./stages/3-lenses.md)). Lenses check the digest; they do not
  rediscover it ([`briefs.md`](./briefs.md) shared header).
- Everything in the digest is a fact with a command behind it. A number the
  baseline could not measure says "not measured" and why, never a guess.
