# Repo-audit checks the fleet standards, read fresh

> **Status: Accepted** — maintainer decision (2026-11-19). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

> **Amended by [ADR 0047](./0047-repo-audit-asks-once-before-running-untrusted-code.md)** (2026-11-23, [dividedby/skills#666](https://github.com/dividedby/skills/issues/666)) — the fleet-standards section applies only to a repo that passes the ownership test: a repo with no remote gets "Not assessed (Needs X: a remote)" and a repo that fails it, such as a third-party fork not in the index, gets "n/a (not a fleet repo)".

## Context

ADR 0042 made `repo-audit` a read-only audit with four lenses and one report
page. It checks a repo against general good practice, not against the
maintainer's own fleet-wide standards (formatting, linting, typechecking, CI,
lockfiles, changelog, labels, merge settings and the rest). The skills that
used to enforce those were retired by ADR 0039 and ADR 0040, and the rules sat
in several documents, none of them a checklist.

The rules now have one checklist: `docs/standards.md` in
`dividedby/claude-config` (dividedby/claude-config#214, #215, #216). Each row
gives an id, the requirement, the repo types it applies to, a read-only check
and the source document. The checklist changes when a source rule changes, and
rows are added over time (26 at the time of this ADR).

## Decision

`repo-audit` checks the audited repo against that checklist on every run
(dividedby/skills#619).

- **Read fresh.** The checklist is fetched from `dividedby/claude-config` at
  the current `main` commit on each run, with the local `~/repos/claude-config`
  checkout as fallback, and the page records which commit it read. If neither
  can be read, the area is reported as not checked with the reason; the rest of
  the audit goes on. This is the fetch-fresh pattern of ADR 0008, applied to a
  checklist instead of a skill.
- **Main session, not a lens.** Most rows are mechanical file tests and
  `gh api` reads, so the main session runs them during Stage 2 (Capture) and
  hands the results to the Architecture, repo and docs lens, which does not
  re-report them. ADR 0042's four lenses and six stages stay as they are.
- **Checks are data.** A row's check runs only when everything in it is on
  an allowlist: read-only commands (file reads and tests, `git -C` read
  subcommands, `gh api` GETs), file arguments inside the audited checkout,
  API paths on the audited repo, pipes and substitutions between listed
  commands, and no redirection but `2>/dev/null`. Anything else, environment
  assignments included, leaves the row not checked. ADR 0042's read-only rule
  holds: the audit fixes nothing it finds.
- **Results.** Each row is pass, fail, n/a (by the repo's type) or not checked,
  with evidence. Each fail cites its source, gets a severity and a one-line
  fix, and joins the plan like any other finding. The page gains a Fleet
  standards table and verdict card.
- **Stands alone for now.** The audit rubric (dividedby/skills#612) is not
  built. When it lands, Fleet standards becomes one of its areas, with the
  verdict rule in `fleet-standards.md`.

The procedure lives in a new supporting file, `fleet-standards.md`.

## Consequences

- Every run makes two more `gh api` reads against `dividedby/claude-config`
  plus the GETs the checklist's rows call for on the audited repo.
- A new or changed checklist row reaches the next audit without a change here.
  A row whose `applies to` uses a word the facts table does not cover is read
  plainly and the reading is recorded on that row.
- The audit depends on another repo's file format: the table must keep the
  columns `id`, `requirement`, `applies to`, `check` and `source`. If it does
  not, the area reports not checked rather than guessing.
- Fixing the fails stays outside the audit: settings through the API, files
  through one PR per repo, done separately.
