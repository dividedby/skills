---
name: repo-audit
description: >
  User-invoked, read-only audit of a repo's code, design, repo hygiene and docs, and market — parallel lens agents, every high finding verified at its source, published as one private report page with screenshots, mockups and a Now/Next/Later plan.
disable-model-invocation: true
---

# Repo Audit

A **read-only** review a maintainer can start and walk away from (overnight is
the intended use). It looks at a repo through four lenses — code and
performance, design, architecture/repo/docs, and the outside world — checks
every claim that matters against the source, and ends in **one report page**:
verdicts, a phased plan, evidenced findings, screenshots, mockups, and an honest
list of what was and was not verified.

Defers:
- Agent tool (lens agents run in parallel); the Artifact tool to publish the page.
- The built-in browser or the project's own run tooling, for screenshots.
- `/to-tickets` — only if the user later asks for the plan as issues.

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

Profile the project: languages, size (lines per area, largest files), test
suite and its run time, build and release path, CI, docs present, licence,
public or private. Decide which lenses apply and say so in one line each:

- **Design** runs only when there is a user-facing UI (app, site, or CLI output
  when the output is the product). A library skips it.
- **Market** runs when the project has users or competitors to compare against;
  internal tooling may skip it.

Read the user's prompt for a focus ("design only", "perf first") and weight the
briefs toward it.

**Done when:** the commit is pinned, the profile is written down, and the lens
lineup is stated with reasons.

## Stage 2 — Capture

Gather the evidence the lenses cannot gather blind:

- **Screenshots** of every main screen and state (empty, loading, error,
  populated), from a demo or sample-data build. Native apps: build and launch a
  separate copy (own bundle id) so the user's real install and data are
  untouched. Web apps: the built-in browser against a local dev server.
  Capture light and dark where the product supports both.
- **Baseline numbers** the code lens will need: test run time, build time,
  sizes of state or output files, anything cheap to measure now.

Stop any server or app this stage started before Stage 3 ends.

**Done when:** each main screen has a capture (or the reason it has none), and
the captures sit in the scratchpad.

## Stage 3 — Lenses (parallel)

Launch the applicable lens agents in one message so they run concurrently. Each
gets the pinned commit, the profile, the read-only rule, the relevant captures,
and its brief from [`briefs.md`](./briefs.md). Each writes a full report to the
scratchpad and returns a short summary.

| Lens | Model | Finds |
|---|---|---|
| Code and performance | sonnet | Cost at scale, measured; correctness and concurrency risk; I/O and API use; test health |
| Architecture, repo, docs | sonnet | Module shape, security and privacy, build and release, CI, docs, repo settings |
| Design | opus | Per-screen and app-level issues against the platform's guidelines; a mockup spec |
| Market and research | sonnet | Competitors, real user complaints, technical gotchas, projects worth copying |

Every finding carries severity (High / Med / Low), evidence (`file:line`, a
command and its output, or a URL), why it matters, a fix plan, and an effort
(S / M / L). Measured numbers say how they were measured; projections say so.

**Done when:** every launched lens has returned and its report file exists.

## Stage 4 — Verify (main session)

The lens reports are claims. Before anything reaches the page:

1. Re-check every **High** finding, and any finding the plan's "Now" column
   rests on, at its cited source. Read the line; rerun the command.
2. Correct what does not hold: lower the severity, fix the evidence, or drop the
   finding. Keep a list of every correction with the reason.
3. Where lenses disagree with each other or with the code (a research claim
   versus what the code does), show both readings and say which the evidence
   favours.
4. Context a lens lacked can change a rating (sandboxing, single-user scope,
   data size). Apply it and note it.

**Done when:** every High is confirmed or corrected, and the correction list is
written.

## Stage 5 — Plan and mockups

Turn verified findings into a **Now / Next / Later** plan:

- **Now** — high value, small effort, low risk; can start tomorrow.
- **Next** — the redesigns and refactors that need a go-ahead.
- **Later** — strategic work (release path, new capabilities).

Each plan item links to its finding. Keep the plan short enough to read in a
minute; the tables hold the detail.

Render the design lens's mockup spec as HTML inside the page, in the template's
mockup frame, following the theme toggle. Mockups are hand-written HTML and CSS
that match the platform's look; they are not screenshots of code.

## Stage 6 — Publish

Fill [`template.html`](./template.html): replace each `{{PLACEHOLDER}}`, clone
each `<!-- repeat: … -->` block per item, and embed screenshots as `data:` URIs
(downscale first; keep the page under the Artifact size limit). Preview it
locally in the browser pane, light and dark, desktop and phone width, before
publishing.

Publish as a **private** Artifact. Where the Artifact tool is unavailable, save
the page in the scratchpad and send it to the user as a file.

Close with a short message: the link, one verdict line per area, the top
findings, what was verified and what was not, confirmation that the repo is
unchanged, and **one question** — which part of the plan to start on. Offer
`/to-tickets` for the plan in one line.

**Done when:** the page is published (or sent), the repo shows no changes, and
the closing message names what is unverified.

---

## Failure conditions

- Any change to the audited repo. The audit has failed even if the report is good.
- A High finding on the page that was not re-checked in Stage 4.
- A projection presented as a measurement.
- Real personal data or a secret value in a screenshot or on the page.
