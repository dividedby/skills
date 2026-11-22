# Repo Audit — Baseline

The one home for the deterministic baseline: the tools and commands the main
session runs in Stage 2, before the lenses launch, so that what a tool answers
exactly is not left to a lens to find by reading. `SKILL.md` Stage 2 and
`briefs.md` cite this file and do not restate it. The baseline measures and
judges nothing; the lenses judge. It runs under the
[Execution boundary](./SKILL.md#execution-boundary).

Commands here are sketches of the principle: use the repo's own versions and
flags where they differ, and say so in the digest. The stack list is not closed:
a stack with no section gets the [universal tools](#1-universal-tools) and a
digest line that says so, as [`types.md`](./types.md) directs for a fallback
profile.

## Setup

Everything the baseline writes goes under one scratchpad folder, `$B`:
`tools/` (binaries and venvs), `raw/` (raw output, one file per command), `cache/`,
`home/`, `tmp/`, `clone/` (a scratch clone, only when needed) and `digest.md`,
`commands.md` (below).

- **Install only into `$B/tools`.** A scratch venv (`uv venv $B/tools/venv`, then
  `uv pip install --python $B/tools/venv/bin/python <tool>`; `python -m venv` and
  `pip` also work), `pnpm dlx <tool>`, or a release binary
  (`gh release download -R <owner>/<repo> -p <asset> -D $B/dl/<tool>`, each
  download in its own empty directory; verify the checksum when the release
  publishes one; copy the binary to `$B/tools/bin`). Never install into the
  repo, and never into a global location: pass `--no-bin` to `uv python install`
  and set `UV_PYTHON_INSTALL_DIR`, `GOBIN` and the like to `$B/tools`. Pin the
  version the repo's CI pins; otherwise record the version used.
- **Run the repo's code under the scrubbed environment**, with a timeout:

  ```sh
  env -i PATH="$B/tools/bin:$B/tools/venv/bin:<the host's tool directories>" \
    HOME="$B/home" TMPDIR="$B/tmp" XDG_CACHE_HOME="$B/cache" \
    PYTHONPYCACHEPREFIX="$B/cache/pyc" <demo variables from the profile> \
    timeout 600 <command>
  ```

  The host's tool directories are wherever `git`, the toolchains and the
  package managers live (for example `/usr/bin:/bin`, plus Homebrew's or the
  version manager's directory). `HOME` in the scratchpad also redirects most
  tools' caches and stores. Tools
  the baseline installs and reads (`osv-scanner`, `gitleaks`, `scc`, `git log`)
  scan files; they do not run the repo's code and need no scrubbing.

- **Time-box:** 10 minutes per gate or scan by default (`timeout 600`; `gtimeout`
  from coreutils on macOS, or `perl -e 'alarm 600; exec @ARGV' -- <command>`). A
  timed-out command is stopped, keeps its partial output and is reported as "not
  completed (time-box)", reason Depth.
- **Never run bare `pip-audit`, `npm ls` or the like where the tool inspects
  the environment it runs in**: it audits the scratch venv, not the repo. Give
  it the repo's manifest.
- **A command that would write tracked files** (a formatter's write mode, a
  generator, a test that rewrites snapshots), or a gate that needs the repo's
  dependencies installed when its checkout has none, runs in a scratch clone of
  the pinned commit (`git clone --no-hardlinks <repo> $B/clone`, then
  `git -C $B/clone checkout --detach <commit>`), not in the repo. Say "ran in scratch clone" in the digest. A clone has none of the
  repo's ignored files, so a gate that needs one is "not run (needs X)".
- **In-repo caches.** Many tools write a cache or state file into the repo
  folder or its `node_modules` by default (`.pytest_cache`, `__pycache__`,
  `.ruff_cache`, `.mypy_cache`, `.hypothesis`, a default `.coverage`,
  `node_modules/.vite` and `node_modules/.cache`, Jest's cache, `.eslintcache`,
  `*.tsbuildinfo`, `.turbo`, `.nx`, `.build`, `.terraform`). Each stack section
  below lists the redirect for the tools it names. A tool with no redirect, or
  one this file does not name, runs in the scratch clone; check with the
  Stage 1 marker (see the Execution boundary) that nothing in the repo changed.
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
  | the run may not execute the repo's code (untrusted repo)          | Untrusted not run       |
  | the 10-minute time-box or a sampled scan stopped it               | Depth: what was reached |
  | the user limited the run to named packages                        | Not selected            |

  The area follows the tool: vulnerability, currency, licence and supply-chain
  scans feed `tech-stack`; secret scans `security`; dead code and complexity
  `code-quality`; gates, durations and coverage `tests`; documented-versus-actual
  gates `agent-readiness`; the cruft digest `repo-hygiene`. Stage 6 copies each
  row into that area's `skipped_methods`.

## 1. Universal tools

Run on every repo, whatever the stack. Each result is a file in `$B/raw/`.

- **Dependency vulnerabilities, all ecosystems:**
  `osv-scanner scan source --recursive --format json --output-file $B/raw/osv.json <repo>`
  (reads lockfiles and manifests; exit 1 means vulnerabilities were found, not
  that the tool failed). A repo with no lockfile reports "0 packages found",
  which the digest says in those words.
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
- **Size:** `scc --by-file --format json --output $B/raw/scc.json <repo>` (honours
  `.gitignore`; `tokei`, or `git ls-files | xargs wc -l`, when `scc` is not
  available). Per-language lines feed the profile and the test digest.
- **Churn hotspots:**
  `git --no-optional-locks log --since="1 year ago" --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | head -10`
  (widen the window for a repo with little recent history). This is the churn
  method [`types.md`](./types.md) refers to for large-tier sampling.
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
   counts (tests, files checked, errors) and wall time. Do not retry a failure.
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
  `osv-scanner` reads the lockfile directly). With no manifest, look at the
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
  `yarn npm audit` for the others); `osv-scanner` covers the lockfile.
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
  similar variables for monorepo runners) or runs in the scratch clone. `HOME` and
  `XDG_CACHE_HOME` in `$B` cover pnpm's store and dlx cache. TypeScript:
  `tsc --noEmit --incremental false`, or `--tsBuildInfoFile $B/cache/tsbuildinfo`
  for a `composite` project (which rejects `--incremental false`). ESLint and
  Prettier write no cache unless `--cache` is passed.
