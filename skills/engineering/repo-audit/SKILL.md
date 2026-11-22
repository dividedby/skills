---
name: repo-audit
description: >
  User-invoked, read-only audit of a repo's code, design, repo hygiene and docs, fleet standards, and market — parallel lens agents, every high finding verified at its source, published as one private report page with screenshots, mockups and a Now/Next/Later plan.
disable-model-invocation: true
---

# Repo Audit

A **read-only** review a maintainer can start and walk away from (overnight is
the intended use). It looks at a repo through four lenses — code and
performance, design, architecture/repo/docs, and the outside world — checks
the repo against the fleet-wide repo standards, checks every claim that matters
against the source, and ends in **one report page**:
verdicts, a phased plan, evidenced findings, screenshots, mockups, and an honest
list of what was and was not verified.

Defers:

- Agent tool (lens agents run in parallel); the Artifact tool to publish the page.
- The built-in browser or the project's own run tooling, for screenshots.
- `/to-tickets` — only if the user later asks for the plan as issues.
- `dividedby/claude-config` `docs/standards.md` (the fleet-standards checklist)
  and `docs/testing.md`, read fresh on each run per
  [`fleet-standards.md`](./fleet-standards.md).

## When to use

- You want a full, evidenced picture of a repo: what is slow, what is fragile,
  what looks unfinished, what the docs lack, and where it stands against others.
- You want a design bar check ("does this look first-class?") with concrete
  mockups, not adjectives.
- You want a plan to pick from, not tickets filed for you.

## When not to use

- Reviewing one branch or PR: use `/code-review`.
- One design decision: use `/council`.
- You want issues filed now: run this, then `/to-tickets` on the plan.

## The read-only rule

The audited repo is never changed: no edits, commits, branches, pushes, issue or
PR writes, or settings changes. Builds and tests may run when they write only to
ignored build output. Benchmarks, scratch packages, captured screenshots and the
page itself live in the session's scratchpad. If a check would need a change to
the repo, record it as unverified instead. The run ends with `git status`
showing nothing new.

Real user data never enters the report: screenshots come from a demo, sample or
dev build, and secrets found in history are reported as present, never printed.

---

## Stage 1 — Scope

Pin the subject: repo path, branch, commit, remote. Every agent brief names that
commit and every agent confirms which one it read.

Profile the project: languages (Node/TS, Python, Swift, Go, shell, userscript
`*.user.js`; each with tracked source beyond a stray script), size (lines per
area, largest files), test suite (test files or a test command) and its run
time, build and release path, CI (`.github/workflows/` holds a workflow), docs
present, licence, public or private (`gh api repos/$GH --jq .private`), and the
repo facts the fleet-standards check adds
([`fleet-standards.md`](./fleet-standards.md) section 2). Write the profile as
a table of `fact | value | source`.

Decide which lenses apply and say so in one line each:

- **Design** runs only when there is a user-facing UI (app, site, or CLI output
  when the output is the product). A library skips it.
- **Market** runs when the project has users or competitors to compare against;
  internal tooling may skip it.

Read the user's prompt for a focus ("design only", "perf first") and weight the
briefs toward it.

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

**Done when:** the commit is pinned, the profile is written down with a source
per fact, and the lens lineup is stated with reasons.

## Stage 2 — Capture

Gather the evidence the lenses cannot gather blind:

- **Screenshots** of every main screen and state (empty, loading, error,
  populated), from the project's own demo, sample-data or dev mode. Native
  apps: build and run a separate copy from a clone in the scratchpad,
  with its own identity (bundle id or equivalent), so the user's real install
  and data are untouched; any change needed for that happens in the clone,
  never in the repo. Web apps: the built-in browser against a local dev
  server. Capture light and dark where the product supports both.
- **No safe way to run it** (no demo mode, real accounts required): skip
  screenshots, say so, and let the design lens work from source.
- **Baseline numbers** the code lens will need: test run time, build time,
  sizes of state or output files, anything cheap to measure now.
- **Fleet standards.** The main session runs the check in
  [`fleet-standards.md`](./fleet-standards.md) and fixes nothing it finds.

