# Repo Audit — Repo Types, Size Tiers and Shape

The one home for what changes with the kind, size and shape of the repo: the
types and their added checks, the fallback for a repo that matches none, the
area set for non-code repos, the size tiers, the monorepo rule and the language
rule. `SKILL.md` Stage 1 and `briefs.md` cite this file and do not restate it.
The areas and the reasons an area goes unassessed are in
[`rubric.md`](./rubric.md).

## How to use

Stage 1 detects the types from the files present, records them as the profile's
`type` row, and for each matched entry:

- copies its **Added checks** and **Brief bullets** into the lens briefs
  that own them;
- records each area its **Usually not applicable** list names as applicable or
  Not assessed. The list is a hint; the profile's fact decides, and the reason
  is the one [`rubric.md`](./rubric.md)'s "Applies when" gives, naming that
  fact.

Types are additive. A repo can carry several; its applicable areas are the union
of what each type needs. A directory that is a different type from the rest
(a userscript folder in a docs repo) is profiled as its own part, as a package
is (see [Monorepos](#monorepos)). Examples in this file come from several types
and are illustrations, not a closed list.

## Types

### Userscript

- **Detect:** `*.user.js`, a `==UserScript==` header.
- **Added checks:** the version field bumped with each change; stable namespace
  and update and download URLs; anchored match and include patterns; no wildcard
  `@connect`; decoders that fail safe (bad input leaves the page alone); the
  store description (such as a `greasyfork-description.md`) kept current. A push to the default branch is a release.
- **Usually not applicable:** `data-integrity` when the script keeps no storage
  (Not applicable: no data store); the UI areas when it adds nothing visible to
  the pages (Not applicable: no user-facing UI).
- **Brief bullets:** Code: decoders and their failure path. Architecture: requested
  grants and connect targets. Product: update URLs. Design (when it adds UI): the pages
  it changes are its screens and its walkthroughs, and the store description is a
  branding surface.

### Library

- **Detect:** a manifest with `main`, `exports` or `lib`; a `[project]` table
  with no entry point; a crate with `lib.rs`; a library product with no
  executable.
- **Added checks:** the public API and its docs; semver and changelog
  discipline; what the package ships (a file list, no tests or secrets in the
  archive); examples in the docs run; the minimum supported runtime.
- **Usually not applicable:** `accessibility`, `content-branding`, `usability`
  (Not applicable: no user-facing UI).
- **Brief bullets:** Architecture: API surface and what counts as a breaking
  change. Product: the documented examples run.

### CLI

- **Detect:** `bin` entries, `[project.scripts]`, a `cmd/` directory, a `main`
  with an argument parser, an executable product.
- **Added checks:** argument-list exec, no shell strings built from input; exit
  codes that mean something; errors to stderr; `--help` and `--version`;
  release-binary hygiene (debug-only test hooks and code paths are absent from
  the release build, checked on the built binary as sideload's
  `scripts/check.sh` does; no debug symbols, test files or local paths);
  explicit device or simulator targeting where the CLI drives one (every
  command names a saved device id, never `booted` or an implicit default, as
  mobile-safari-lab does).
- **Usually not applicable:** none by default. Output is the UI when it is the
  product, so `accessibility`, `content-branding` and `usability` apply and use
  the probe. A CLI has no screens, so there is nothing to capture.
- **Brief bullets:** Code: argument handling and exit paths. Design: output
  width, colour and wording, judged from the probe; copy counts per command from
  its captured help and output; the walkthroughs are the documented commands end
  to end, run from the scratch build, with the output as evidence.

#### CLI probe

Build into the scratchpad ([execution boundary](./SKILL.md#execution-boundary)), then run
the built binary by absolute path from `$B/tmp`, never with the repo as the
working directory ([`baseline.md`](./baseline.md#environment)): `--help`, a bad argument, a missing
argument, the exit code of each, output at 80 columns, `NO_COLOR` set, and
output piped (non-TTY). Never point the probe at real accounts or data.

### Native app

- **Detect:** an app target in a package manifest (`Package.swift`), a project
  or workspace file (`*.xcodeproj`),
  an Android application module, an Electron or Tauri config.
- **Added checks:** work on the UI thread that should not be there; swallowed
  failures (`try?`, ignored results); signing, notarization, entitlements and
  runtime hardening, or the store path; the build setup itself (project files,
  build configs); CI runner availability for the targeted platform version;
  release-binary hygiene and explicit device or simulator targeting, as for a
  CLI, in scripts and docs as well as code.
- **Capture:** screenshots plus source. Build and run a separate copy from a
  clone in the scratchpad, with its own identity (bundle id or equivalent), so
  the user's real install and data are untouched; any change needed for that
  happens in the clone, never in the repo. The built app and any binary it
  builds start from the scratchpad, never with the repo as the working
  directory ([`baseline.md`](./baseline.md#environment)).
- **Never:** install to a real device, use the signing identity, or touch the
  user's real install or data.
- **Brief bullets:** Code: UI-thread work, actor or thread isolation, swallowed
  failures. Architecture: entitlements. Product: signing, notarization or store
  path, runner availability. Design: menu bar items against the platform's
  guidelines; the walkthroughs run in the scratch build at the window sizes the
  app supports, and copy counts come from the captures and the UI strings in
  source.

### Server or MCP

- **Detect:** server entry points, web framework imports, a `Dockerfile` or
  `compose.yaml` that runs a service, MCP SDK imports.
- **Added checks:** contract tests; lock drift; tools that claim to be
  read-only really are; log redaction; a health endpoint; the blast radius of an
  image tag; blocking the event loop.
- **Usually not applicable:** UI areas when the service has no UI (Not
  applicable: no user-facing UI).
- **Never:** call a live third-party API with real credentials.
- **Brief bullets:** Code: blocking calls on the request path. Architecture:
  read-only guarantees, redaction. Product: health and restart behaviour.

### Infra or ops

- **Detect:** `*.tf` or `*.tofu`, `compose.yaml`, systemd units, Ansible, an
  `ops/` directory of scripts.
- **Added checks:** `fmt` and `validate`; state files git-ignored (report the
  path of any state file, never its contents); pinned providers and image tags;
  failure notification (an `OnFailure` unit or equivalent); a heartbeat; a test
  per script; restore runbooks; cloud cost and quota notes.
- **Commands:** `init -backend=false` with `TF_DATA_DIR` in the scratchpad, then
  `validate` only.
- **Never:** `plan`, `apply`, or anything that contacts a provider.
- **Usually not applicable:** UI areas (Not applicable: no user-facing UI).
- **Brief bullets:** Architecture: state handling, pinning. Product: blast
  radius of a change. Code: a test per script.

### Local web app

- **Detect:** a server bound to loopback with a static or templated UI, a
  launcher script, no deploy workflow.
- **Added checks:** Host and Origin header checks (DNS-rebinding defence; the
  requests below); loopback-only binding; the launcher works on a fresh clone; an isolated data
  directory and port for capture and fault runs; backups; port conflicts.
- **Capture:** the isolated instances and the probe ([`SKILL.md`](./SKILL.md)
  Stage 2).
- **Host and Origin requests.** Sent to the second instance by the architecture
  lens ([`briefs.md`](./briefs.md) Security, privacy and data, Security). `$PORT`
  is its port, `<read>` a path that returns data, `<write>` a path and `<method>` the method
  that changes data (from the routes or the docs) and `<body>` the smallest body it
  accepts. Checksum the instance's data directory before and after. A server
  with no write path skips requests 2 and 3, Not applicable (no write path).
  1. Forged `Host`:
     `curl -si -H 'Host: attacker.example' http://127.0.0.1:$PORT/<read>`.
     Expect a refusal (4xx) with no data in the body.
  2. Cross-origin write:
     `curl -si -X <method> -H 'Origin: http://attacker.example' -H 'Content-Type: application/json' --data '<body>' http://127.0.0.1:$PORT/<write>`.
     Expect a refusal and an unchanged data directory.
  3. Write with no `Origin` header: request 2 without the `Origin` header. Expect a
     refusal when the repo's docs or code require an `Origin` on writes; otherwise
     report what happened and raise no finding.

  Record request, status and whether the data changed. A 2xx or a changed
  directory on request 1 or 2 is a hole reachable from outside the trust
  boundary, rated on the Severity scale.

- **Brief bullets:** Architecture: Host and Origin checks (the requests above),
  binding, where data lands. Code: behaviour on a taken port.

### Hosted web app or site

- **Detect:** a deploy workflow or platform config, an SSR framework, or static
  HTML only.
- **Added checks:** the deploy re-runs the gates; lab Core Web Vitals; security
  headers; the privacy page kept current; consent where the site sets cookies.
- **Capture:** the probe with Lighthouse, against a local build of the site
  ([`probe.md`](./probe.md)).
- **Usually not applicable:** `data-integrity` for static HTML only (Not
  applicable: no data store).
- **Brief bullets:** Architecture: headers. Product: deploy path. Design: Core Web
  Vitals and the privacy page.

### Docs, config or data

- **Detect:** no runtime: no tracked source beyond scripts (the non-code
  trigger, as in [Non-code repos](#non-code-repos)); Markdown, YAML, JSON or CSV
  dominate.
- **Added checks:** link integrity; accuracy against the code or sources it
  describes; safety labelling for commands; structure and freshness; hook or
  script self-tests.
- **Area set:** see [Non-code repos](#non-code-repos).

## Fallback

A repo, or a part of one, that matches no entry gets a generic profile built
from what is present: languages, entry points, build and test commands, docs, CI
and data files. Its checks come from the repo's own docs and rules and the 16
areas. The stack list is not closed: an unknown stack uses the universal tools
and says so. The page names the unrecognised type, marked "fallback profile",
and the run log records a Guesses row: "type not in `types.md`: <description>;
suggest an entry".

## Non-code repos

A repo with no tracked source beyond scripts (docs, config, data) typically
gets: `repo-hygiene` (structure, freshness and link integrity),
`feature-completeness` (accuracy against the code or sources it describes),
`external-facts` when its scripts or config hard-code external values,
`privacy`, `security` and `agent-readiness`. This set is a hint:
[`rubric.md`](./rubric.md)'s "Applies when" decides every area. Areas keyed to
tracked source apply to the scripts when any exist (scripts and hooks are
tracked source), and the other always-on and fact-keyed areas apply when their
fact holds. An area whose condition fails is Not applicable, with the deciding
fact ("no tracked source", "no user-facing UI"). The page may merge consecutive
Not-applicable rows that share one reason into one row naming their ids;
`findings.json` keeps a row per area.
The page carries no separate list of "not assessed" rows.

## Size tiers

Stage 1 counts tracked source lines from `git ls-files` with `wc -l`, or
`scc` or `tokei` when installed, and sets a tier.

- **Exclusions.** Vendored files (third-party directories, tracked dependency
  trees), generated files (lockfiles, minified files, build output, files with a
  generated marker), fixtures (test data, snapshots, recorded responses) and
  binary or data blobs. The profile lists each exclusion with its line count and
  counts test lines separately.
- **Tiers**, from the lines left after exclusions. The thresholds are
  approximate; more than about 1,000 tracked source files raises the tier by one.
  - **Small:** under about 2k lines. The main session reads everything.
  - **Medium:** up to about 50k lines. Each lens reads its areas in full where
    feasible.
  - **Large:** over about 50k lines. Each lens samples: the entry points, the
    largest files, churn hotspots (the baseline digest's churn row,
    [`baseline.md`](./baseline.md) section 1), the code behind each documented
    feature, and a random sample.
- **Coverage line.** Each lens ends its report with one line: what it read and how
  it chose. Example: "read 60 of 1,900 files: entry points, top 20 by churn, 20
  random". The page repeats it per lens.
- A sampled area is assessed on its sample and says so. It is not "Not
  assessed"; that reason is for an area the run never reached.

## Monorepos

Detected from a `pnpm-workspace.yaml`, a `package.json` `workspaces` field, a
`[tool.uv.workspace]` table, a Cargo `[workspace]`, a `go.work`, or `apps/` or
`packages/` directories that each hold a manifest.

- Stage 1 profiles each package: its type, its size and tier, and its applicable
  areas.
- The scorecard gets a verdict per package as well as overall; the overall
  verdict is the worst. A package's verdict comes from the findings in it.
- Fleet rows that apply per package are checked per package
  ([`fleet-standards.md`](./fleet-standards.md) section 3).
- A large monorepo with no packages named is audited in full at large-tier
  sampling. When the user names packages, only those are audited; the rest are
  Not assessed with the reason Not selected and listed on the page.

## Language

Stage 1 records the natural language of the docs and UI text. Text in a
non-space-delimited language (Chinese, Japanese, Thai) gets counts only
(characters, lines): no word or sentence thresholds and no density findings.
