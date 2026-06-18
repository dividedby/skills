---
name: triage
description: Triage issues through a state machine driven by the dividedby label vocabulary. Use when the maintainer wants to see what needs attention, triage a specific issue, move an issue to a new state, or manage issue workflow on this repo's GitHub tracker.
---

# Triage

Move issues on the project issue tracker through a small state machine. Every triaged issue carries exactly one state label, one category label, and one size label.

## Label vocabulary

Full label definitions live in `docs/agents/labels.md`. The working set:

**State** (apply exactly one): `needs-triage` / `ready-for-agent` / `ready-for-human` / `blocked` / `wontfix`

**Category** (apply exactly one): `bug` / `enhancement` / `chore` / `epic`

**Size** (apply exactly one): `size:S` / `size:M` / `size:L` / `size:XL`

Normal flow: unlabelled → `needs-triage` → one of `ready-for-agent`, `ready-for-human`, `blocked`, or `wontfix`. The maintainer can override at any time — flag transitions that look unusual and confirm before proceeding.

**Conflicting state labels.** If an issue carries two or more state labels, surface the conflict and ask which one to keep before doing anything else. Never silently pick one.

## Branches

The maintainer invokes `/triage` in natural language. Three branches:

- "Show me what needs attention" → **Show attention queue**
- "Triage #N" or "Let's look at #N" → **Triage a specific issue**
- "Move #N to ready-for-agent" → **Quick state override**

## Show attention queue

Query the tracker and present two buckets, oldest first:

1. **Unlabelled** — no state or category label (never triaged).
2. **`needs-triage`** — evaluation in progress.

Show counts and a one-line summary per issue. Let the maintainer pick.

```bash
gh issue list --state open --label "needs-triage" --json number,title,createdAt \
  --jq 'sort_by(.createdAt) | .[] | "[#\(.number)] \(.title)"'
```

## Triage a specific issue

1. **Gather context.** Read the full issue — body, comments, labels, dates. Parse any prior triage notes to avoid re-asking resolved questions. Explore the codebase via domain glossary and ADRs in the area.

2. **Intake routing.** If the issue describes something that belongs in the capture/drain path, reference `docs/agents/idea-inbox.md`. Do not re-file Inbox ideas as tracked issues.

3. **Skill-request path.** If the issue carries `skill-request`, follow **Skill-request triage** below instead of the generic path.

4. **Bug reproduction step.** If the category is `bug`, capture a minimal reproduction before proceeding: the exact steps, observed behaviour, and expected behaviour. Record this in a comment on the issue if not already present. An agent cannot reliably fix a bug it cannot reproduce.

5. **Recommend.** State your category, state, and size recommendation with reasoning. Wait for direction.

6. **Apply the outcome** and label:

   ```bash
   gh issue edit <number> --add-label "<state>,<category>,<size>" --remove-label "<old-state>"
   ```

   - `ready-for-agent` → post an agent brief (see **Agent brief** below) and apply labels.
   - `ready-for-human` → post a comment explaining why it cannot be delegated (judgment calls, external access, design decisions, manual testing) and apply labels.
   - `blocked` → post a comment stating what is blocking and on what (issue number, external dependency, or open decision) and apply labels.
   - `wontfix` → post a rationale comment, apply labels, and file a durable rejection entry (see **Rejection KB** below).
   - `needs-triage` → apply the label. Optional comment if there is partial progress.

## Skill-request triage

When an issue carries `skill-request`:

1. Run `/cba-searching` (installed skill — `docs/agents/installed-skills.md`) to check whether the wider open-source world already ships this capability well. Feed the issue description as the target concept.
2. Route on the scan verdict per `docs/design/skill-request-flow.md` (ADR 0021): accept (`ready-for-agent`), park (`awaiting-corroboration`), or reject (`wontfix`).

Do not re-derive the accept/park/reject semantics here — delegate to that flow.

## Agent brief

Post a comment on the issue structured as:

```markdown
### Goal
<One sentence.>

### Read first
- <file or doc> — <why>

### Decided (do not re-litigate)
- <decision already made>

### Must do
- <concrete deliverable>

### Discrepancies to resolve
- <anything ambiguous the agent must surface before implementing>
```

**Interface-not-procedure.** Briefs must survive code churn: name behaviours, interfaces, and types — not file paths or line numbers. A brief that says "edit `lib/foo.py` line 42" is fragile; one that says "the `FooProcessor` interface must reject empty inputs" is durable.

**AI-authored briefs** must include an `> AI-generated brief — review before handing to agent` blockquote at the top of the comment.

Omit sections that are empty (no discrepancies → omit that section). Model goal/read-first/must-do quality on issues #292 and #293 in this repo.

## Rejection KB

When closing an issue as `wontfix`, file a durable rationale entry in `.out-of-scope/` at the repo root — a short Markdown file named after the rejected concept (e.g. `.out-of-scope/live-reload-hook.md`). This is the single source of truth for why a class of work was rejected, so future requests in the same space get a grounded answer without re-litigating the decision.

Each entry states: what was rejected, why (the concrete reason, not "out of scope"), and the bar to revisit. Link the originating issue under `## Prior requests`.

## Quick state override

If the maintainer says "move #N to ready-for-agent", trust them and apply the label directly. Confirm what you are about to do (label changes, comment, close), then act. Skip deep context-gathering. If moving to `ready-for-agent` without a full triage session, ask whether they want an agent brief.

## Resuming a session

If prior triage comments exist on the issue, read them before continuing. Do not re-ask resolved questions.