Stop any server or app this stage started before Stage 3 ends.

**Done when:** each main screen has a capture (or the reason it has none), the
captures sit in the scratchpad, and every checklist row has a result (or the
area is marked not checked, with the reason).

## Stage 3 — Lenses (parallel)

Launch the applicable lens agents in one message so they run concurrently. Each
gets the pinned commit, the profile, the read-only rule, the relevant captures,
the fleet-standards results and the baseline numbers, and its brief from
[`briefs.md`](./briefs.md): the brief's heading names the lens's model, its body
says what the lens finds, and the shared header sets the shape of a finding and
how to use the profile and those results. Each writes its report (and the
design lens its mockup spec) to a named scratchpad path and returns a short
summary.

**Done when:** every launched lens has returned and its report file exists.

## Stage 4 — Verify (main session)

The lens reports are claims. Before anything reaches the page:

1. **Merge duplicates, before any re-check.** Two findings are duplicates when
   they cite the same `file:line` or the same command output.
   - Keep one, in the lens that owns the finding's rubric area; while lenses
     own no rubric areas, in the lens with the most specific evidence. Record
     the other lenses as "also reported by".
   - Keep the highest severity that survives verification.
   - A finding that restates a fleet-standards row is folded into that row.
   - Each merge is a "merged" line in the correction list.
2. Re-check every **High** finding, and any finding the plan's "Now" column
   rests on, at its cited source. Read the line; rerun the command. This
   includes High fleet-standards fails.
3. Correct what does not hold: lower the severity, fix the evidence, or drop the
   finding. Keep a list of every correction with the reason.
4. Where lenses disagree with each other or with the code (a research claim
   versus what the code does), list it as a "disputed" line in the correction
   list.
5. Context a lens lacked can change a rating (sandboxing, single-user scope,
   data size). Apply it and note it.

**Done when:** duplicates are merged, every High is confirmed or corrected, and
the correction list (merged, corrected and disputed lines) is written.

## Stage 5 — Plan and mockups

Turn verified findings into a **Now / Next / Later** plan:

- **Now** — high value, small effort, low risk; can start tomorrow.
- **Next** — the redesigns and refactors that need a go-ahead.
- **Later** — strategic work (release path, new capabilities).

Each plan item links to its finding. Keep the plan short enough to read in a
minute; the tables hold the detail.

Render the two or three screens behind the top findings, the only ones the
design lens specs, as HTML inside the page, in the template's mockup frame,
following the theme toggle. Mockups are hand-written HTML and CSS that match the
platform's look; they are not screenshots of code. The template ships a browser
frame, and its header says when to copy a desktop-window, phone or terminal
frame from [`snippets.html`](./snippets.html).

## Stage 6 — Publish

Fill [`template.html`](./template.html) as its header comment directs; the
fill rules live there. Embed each screenshot at its original width up to
1,280 px, downscale only above that, never upscale, as JPEG at about q70, and
keep the page under the Artifact size limit. Preview it locally in the browser
pane, light and dark, desktop and phone width, before publishing.

Publish as a **private** Artifact. If the Artifact tool offers a `quickstart`,
run it (it is read-only), then keep this skill's template, which already meets
the page contract. Where the Artifact tool is unavailable, save the page in the
scratchpad and send it to the user as a file.

Close with a short message: the link, one verdict line per area (fleet
standards included, with the checklist commit), the top
findings, what was verified and what was not, and confirmation that the repo is
unchanged. When the run reports to the user, end with **one question** — which
part of the plan to start on — and offer `/to-tickets` for the plan in one
line. When it reports to another session, end with the page link and the plan's
first item instead.

**Done when:** the page is published (or sent), the repo shows no changes, and
the closing message names what is unverified.

---

## Failure conditions

- Any change to the audited repo. The audit has failed even if the report is good.
- A fleet-standards check run that was not read-only, or a checklist copy
  reused instead of read fresh.
- A High finding on the page that was not re-checked in Stage 4.
- A projection presented as a measurement.
- Real personal data or a secret value in a screenshot or on the page.
