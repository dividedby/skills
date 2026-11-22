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
to fleet repos, as the ownership test in [`SKILL.md`](./SKILL.md) Stage 1
decides. A repo that fails it gets "n/a (not a fleet repo)".

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
| External facts                            | `external-facts`       | Architecture, security, data | Architecture, repo and docs | The repo hard-codes external values                          |
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

A person or an agent orients in a repo from its folders and its docs. The area
asks whether they lead somewhere true: nothing stray in the tree, no doc
nothing points to, and a glossary and ADR set that are lean and current when the
repo keeps them. Code against what the ADRs decide is `rules.md` work, not this
area's.

- **Checks:**
  - **Structure (reported, not scored).** Top-level tracked entries (folders and
    files, counted apart), the maximum directory depth with the deepest path,
    and for each top-level source folder whether its public surface is findable
    from the folder: an entry file, an index, a README or a manifest target that
    shows what it offers without opening the internals. Never a finding on its
    own: no threshold on the counts, no "too many top-level folders". On a Small
    tier repo the findability check is skipped, reason "Depth: Small tier,
    counts and depth only"; the counts and depth are still given.
  - **Cruft.** The baseline digest's cruft section
    ([`baseline.md`](./baseline.md) section 6: tracked generated, vendored or
    build output, large binaries, files an ignore rule matches) is cited as it
    stands, never re-run. Add what the digest cannot see; each item states its
    own test, so "stale" is checkable:
    - **Stale scratch directory:** a tracked folder named for throwaway use
      (`scratch`, `tmp`, `old`, `backup`, `archive`, `wip`, `playground`) or
      holding only experiments, with no commit touching it in 180 days
      (`git log -1 --format=%cs -- <dir>`) and no tracked file outside it naming
      it (`git grep -l <name>`, each hit judged in context: `tmp` and `old`
      match almost everywhere).
    - **Orphan doc:** a tracked doc (`.md`, `.rst`, or a `.txt` that is prose,
      not a tool input such as `CMakeLists.txt` or `robots.txt`) that no other
      tracked file links to or names by path or file name. Not orphans: README,
      CHANGELOG, licence, contributing, security and code-of-conduct files,
      agent files, the glossary, `.github` templates, any file a manifest,
      config or index registers, the ADRs (the ADR checks below cover them),
      and any file in a folder another tracked file names as where such docs
      live (a decisions folder, a records folder the glossary points to).
    - **Commented-out code:** a run of 3 or more consecutive comment lines that
      read as code (statements, calls, braces) rather than prose, in a source
      file. Examples in doc comments and licence headers do not count.
    - **Stale marker:** a `TODO`, `FIXME`, `XXX` or "not built" marker from the
      `rules.md` rows [`briefs.md`](./briefs.md) Product and docs conformance
      item 4 lists (not listed again here) that is stale when it names an issue
      or pull request that is closed, names a date or version already past, or
      sits on a line `git blame` dates over 365 days ago.
  - **Glossary, when present.** A glossary is `GLOSSARY.md`, `CONTEXT.md` or a
    file the README or agent file names as the project's vocabulary.
    - **Format:** each entry has a term, a one or two sentence definition and,
      where the term has rivals, the synonyms to avoid (`_Avoid_`). Count the
      entries missing a definition or breaking the pattern the rest follow.
    - **No implementation detail:** a definition that names a file, function,
      class, table or library says how the thing is built, not what it means.
    - **Avoided terms still used:** each `_Avoid_` term still used in tracked
      source, tests or user-facing strings, outside the glossary, ADRs and
      changelog. Match the term inside identifiers too, with
      `git grep -n -i <term>` and no `-w` (`client` finds `client_id` and
      `ClientId`), and judge each hit in context.
    - **Lean (reported):** the entry count, and the terms nothing outside the
      glossary uses, as candidates to prune.
  - **ADRs, when present.** The decision records, in `docs/adr/`, `adr/`,
    `docs/decisions/` or the directory the README names.
    - **Numbering:** gaps and duplicate numbers in the sequence, and a number
      format that changes partway.
    - **Status:** every ADR has one, from the set the repo's own ADRs use or
      Proposed, Accepted, Rejected, Deprecated, Superseded; a Proposed ADR
      untouched for 180 days is stale.
    - **Supersede links:** where an ADR supersedes or amends another, both
      directions exist (the old one says "Superseded by N", the new one says
      "Supersedes M"), both numbers resolve, and a superseded ADR is no longer
      marked Accepted.
    - **Noise ADRs:** a decision a person could reverse by editing one file
      that records no rejected alternative. The finding names which of three
      tests the ADR fails: hard to reverse, surprising without its context, a
      real trade-off. Judgement, so Low.
  - **Recommend a glossary entry or an ADR** only when a specific undocumented
    term or decision is named, with its `file:line`s: a concept the code names
    two ways, or a non-obvious hard-to-reverse choice the code makes and no doc
    records. This holds whether or not the file exists. It uses only what the
    lens read for its other areas; it does not go looking. With nothing named,
    there is no finding, however thin the docs.
  - **README, CHANGELOG, licence, ignore rules, repo settings:** present and
    current; ignore rules cover what the stack generates.
