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
- `dividedby/claude-config` `docs/standards.md`, the fleet-standards checklist,
  read fresh on each run per [`fleet-standards.md`](./fleet-standards.md).

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
public or private, and the repo facts the fleet-standards check needs
([`fleet-standards.md`](./fleet-standards.md) section 2). These are the
profile's **known facts**; the lenses verify
them rather than trust them. Decide which lenses apply and say so in one line
each:

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
- **Fleet standards.** The main session reads the checklist fresh, records the
  commit it read, and marks every row pass, fail, n/a or not checked with
  evidence and a fix line, as [`fleet-standards.md`](./fleet-standards.md)
  directs. The checklist's checks run only when they are read-only; the audit
  fixes nothing it finds.

Stop any server or app this stage started before Stage 3 ends.

**Done when:** each main screen has a capture (or the reason it has none), the
captures sit in the scratchpad, and every checklist row has a result (or the
area is marked not checked, with the reason).

## Stage 3 — Lenses (parallel)

Launch the applicable lens agents in one message so they run concurrently. Each
gets the pinned commit, the profile, the read-only rule, the relevant captures,
and its brief from [`briefs.md`](./briefs.md), which also sets the shape of a
finding. The Architecture, repo and docs lens also gets the fleet-standards
results, so it does not re-report those rows. Each writes its report (and the
design lens its mockup spec) to a named scratchpad path and returns a short
summary.

| Lens                     | Model  | Finds                                                                                   |
| ------------------------ | ------ | --------------------------------------------------------------------------------------- |
| Code and performance     | sonnet | Cost at scale, measured; correctness and concurrency risk; I/O and API use; test health |
| Architecture, repo, docs | sonnet | Module shape, security and privacy, build and release, CI, docs, repo settings          |
| Design                   | opus   | Per-screen and app-level issues against the platform's guidelines; a mockup spec        |
| Market and research      | sonnet | Competitors, real user complaints, technical gotchas, projects worth copying            |

**Done when:** every launched lens has returned and its report file exists.

## Stage 4 — Verify (main session)

The lens reports are claims. Before anything reaches the page:

1. Re-check every **High** finding, and any finding the plan's "Now" column
   rests on, at its cited source. Read the line; rerun the command. This
   includes High fleet-standards fails.
2. Correct what does not hold: lower the severity, fix the evidence, or drop the
   finding. Keep a list of every correction with the reason.
3. Where lenses disagree with each other or with the code (a research claim
   versus what the code does), list it as disputed: both readings, and which
   the evidence favours.
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
that match the platform's look (swap the sample's desktop-window chrome for a
browser, phone or terminal frame as needed); they are not screenshots of code.

## Stage 6 — Publish

Fill [`template.html`](./template.html) as its header comment directs: one
section per lens, the Fleet standards table with a row per checklist row and
its verdict card, each `<!-- repeat: … -->` block cloned per item, every
`{{PLACEHOLDER}}` replaced, unused sections removed with their nav links, and
screenshots embedded as `data:` URIs
(downscale first; keep the page under the Artifact size limit). Preview it
locally in the browser pane, light and dark, desktop and phone width, before
publishing.

Publish as a **private** Artifact. Where the Artifact tool is unavailable, save
the page in the scratchpad and send it to the user as a file.

Close with a short message: the link, one verdict line per area (fleet
standards included, with the checklist commit), the top
findings, what was verified and what was not, confirmation that the repo is
unchanged, and **one question** — which part of the plan to start on. Offer
`/to-tickets` for the plan in one line.

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
