Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 1 — Scope

Pin the subject: repo path, branch, commit, remote (if any). Every agent brief
names that commit and every agent confirms which one it read. Then take the
read-only baseline for the [Execution boundary](../SKILL.md#execution-boundary): save
`git status --porcelain --ignored`, `HEAD`, the sorted path list and the nested
worktrees (`worktrees.txt`) to the scratchpad, and create the marker file
(`touch $B/proof/marker`) that Stage 6 compares file times against.
[`baseline.md`](../baseline.md#keeping-the-repo-unchanged) lists the files. At the
end of Stage 1, compare `HEAD` with the pin. A moved `HEAD` is an outside change:
re-pin, take the baseline again and restart Stage 1, and log it (the same rule
applies at each later check).

Profile the project at the pinned commit and branch: languages (any; each with
tracked source beyond a stray script), type or types and the areas each needs
([`types.md`](../types.md)), size (lines per area after the exclusions, largest
files), tier and exclusions with their line counts, the depth (`quick` or
`standard`, read from the prompt as [Lenses, depth and
budgets](../SKILL.md#lenses-depth-and-budgets) sets), packages for a monorepo, natural
language of the docs and UI text, test suite (test files or a test command) and
its run time, build and release path, CI (any CI config file: a
`.github/workflows/` workflow or another provider's config), docs present,
licence, remote, public or private (`gh api repos/$GH --jq .private` with a
GitHub remote; otherwise "unknown (no GitHub remote)"), the owner, the ownership
test and trust results and the execute answer (see **Ownership and trust**
below), the names of the environment variables the demo or sample mode needs
(the [Execution boundary](../SKILL.md#execution-boundary) passes only these), for a web UI
how its data can be isolated (a variable, flag, demo mode or temp profile, or
none, and where it was found), the ports its docs reserve, the widths and themes
it supports, the minimum target size its docs set, whether it is a hosted site,
the private literals the repo's own rules name, and the repo facts the
fleet-standards check adds ([`fleet-standards.md`](../fleet-standards.md#2-pin-the-repo-facts)
Pin the repo facts). Write the profile as a table of `fact | value | source`. A part or
package that matches no type, or a repo with none, follows the fallback in
[`types.md`](../types.md). In a large monorepo, ask once which packages to audit
when the run can ask.

**Private literals.** A private string the repo's own rules name (an agent
file's hard rule about a household ZIP, a town or a person's name) is listed in
the profile by kind with its source file and line, never its value. The values go
to `<scratchpad>/private-literals.txt`, one `kind<TAB>value` per line (no blank
lines), so a count can be grouped by kind without reading a value. The file
never goes in the publish folder, and every reader takes the value field only.
A lens that reports a hard-coded private value (a Privacy finding such as an
app default) adds it to the file too.

When the hard rule points at a real data file (a household list, a customer
export), extract its names and identifiers into the literals file without
printing them: command output goes straight into the file, and only counts and
kinds are shown. Drop ordinary words: filter against the system word list when
there is one, otherwise keep capitalised names, identifiers with a digit and
anything the rule names outright. A common word in the list redacts every
ordinary use of it and breaks the page, so the scrub's over-match warning
(Stage 6, **Scrub**) is read as a prompt to prune the list and rerun.

**Ownership and trust.** Two results, each recorded in the profile with its
source:

```text
owner              | acme-labs          | git remote get-url origin
ownership test     | fail (owner leg)   | gh api user --jq .login; gh api user/orgs --jq '.[].login'
trust              | untrusted          | ownership test; no override in the prompt
execute repo code  | no (asked 21:03 CT, no answer by 21:05 CT) | the question
```

- **Ownership test.** The maintainer owns the repo or the fleet includes it. It
  has three results: **pass**, **fail** and **no remote**. A repo with no remote
  (local only) gets **no remote**. Otherwise it passes when either leg holds.
  - **Owner leg:** the remote is on GitHub, its owner is the authenticated user
    or an org that user belongs to (`gh api user --jq .login`,
    `gh api user/orgs --jq '.[].login'`), and it is not a fork of a third-party
    repo (`gh api repos/$GH --jq '.fork, .source.owner.login'`; a fork passes
    this leg only when its source repo's owner also passes it).
  - **Index leg:** its `owner/name` is listed in `dividedby/claude-config`
    `docs/repos.md`, read at a pinned commit the way
    [`fleet-standards.md`](../fleet-standards.md#1-read-the-checklist-fresh)
    **Read the checklist fresh** reads the checklist
    (when the file cannot be read, that leg is skipped and the profile says
    so). It is the only way a third-party fork passes.

  Anything else fails: another host, another GitHub owner, a third-party fork
  not in the index, or a `gh` that cannot say who the user is.

- **Trust.** A repo is trusted when it passes the ownership test, when the
  result is no remote, or when the user's prompt says it is trusted or its code
  may run. Otherwise it is untrusted. Fleet standards follow the ownership
  result alone ([`fleet-standards.md`](../fleet-standards.md#2-pin-the-repo-facts)
  Pin the repo facts); a
  prompt override trusts the repo for running its code only and never changes
  that.
- **Untrusted: ask once.** Before anything in Stage 2 runs, the main session
  asks the user one question: may this run execute the repo's code? It lists
  what would run: tests, builds, the app or dev server, the repo's gate
  commands, scanners that execute repo code, and a fresh-clone install. When the
  user is driving the run, use one popup, batched with the monorepo package
  question when that is also due, and say in it that a prompt line ("the repo's
  code may run") answers it in advance and makes the repo trusted. Log the times
  asked and answered.
  - **Yes.** The code runs inside the [Execution boundary](../SKILL.md#execution-boundary),
    and every execution (gates and scanners that run repo code, tests, builds,
    the app for screenshots, any lens that runs code, a fresh-clone install)
    runs from a scratch clone of the pinned commit, never the repo folder. The
    yes covers this run only: a resumed run in the same session keeps it, a new
    run asks again.
  - **No, or no answer.** A run that cannot ask (unattended, or reporting to
    another session) does not ask: the answer is No. A question nobody answers is
    No. Nothing that executes the repo's code runs: its tests, builds, gate
    commands, app or dev server, screenshots that need it running, installs of
    its dependencies and any lens benchmark. Static reading, and scanners that do
    not execute repo code, still run. Each skipped method gets the reason
    "Untrusted not run" ([`rubric.md`](../rubric.md)). An area whose applicable
    methods all needed execution is Not assessed with that reason; an area still
    assessed on static methods lists the skipped methods in
    `coverage.skipped_methods`.
  - **The page** states the result (trusted, untrusted and yes, or untrusted and
    no, with the time) and names every area that lost a method or was Not
    assessed because of it ([Page content](./6-publish.md#page-content)). It also
    says that a prompt line trusting the repo answers the question next time.

Decide whether each area in [`rubric.md`](../rubric.md) applies, from the
profile's facts: it applies, or it is Not assessed with a reason from that
file's list. Record the decision and its fact per area. A type's
usually-not-applicable list is a hint; the fact decides.

Decide which lenses launch, from the Runs-when column of [Lenses, depth and
budgets](../SKILL.md#lenses-depth-and-budgets) and the depth. State each lens and each skip
with its reason, one line each, with the [`types.md`](../types.md) entries that
apply and the brief bullets they add. A UI-less repo skips `design` (a library
has none; [`rubric.md`](../rubric.md) defines a UI); a repo that fails the market
test, or a `standard` run with four core lenses, skips `market`; a `quick` run
skips `product`, `design` and `market`.

Read the user's prompt for a focus ("design only", "perf first") and weight the
briefs toward it.

**Read the previous run, when the prompt gives its page link.** Read its
`findings.json` now (the Artifact `files` map or the link) and check it as Stage
6's `diff` bullet directs: the diff reads only `findings[].key`, and `area` and
`severity` when present, so a schema mismatch elsewhere does not matter. Keep
its findings (key, area, title, evidence path) for Stage 3 and Stage 4, and its
pinned commit (the `profile` row whose `fact` is `commit`). Compute the changed paths read-only:
`git diff --name-only --no-renames <previous commit> <pinned commit>`, empty when
the commits are equal. When the previous commit is missing or not in the clone,
the changed paths are unknown: add a Guesses row and carry on.

**Check the profile's facts before any brief is written.** Every fact a brief
will rely on (a date, version, tracked or ignored file, count, port or command)
gets a source: a `file:line`, a command and its output, or a URL. A fact with
no source is marked "unverified" in the brief. Tracked or ignored is settled by
`git ls-files <path>`, so no fact of that kind stays unverified.

```text
fact                 | value          | source
lockfile tracked     | yes            | git ls-files Cargo.lock -> Cargo.lock
test command         | pnpm test      | package.json:14
build command        | make release   | Makefile:12
release cadence      | monthly        | unverified
```

**Harvest the repo's own rules.** The strongest spec for a repo is the one it
wrote itself, so the lenses hold it to that before generic practice. Write
`rules.md` to the scratchpad, one row per rule: `id | text | source file:line |
area | check`. The area is the [`rubric.md`](../rubric.md) area id the rule
governs (a UI doc's copy rule is `content-branding`, an infra repo's provider
pinning rule is `tech-stack`, a documented command is `agent-readiness`, a
README feature is `feature-completeness`). A marker's area is
`feature-completeness`, except a `VERIFY` marker's, which is `external-facts`.
The check is `read`, `run` or `browse`. Sources, where the repo has them:

- agent instruction files (`CLAUDE.md`, `AGENTS.md`);
- the README: its features, commands and screenshots;
- design, UI and brand docs;
- coding standards;
- accepted ADRs;
- acceptance and definition-of-done docs;
- glossary or context docs;
- in-code markers: `TODO`, `FIXME`, `VERIFY`, `XXX` and "not built".

Keep **rule-like sentences** only:

- A statement that something must, never or always be so, or an imperative
  about the product or the tree, that a file, command or behaviour at the pinned
  commit could break; every README feature and documented command.
- A decision in an accepted ADR, from its Decision section. With no Decision
  heading, take it from the body before the first `##` heading and from each
  dated Update or Amendment. Read the status line and every banner: superseded, rejected and proposed ADRs give no rows, a
  partly superseded one gives only the decisions its banner says stand, and one
  with no status or banner counts as accepted.
- A marker is a note left for later: the token begins a comment or list item or
  is followed by `:` or `(`, and "not built" is a status for a planned or
  missing item. A sentence that mentions the word is not a marker. List every
  marker; they are not filtered further. When the repo defines its own markers
  (a documented `grep` or a stated syntax, such as a `CLAUDE.md` that says
  "`grep -rn VERIFY`"), that definition wins for that token; cite its `file:line`
  in the rows.

Drop rationale, history, rejected alternatives, and process advice to the agent
that leaves nothing in the tree to check. A rule stated in several sources is
one row; name the others in its text. A repo with no such documents gets an
empty `rules.md` that says so. A row whose area is Not assessed is not checked,
with that area's reason.

At `quick`, harvest only agent files, coding standards, accepted ADRs and `VERIFY`
markers. At `standard`, when the harvest sources (the rule and claim documents
above) run past about 60 KB (`wc -c`; provisional), the main session may hand
`rules.md` to one `general-purpose` sonnet helper that runs before the lenses.
The helper is not a lens: it is not one of the four, not in `lens_coverage`, has
its own row in the run log's Agents table (`rules-harvest (helper)`) and its own
budget row, and its tokens count in the agent total. The main session still
checks that every row has a source `file:line`. No rules-harvest helper at `quick`.

**Done when:** the commit is pinned, the profile is written down with a source
per fact (types, tier, exclusions and package list included), the ownership test
and trust are recorded, the execute question is answered when it is due (before
Stage 2), every area is
marked applicable or Not assessed with its reason, `rules.md` is written with a
source `file:line` on every row, the lens lineup is stated with reasons, and the
read-only baseline (status snapshot, path list, nested worktrees and marker)
is saved.
