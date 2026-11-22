# Repo Audit — Readiness Rubric

The one home for what the audit judges: the areas, when each applies, why an
area goes unassessed, the severity scale and the verdict rules. `SKILL.md`,
`briefs.md`, `fleet-standards.md` and `template.html` cite this file and do not
restate it.

The question the audit answers: is this repo ready for the people who use it?
Every area gets a verdict or a reason it has none. Nothing is skipped silently.

## Facts and applicability

Stage 1 records these facts in the profile, each with a source, and decides
every area's applicability from them. A fact is read from the files, not from the
repo's own claims.

| Fact               | Meaning                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Type               | The kind of project, one or more, as [`types.md`](./types.md) defines them; a repo matching none gets its fallback       |
| Target platform    | Where users run it: a browser, a phone, a desktop OS, a server, a pipeline                                               |
| Ships              | As [`fleet-standards.md`](./fleet-standards.md) section 2 defines it                                                     |
| UI present         | A user-facing UI: an app, a site, or CLI output when the output is the product. A library or a pure service has none     |
| Data store present | The project keeps data of its own that outlives a run: a database, a state file, a cache or queue on disk                |
| Tier               | Small, Medium or Large by [`types.md`](./types.md). No area's applicability depends on it; it sets how much a lens reads |

An area applies when its "Applies when" holds. An area that does not apply is
Not assessed, with the reason "not applicable" and the fact that decided it. A
method inside an area follows the same rule: a method whose condition fails is
skipped with a reason.

Fleet standards are a section, not an area, and are not in the table. They apply
to fleet repos. There is no ownership test yet, so every repo is checked, as
before. A repo shown not to be a fleet repo gets "n/a (not a fleet repo)".

## Areas

Order is the page order. `Id` is the slug used on the page and in
`findings.json`. `Owner` is the proposed owning lens; `Lens today` maps it onto
the lenses in [`briefs.md`](./briefs.md) until the roster changes. The market
lens owns no area: it feeds evidence to External facts and Tech stack.

| Area                                      | Id                     | Owner                        | Lens today                  | Applies when                                                 |
| ----------------------------------------- | ---------------------- | ---------------------------- | --------------------------- | ------------------------------------------------------------ |
| Code quality                              | `code-quality`         | Code, tests, performance     | Code and performance        | The repo has tracked source                                  |
| Architecture                              | `architecture`         | Architecture, security, data | Architecture, repo and docs | The repo has tracked source                                  |
| Tech stack, dependencies and supply chain | `tech-stack`           | Architecture, security, data | Architecture, repo and docs | A manifest, lockfile, workflow, container or IaC file exists |
| Tests                                     | `tests`                | Code, tests, performance     | Code and performance        | The repo has tracked source                                  |
| Security                                  | `security`             | Architecture, security, data | Architecture, repo and docs | Always                                                       |
| Privacy                                   | `privacy`              | Architecture, security, data | Architecture, repo and docs | Always                                                       |
| Data integrity                            | `data-integrity`       | Architecture, security, data | Architecture, repo and docs | Data store present                                           |
| Performance                               | `performance`          | Code, tests, performance     | Code and performance        | The repo has tracked source                                  |
| Accessibility                             | `accessibility`        | Design and UX                | Design                      | UI present                                                   |
| Content, copy and branding                | `content-branding`     | Design and UX                | Design                      | UI present                                                   |
| Usability and flows                       | `usability`            | Design and UX                | Design                      | UI present                                                   |
| Feature completeness vs docs              | `feature-completeness` | Product and docs conformance | Architecture, repo and docs | The docs describe behaviour the code should have             |
| Repo organisation, docs and hygiene       | `repo-hygiene`         | Product and docs conformance | Architecture, repo and docs | Always                                                       |
| Ops, release and observability            | `ops-release`          | Product and docs conformance | Architecture, repo and docs | Ships                                                        |
| External facts                            | `external-facts`       | Architecture, security, data | Architecture, repo and docs | The code hard-codes external values                          |
| Agent readiness                           | `agent-readiness`      | Product and docs conformance | Architecture, repo and docs | Always                                                       |

