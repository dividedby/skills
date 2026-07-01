---
name: skill-divergence-audit
disable-model-invocation: true
description: >
  Recurring, report-only audit that diffs this repo's published skills against
  Matt Pocock's repo and the agent-research KB, classifies each gap, and
  proposes realignment issues — at most one per run, cleared against a
  high independent bar. Never edits, commits, or merges; proposals go only
  through the guarded filing path.
---

# Skill Divergence Audit

This skill **mechanizes what was done by hand**: a periodic diff of our
published skills against Matt Pocock's `mattpocock/skills` and the
`agent-research` knowledge base, classified into actionable categories, with
the strongest gaps proposed as labeled issues for the maintainer to decide on.

**It proposes; it never applies.** The only mutation it may make is filing
issues — labeled `source:skill-audit`, capped at one per run, deduplicated
against open issues, and passed through the leak guard before anything reaches
the tracker. The producer/decider split
([ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
is what makes unattended operation safe.

The **≤1-per-run cap**, **dedup**, and **leak guard** are enforced by code,
not prompt discipline. The mechanical details — the gate, the sanitizer, and
the filing path — follow [proposal-flow.md](../apply-agent-research/proposal-flow.md)
exactly. The pure classify core ships with this skill under
[`lib/`](lib/) and is unit-tested there.

## Step 1 — Scan: collect our skill set and both upstream sources

Gather three inputs, all read-only:

1. **Our published skills** — enumerate every `skills/*/*/SKILL.md` in this
   repo. For each, extract the skill `name` (from frontmatter) and a set of
   named **pillars** — the major concept-stations the SKILL.md describes (e.g.
   Scan, Classify, Render, Apply, Anti-patterns). The pillars come from the
   SKILL.md's section headings; read each file and record them.

2. **Matt's skill set** — clone `mattpocock/skills` fresh (or read its
   latest `main`). For each skill found under `skills/`, extract its name and
   pillars with the same method. Tag each entry ``source: "matt"``.

3. **Agent-research KB** — read the public knowledge mirror
   (`agent-research-knowledge`). For each subject area, read the `index.md`
   and note which practice concepts are named. Map each to a skill-name and
   pillar set. Tag each entry ``source: "kb"``.

Completion criterion: three flat lists — our skills, Matt's skills, KB
entries — each a list of dicts with at minimum `name` and `pillars`. No
network calls after this step.

## Step 2 — Classify: diff and categorize

Feed the three lists to the pure classifier in
[`lib/divergence.py`](lib/divergence.py):

```
divergence.diff(our_skills, upstream_skills)
```

where `upstream_skills` is the merged Matt + KB list. The function runs
deterministically against its inputs and returns a list of divergence dicts,
each carrying one of five categories:

| Category | Meaning | Proposed? |
|---|---|---|
| `MISSING_HERE` | Upstream names a skill/practice we have no equivalent for | yes |
| `OUTDATED_HERE` | We have a skill for this surface but are missing pillar(s) upstream covers | yes |
| `DIVERGED` | We cover the same surface but our guidance directly contradicts upstream on a named point | yes |
| `NO_UPSTREAM_EQUIVALENT` | We have a skill with no upstream analogue — surface in the report for human confirmation; never proposed | report-only |
| `ALIGNED` | Same surface, no gap — no action needed | report-only |

Only `MISSING_HERE`, `OUTDATED_HERE`, and `DIVERGED` enter the proposal
pipeline (Step 4 onward).  `NO_UPSTREAM_EQUIVALENT` and `ALIGNED` are
**report-only**: they appear in the findings table for the operator's awareness
but are never passed to `to_candidates` and never filed as issues.  The
classifier lives in pure code so the categorization is reproducible and not a
per-run judgment call.

**Do not re-derive the classification in prose.** Call the pure function.

## Step 3 — Render: emit the markdown findings report

Call `divergence.render_report(divergences)` to produce the findings table.
Print it to stdout for the operator's record. The report is the audit
artifact; it is *not* filed to the tracker.

The report shows every non-ALIGNED finding sorted by category (DIVERGED first,
then MISSING_HERE, then OUTDATED_HERE, then NO_UPSTREAM_EQUIVALENT), with
skill name, category, detail, and source.

## Step 4 — Apply the adversarial pre-gate filter

Before any candidate reaches the proposal gate, challenge it on five rejection
criteria (from
[proposal-flow.md](../apply-agent-research/proposal-flow.md#the-proposal-gate--run-once-over-every-channels-candidates)):

1. **Catalog overlap** — does this duplicate a published skill, installed skill,
   or wontfixed proposal? Judge by the principle behind any prior closure, not
   just the dedup key.
2. **Restatement dilution** — does the finding mostly restate what existing
   skills already own, with only a thin novel core?
3. **Frequency fit** — would the maintainer encounter this gap regularly enough
   for a proposal to be worth acting on?
4. **Evidence strength** — is the upstream source strong enough to motivate
   exactly this proposal, or is the diff an artifact of a naming mismatch?
5. **Concreteness** — is the specific surface named and the change concrete
   enough to implement without ambiguity?

A candidate that cannot clear all five is dropped before the gate sees it.

## Step 5 — Run the budgeted proposal gate and file

Call `divergence.to_candidates(divergences)` to convert the surviving
classified findings to gate-ready candidates (with `dedup_key`, `priority`,
and metadata). Then gather the existing open-issue dedup keys and run the gate
**once**:

```
echo '{"candidates": [...], "open_issues": [...], "budget": 1}' \
  | python3 <skill-dir>/lib/cli.py gate
```

The gate returns at most **one** ranked candidate. For that candidate, write the issue
body to a file (with the dedup-key HTML comment and a Sources line), then file
through the **guarded path**:

```
python3 <skill-dir>/lib/cli.py file \
  --title "<concise title>" \
  --body-file <path> \
  --label source:skill-audit \
  [--repo <owner/name>] [--marker <private-name> ...]
```

`file` sanitizes `title + body`, then runs `gh issue create` **only on ALLOW**.
Never call `gh issue create` directly — the guard cannot be bypassed, and the
skill is never allowed that tool.

Label: `source:skill-audit` — reuse the existing label; do not create a new one.

Completion criterion: gate has run exactly once; every returned candidate has
been filed through `cli.py`; nothing else has been written.

## Quality bar (applies to every proposal)

- **Recommendations, not a menu.** Each filed issue makes one call. If nothing
  clears the bar, say so and stop — a forced finding is worse than none.
- **Concrete before/after.** Name the surface (which SKILL.md section, which
  pillar), describe what is there now in prose (no pasted code or path tokens
  that trip the guard), and state the exact gap or change.
- **Generalized, leak-safe.** Describe the need so it reads as broadly useful;
  carry no private content. The guard is a backstop, not a license to skip
  prose discipline.
- **Cite the source.** Reference the upstream skill or KB note so a reviewer
  can trace the basis.

## Dependencies

This skill has a **hard runtime dependency** on the sibling
[`apply-agent-research`](../apply-agent-research/) skill.  `lib/cli.py`
resolves `proposal_gate` and `sanitizer` by sibling path
(`../apply-agent-research/lib/`) at import time — they are reused, not
vendored, so the security-relevant guard stays current (ADR 0008).  The
sibling must be present alongside this skill in any checkout or install;
fetching only `skill-divergence-audit` alone is not sufficient (ADR 0024).

## Anti-patterns

- **Re-deriving the classification in prose.** The diff and classify logic is a
  tested pure function (`lib/divergence.py`); call it.
- **Filing ALIGNED or NO_UPSTREAM_EQUIVALENT findings.** Both are report-only
  categories.  `ALIGNED` means no gap.  `NO_UPSTREAM_EQUIVALENT` is an
  observation, not an action item — surface it in the report for human review,
  do not pass it to `to_candidates` or file it as an issue.
- **Creating a new label.** Use `source:skill-audit`; it already exists.
- **Calling `gh issue create` directly.** All writes go through
  `cli.py file`; the leak guard cannot be bypassed.
- **Running the gate more than once per run.** Gate runs once over the merged
  candidate set; there is no second pass.
- **Filing more than one proposal.** The budget is a ceiling and the code
  enforces it. A typical run files 0–1.
- **Treating a naming mismatch as a gap.** Two skills covering the same
  concept under different names are not a divergence — read the content, not
  just the slug, before classifying.