- **How:** read; measure with `git ls-tree`, `git ls-files` and `git log`; read
  repo settings with `gh api` when a GitHub remote exists. Without `-w` an
  avoided term also hits longer words and other senses (`client` in `clientele`,
  or a common word used as ordinary prose); only a hit in the term's sense is a
  use.
- **Evidence:** the path of every cruft item the lens finds, one per row, never
  a count alone. The baseline digest gives counts and its top 10 with sizes, so
  those 10 are cited as rows and the rest as "N more" with the raw digest
  path where they live. For an avoided term the `git grep` hit count, the count
  judged in sense and up to five `file:line` samples; for an ADR problem the ADR
  numbers and the line that breaks the rule; for structure the counts and the
  command. The path, `file:line` or API field otherwise.
- **Severity:** a cruft finding is Med when it misleads a reader or an agent
  (an orphan doc that describes removed behaviour, a scratch folder that
  shadows a real one), otherwise Low. Structure never produces one.
- **Skips:** each check or test that cannot run is skipped with its reason, and
  the rest of the area still runs:
  - no glossary: the glossary checks, "Not applicable (no glossary)";
  - no ADRs: the ADR checks, "Not applicable (no ADRs)";
  - no tracked source: findability and commented-out code, "Not applicable (no
    tracked source)";
  - no GitHub remote: the closed-issue test for stale markers and the repo
    settings, "Needs X: a GitHub remote"; the date, version and age tests still
    run;
  - shallow history (`git rev-parse --is-shallow-repository` prints `true`):
    the commit-age and `git blame` tests, "Needs X: full git history";
  - a digest check the baseline did not run: its reason from the digest's Not
    run table.

### Ops, release and observability

- **Checks:** CI gates, dependency updates, versioning, the release path,
  fresh-clone install, rollback, runbooks, config; log levels and redaction,
  user-facing errors that say what to do, a health check or heartbeat, failure
  notification.
- **How:** read; run the fresh-clone install in a scratch clone.
- **Evidence:** the workflow or runbook `file:line`, or the install output.

### External facts

- **Checks:** each value the repo hard-codes from outside itself, against its
  official source, and how the values stay current. A fact is:
  - a constant or table in a config or data file (a tax table or an eligibility
    threshold in a web app, a quota or an instance limit in infra code);
  - a value with a year, a date, a percentage or an amount of money;
  - a value the repo marks (`VERIFY`, "update yearly"), including the
    `rules.md` rows with this area;
  - an external API limit or format the code relies on: a quota, a rate limit, a
    page-size cap, a deprecation, a format change.

  Currency is an update step, a test that pins the values, or a date after
  which the app warns.

