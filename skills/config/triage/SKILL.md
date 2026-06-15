---
name: triage
description: Triage issues through a state machine driven by our label vocabulary. Use when the maintainer wants to see what needs attention, triage a specific issue, move an issue to a new state, or manage issue workflow on this repo's GitHub tracker.
---

# Triage

Move issues on the project issue tracker through a small state machine. Every triaged issue carries exactly one state label, one category label, and one size label.

## Reference docs

- `docs/agents/labels.md` — full label vocabulary (state, category, size, channel)
- `docs/agents/issue-tracker.md` — `gh` CLI conventions for reading, commenting, labelling
- `docs/agents/idea-inbox.md` — inbox intake/drain convention
- `docs/design/skill-request-flow.md` + ADR 0021 — skill-request triage path

## State machine

**State labels** (apply exactly one):

- `needs-triage` — maintainer needs to evaluate
- `ready-for-agent` — fully specified, ready for an AFK agent
- `ready-for-human` — needs human implementation
- `blocked` — waiting on an external dependency or decision
- `wontfix` — will not be actioned

**Category labels** (apply exactly one): `bug` / `enhancement` / `chore` / `epic`

**Size labels** (apply exactly one): `size:S` / `size:M` / `size:L` / `size:XL`

Normal flow: an unlabelled issue goes to `needs-triage` first; from there it moves to `ready-for-agent`, `ready-for-human`, `blocked`, or `wontfix`. The maintainer can override at any time — flag transitions that look unusual and confirm before proceeding.

**Conflicting state labels.** If an issue already carries two or more state labels, surface the conflict and ask the maintainer which one to keep before doing anything else. Never silently pick one.

## Invocation

The maintainer invokes `/triage` and describes what they want in natural language. Interpret the request and act. Examples:

- "Show me anything that needs my attention"
- "Let's triage #42"
- "Move #42 to ready-for-agent"

## Show what needs attention

Query the issue tracker and present two buckets, oldest first:

1. **Unlabelled** — never triaged (no state or category label).
2. **`needs-triage`** — evaluation in progress.

Show counts and a one-line summary per issue. Let the maintainer pick.

```
gh issue list --state open --label "needs-triage" --json number,title,createdAt \
  --jq 'sort_by(.createdAt) | .[] | "[#\(.number)] \(.title)"'
```

For the unlabelled bucket, list issues that carry none of the known state or category labels. Oldest first.

## Triage a specific issue

1. **Gather context.** Read the full issue — body, comments, labels, reporter, dates. Parse any prior triage notes so you don't re-ask resolved questions. Explore the codebase using the project's domain glossary and ADRs in the area.

2. **Check Idea Inbox.** If the issue body or title describes something that belongs in the intake/drain path (`docs/agents/idea-inbox.md`), flag it. Do not re-file inbox ideas as tracked issues.

3. **Check for skill-request.** If the issue carries the `skill-request` label, do not follow the generic path — see **Skill-request triage** below.

4. **Recommend.** Tell the maintainer your category, state, and size recommendation with reasoning. Wait for direction.

5. **Apply the outcome:**
   - `ready-for-agent` → post a strong agent brief (see below) and apply labels.
   - `ready-for-human` → post a brief-style comment explaining why it can't be delegated (judgment calls, external access, design decisions, manual testing) and apply labels.
   - `blocked` → post a comment stating what is blocking and on what (issue number, external dependency, or open decision) and apply labels.
   - `wontfix` → post a rationale comment and apply labels.
   - `needs-triage` → apply the label. Optional comment if there is partial progress.

Apply labels via:

```
gh issue edit <number> --add-label "<state>,<category>,<size>" --remove-label "<old-state>"
```

## Skill-request triage

When triaging a `skill-request`-labelled issue, route through the documented flow in `docs/design/skill-request-flow.md` (ADR 0021). The decision path is:

1. Run the `cba-searching` prior-art scan (installed skill — `docs/agents/installed-skills.md`) to check whether the wider open-source world already ships the capability well.
2. Based on the scan verdict, accept (`ready-for-agent`), park (`awaiting-corroboration`), or reject (`wontfix`) per the accept/park/reject semantics in `skill-request-flow.md`.

Do not re-derive the internals of that flow here — delegate to it.

## Strong agent brief (ready-for-agent)

Post a comment structured as:

```markdown
### Goal
<One sentence.>

### Read first
- <file or doc> — <why>
- …

### Decided (do not re-litigate)
- <decision already made>
- …

### Must do
- <concrete deliverable>
- …

### Discrepancies to resolve
- <anything ambiguous the agent must surface before implementing, not silently decide>
```

Model the quality of the briefs on issues #292 and #293 in this repo: goal is one sentence; read-first cites specific file paths; decided locks in choices so the agent doesn't re-open them; must-do maps directly to acceptance criteria; discrepancies names anything where the spec leaves the agent room to go wrong silently.

Omit sections that are empty (e.g. no discrepancies → omit that section).

## Quick state override

If the maintainer says "move #42 to ready-for-agent", trust them and apply the label directly. Confirm what you are about to do (label changes, comment, close), then act. Skip deep context-gathering. If moving to `ready-for-agent` without a full triage session, ask whether they want to write an agent brief.

## Resuming a previous session

If prior triage comments exist on the issue, read them before continuing. Don't re-ask resolved questions.