Each area below lists its checks, how they are done and the evidence a finding
needs. The four methods are **read** (source and docs), **run** (a build, test or
tool, inside the [execution boundary](./SKILL.md#execution-boundary)), **measure** (a number with its method) and
**browse** (the running UI, a capture, or a web page). A method an area lists
and the run does not use is skipped with a reason from the list below. A
finding with no evidence is not a finding.

### Code quality

- **Checks:** duplication, dead code, oversized files and functions, swallowed
  errors, naming.
- **How:** read; run the stack's own lint or dead-code tool if the repo has one;
  measure file and function sizes.
- **Evidence:** a `file:line` per sample; the command and count for a number.

### Architecture

- **Checks:** layering, dependency direction, god modules, demo or test code in
  production paths, whether a part should be its own module.
- **How:** read; run the repo's dependency-graph tool if it has one.
- **Evidence:** the `file:line` of the import or reference that breaks the
  direction.

### Tech stack, dependencies and supply chain

- **Checks:** runtime and framework end of life, version pinning and lockfile,
  lock drift, known vulnerabilities, licences, unused dependencies, and the CI,
  container and IaC supply chain (unpinned actions, image tags, provider
  versions).
- **How:** read; run the repo's own audit or lock-check command; browse the
  vendor's support page for end-of-life dates.
- **Evidence:** the manifest `file:line`, the tool's output line, or the URL and
  the date it was read.

### Tests

- **Checks:** the gates pass, run time, flakiness, untested risky paths,
  core-logic coverage, an end-to-end test of the primary flow, tests run in CI.
- **How:** read; run the test command; measure run time, count and ratio.
- **Evidence:** the command and its result; `file:line` samples. Cite the
  `test-size` numbers, do not remeasure them.

### Security

- **Checks:** the trust boundary, input validation, authentication and
  authorisation, secrets in the tree and in history, log redaction. A web app
  also gets OWASP ASVS 5.0 Level 1.
- **How:** read; run a secret scan; browse for the web checks.
- **Evidence:** `file:line`, or the command and result. A secret is reported as
  present with its path and commit, never its value.

### Privacy

- **Checks:** personal data stored and sent, file permissions on stored data,
  docs that match the code, no real data in fixtures or screenshots.
- **How:** read; measure permissions with `ls -l` on the data paths.
- **Evidence:** the `file:line` or path, with the permission bits. Never print
  the data.

### Data integrity

- **Checks:** validation on write, atomic writes, concurrent writers, backup and
  restore, recovery from corruption, format versioning, cache bounds.
- **How:** read; run against a scratch copy of the data, never the real one.
- **Evidence:** the `file:line` of the write path, or the scratch result.

### Performance

- **Checks:** hot paths at a realistic scale, startup time, page weight; for a
  hosted site, lab LCP, INP and CLS.
- **How:** measure with a scratch benchmark outside the repo; browse for page
  weight and the web vitals.
- **Evidence:** numbers with how they were measured. A projection is labelled as
  one.

### Accessibility

- **Checks:** WCAG 2.2 AA, keyboard-only primary flows, contrast in both themes,
  target size, reflow.
- **How:** read the UI source; browse the captures and the running UI; measure
  contrast and target size.
- **Evidence:** the capture path or `file:line`, and the criterion it fails.

### Content, copy and branding

- **Checks:** name and icon across surfaces; tokens against literals; type and
  spacing scale; dark-theme parity; words per screen, longest block, sentence
  length, jargon, duplicated explanations.
- **How:** read; browse; measure word counts.
- **Evidence:** the capture path or `file:line`, and the count.

### Usability and flows

- **Checks:** the primary tasks end to end, first run, empty and error states,
  recovery. For a product that targets phones, completion at 375 px.
- **How:** browse; run the flow from the demo or dev build.
- **Evidence:** the steps taken and where the flow broke, with a capture.

### Feature completeness vs docs

- **Checks:** each documented feature exists and works; TODO, FIXME, XXX and
  "not built" markers are listed; drift in both directions.
- **How:** read the docs and the code; run the feature.
- **Evidence:** the doc `file:line` and the code `file:line` or command output.

### Repo organisation, docs and hygiene

- **Checks:** structure, cruft, glossary, ADRs; README, CHANGELOG, licence,
  ignore rules, repo settings.
- **How:** read; read repo settings with `gh api` when a GitHub remote exists.
- **Evidence:** the path, `file:line` or API field.

### Ops, release and observability

- **Checks:** CI gates, dependency updates, versioning, the release path,
  fresh-clone install, rollback, runbooks, config; log levels and redaction,
  user-facing errors that say what to do, a health check or heartbeat, failure
  notification.
- **How:** read; run the fresh-clone install in a scratch clone.
- **Evidence:** the workflow or runbook `file:line`, or the install output.

### External facts

- **Checks:** domain values, external API limits and formats the code relies on,
  each against its official source; each `VERIFY` marker the repo carries.
- **How:** read the code for hard-coded values; browse the official source.
- **Evidence:** the code `file:line`, the source URL and the date it was read.

### Agent readiness

- **Checks:** the documented gates run as written, a focused test command
  exists, the agent instruction file matches the repo.
- **How:** read; run each documented command as written.
- **Evidence:** the doc `file:line` and the command's result.

## Not-assessed reasons

A skipped area or method gets one reason from this list, never silence. Name
the fact, tool or need in the reason.

- **Not applicable (fact):** the area's "Applies when" fails. Name the fact: "no
  user-facing UI".
- **Depth:** the run's depth did not reach it. Say what was sampled.
- **Untrusted not run:** it needs code from a repo whose code the run may not
  run.
- **Needs X:** credentials, a service or a device the run does not have (for
  example a GitHub remote). Name X.
- **Not selected:** the user limited the run to named packages. Name them.
- **Lens failed:** the owning lens failed. Give its reason.
- **Tool unavailable:** a scanner or browser the check needs is missing. Name it.

## Severity

Every finding in every area is rated on this scale, by how often it happens,
how much it costs and whether it persists.

- **Blocker:** harms a user or the maintainer if shipped now. Data loss or
  silent corruption; a secret or personal data exposed; a hole reachable from
  outside the trust boundary; the primary flow broken; a documented promise
  broken on the main path; a domain fact wrong in a number the user decides on;
  a failure users will hit with no recovery. For products that target phones or
  the web: unusable at 375 px or by keyboard.
- **High:** users hit it often, or it erodes trust. Wrong numbers, an unhandled
  error state, an AA failure on a main screen, a risky path untested, a
  reachable vulnerable dependency, a missing gate on a repo that ships.
- **Med:** friction or debt with a workaround.
- **Low:** polish.

Caps:

- A product opinion with no measured user impact is Med at most.
- A repo that does not ship cannot be Not ready for a missing release gate;
  those findings cap at Med.
- A hard-coded external fact with no update path is Med. One that is out of date
  with no user impact yet is Med. One that is wrong in a number the user decides
  on is a Blocker.

Repo rules: a failed row of the repo's own rules (`rules.md`, Stage 1) ranks
above a generic gap with the same impact wherever findings are ordered by
impact: a lens report, an area's table, the plan. Severity still follows the
scale and its caps. The finding cites the rule, and its `rule_source` is the
repo document's `file:line`.

## Verdicts

Each applicable area gets one verdict:

- **Not ready:** any Blocker.
- **Ready with fixes:** any High or Med.
- **Ready:** Low findings or none.
- **Not assessed:** a reason from the list above.

The overall verdict is the worst verdict among the applicable areas that have
one, and Blockers are listed by name. Applicable areas that are Not assessed are
listed beside it, so a Ready overall never hides an area nobody looked at.

## Fleet standards and the areas

A fleet-standards fail is also a finding in the area its requirement belongs to,
rated on the Severity scale, and counts toward that area's verdict. A secret-scan
fail is a Security finding; a missing release workflow is an Ops, release and
observability finding. The lens that owns the area cites the row and does not
re-rate it. If the owning lens failed, the area still takes the verdict its
fleet fails set, and its coverage keeps the "lens failed" reason for the
methods that lens would have run. The procedure and the row-by-row ratings are in
[`fleet-standards.md`](./fleet-standards.md).