- **How:** read the code, config and data files for the facts; browse the
  official source for each: a government or standards-body page, the provider's
  own docs, the standard. A blog, a forum or the repo's own comment is not a
  source. A fact whose source cannot be found or read is "couldn't verify", never
  a match. Over 30 candidates, check every marked value and every value that
  feeds a user-facing number (an amount, date or limit the user sees or decides
  on), then list the rest as not checked with the count.
- **Evidence:** per fact, the code `file:line`, the source URL, the date it was
  read, the value found and the result: match, mismatch or couldn't verify. A
  mismatch gives both values. The `file:line` of the update step, the pinning
  test or the warning, or a statement that there is none.

### Agent readiness

An agent has no memory of the repo: each session it orients from the code, the
agent file and the commands it can run. The area asks whether it can do that
and check its own work. An agent file is `CLAUDE.md`, `AGENTS.md` or another
agent instruction file the repo keeps, nested ones included.

- **Checks:**
  - **Documented gates run verbatim.** Each gate an agent file documents, from
    the baseline digest's Gates (documented vs actual) table
    ([`baseline.md`](./baseline.md) section 2): pass or fail, wall time, and the
    manual steps needed, meaning a step the doc leaves out that the run needed
    (a tool install, an environment variable). The check judges the gates an
    agent file documents; the page's gates table lists every gate in the digest,
    and a gate the agent file does not document shows its README or CI
    `file:line` with "not in agent file".
  - **Time to first signal.** A focused fast test command exists: one file, one
    test or one package, documented or discoverable from the test config. Its
    absence is a finding. A repo with no tracked source skips this row, reason
    "Not applicable (no tracked source)".
  - **Named paths and commands exist.** Every path and command an agent file
    names exists and works.
  - **Repo-specific facts only.** The file holds facts about this repo. It does
    not copy fleet or global rules or restate docs; it points to the glossary,
    ADRs and docs instead.
  - **Size.** Each agent file's lines and words are reported, not scored.
  - **Open issues (optional).** Sample 10 open issues for one state label and
    acceptance criteria. Only when the repo has a GitHub remote and more than 5
    open issues; otherwise skipped, reason "Needs X: a GitHub remote" or "Not
    applicable (5 or fewer open issues)".
- **How:** read the agent files and the digest; this area does not re-run
  gates. A named command that is a gate takes the baseline's result. Any other
  named command is checked for existence (the script, the make or just target,
  the package script, the binary) and run only when it is read-only and inside
  the [execution boundary](./SKILL.md#execution-boundary); otherwise it is
  checked for existence only and recorded as "exists, not run (not read-only)",
  a finding only if missing. Run the focused command once, on one test, inside the
  boundary, and record its wall time. Compare each agent file's statements
  against the docs they overlap to find duplicates.
- **Evidence:** the agent file `file:line` of each stale path or command, each
  missing manual step and each duplicated item (a duplicate cites both
  `file:line`s); the baseline gate row; the focused command, its result and
  wall time; the issue numbers sampled.
- **No agent file:** one finding, rated on the scale. The gate rows still run,
  from the documented gates the README, CI config and manifests give, and so
  does time to first signal. Exactly two rows are Not assessed, Named paths and
  commands and Repo-specific facts only, reason "Not applicable (no agent
  file)". The open-issues sample still runs under its own condition, which does
  not depend on an agent file; Size has nothing to report.

## Not-assessed reasons

A skipped area or method gets one reason from this list, never silence. Name
the fact, tool or need in the reason.

- **Not applicable (fact):** the area's "Applies when" fails. Name the fact: "no
  user-facing UI".
- **Depth:** the run's depth did not reach it. Say what was sampled.
- **Untrusted not run:** it needs code from an untrusted repo and the run was
  not allowed to execute it: the answer was No, or nobody answered
  ([`SKILL.md`](./SKILL.md) Stage 1, Ownership and trust).
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