- **Installing the repo's dependencies in the repo** creates or changes
  `node_modules` (ignored, but its mtimes change): run the install in a scratch
  clone.

### Browser JS with no manifest

Detect tracked `*.js` or `*.mjs` files that no `package.json` covers, usually
loaded by `<script src>` from HTML. The Node rows do not apply, so run these:

- **Lint and complexity:** write a default flat config to `$B/cfg/eslint.config.mjs`
  with no imports, so it resolves from the scratchpad:

  ```js
  export default [
    {
      files: ["**/*.js", "**/*.mjs"],
      languageOptions: {
        ecmaVersion: "latest",
        sourceType: "script", // "module" when the HTML loads it as a module
        globals: {
          window: "readonly",
          document: "readonly",
          fetch: "readonly",
          console: "readonly",
        },
      },
      rules: {
        "no-undef": "error",
        "no-unused-vars": "warn",
        eqeqeq: "warn",
        "no-empty": "warn",
        complexity: ["warn", 10],
      },
    },
  ];
  ```

  then, from the repo root, `pnpm dlx eslint -c $B/cfg/eslint.config.mjs -f json $(git ls-files '*.js' '*.mjs')`
  under the scrubbed environment. Add the globals the code uses (check what
  `no-undef` reports before counting it). Top 10 by complexity and the counts by
  rule go in the digest.

- **Coverage:** when the repo has browser JS and UI tests, collect JS coverage
  from Chromium with Playwright's coverage API in a scratch script outside the
  repo (Playwright installed into `$B/pw` with `PLAYWRIGHT_BROWSERS_PATH` there):
  `page.coverage.startJSCoverage()`, drive the UI tests' flows (or the Stage 2
  screen walk) against the isolated instance, `stopJSCoverage()`, and report used
  bytes over total bytes per script. Say which drove it; a screen walk is not the
  test suite. Without UI tests, a browser, or a way to start the instance:
  **"JS coverage: not measured (reason)"**, with the reason from the closed list.

### Swift

- **Toolchain:** the installed one; no install. Point build output at the
  scratchpad: `swift build --scratch-path $B/cache/swift` and
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
- **Redirects:** `GOCACHE`, `GOMODCACHE`, `GOPATH`, `-coverprofile`, and `-o` for
  any `go build` output.

### Terraform and OpenTofu

[`types.md`](./types.md)'s infra entry sets the boundary: `validate` only; never
`plan`, `apply` or anything that contacts a provider with credentials.

- **Validate:** `terraform fmt -check -recursive -diff`, then
  `terraform init -backend=false -lockfile=readonly` and `terraform validate`
  (`tofu` for OpenTofu), both under the scrubbed environment with
  `TF_DATA_DIR=$B/cache/tf` and `TF_PLUGIN_CACHE_DIR=$B/cache/tf-plugins` added to
  its variables (`validate` reads the same data directory), so no `TF_VAR_*` or
  provider credential is visible. `init` downloads
  providers (network allowed); if it needs to write `.terraform.lock.hcl`, run it
  in a scratch copy of the module (`git archive <commit> <dir> | tar -x -C $B/clone`).
- **State files:** `git ls-files | grep -E '\.tfstate'` and
  `git check-ignore -v` on any found path; report the path and whether it is
  tracked, never its contents.
- **IaC misconfiguration:** `trivy config --cache-dir $B/cache/trivy --format json --output $B/raw/trivy-config.json <repo>`
  (see [Supply chain](#4-supply-chain)); `tflint` with `TFLINT_PLUGIN_DIR=$B/cache/tflint`
  when installed.
- **Currency:** the providers and versions in `.terraform.lock.hcl` and
  `required_providers` against the registry's latest, read from the registry's
  page; `required_version` against the vendor's support page.

### Shell

- **Install:** `shellcheck` and `shfmt` as release binaries in `$B/tools/bin`
  (or from a package manager if already installed).
- **Lint:** `shellcheck -f json $(git ls-files '*.sh')` plus files with a shell
  shebang (`git grep -lE '^#!.*(/|env )(ba|da|k)?sh( |$)'`); `-s sh` for a POSIX
  shebang. `shellcheck` does not support zsh: a zsh script is "not run (tool
  unavailable: no zsh support in shellcheck)". `shfmt -d` shows the format diff and never rewrites (`-w` is not
  used).
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
size          | lines per language (scc)                  | raw/scc.json
churn         | top 10: count | path

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
  ([`SKILL.md`](./SKILL.md) Stage 3). Lenses check the digest; they do not
  rediscover it ([`briefs.md`](./briefs.md) shared header).
- Everything in the digest is a fact with a command behind it. A number the
  baseline could not measure says "not measured" and why, never a guess.
