---
name: idea-intake
description: >
  Where a new idea or issue lands in any repo. Use when the user says "file an idea" or "file an issue" (unqualified), or asks to log, park or capture an idea: appends an enriched row (the raw idea, ambient context and links, one sentence of why) to the top of `## Ideas` in the repo's Idea Inbox issue (label `idea-inbox`, one per repo) without grilling or scoping it. A "file a tracked issue" request or a plainly-scoped bug skips the Inbox and files a `needs-triage` issue. Uses `gh api` REST routes, never GraphQL.
---

# Idea Intake

Capture only. Scoping, dedup and promotion happen later, at drain.

Defers:

- `docs/agents/idea-inbox.md` in the target repo, when present. It is the capture and drain protocol and **wins over this skill** where they differ. Read it first.

## Route the request

- **"file an idea"**, or an unqualified **"file an issue"** → capture to the Idea Inbox (below).
- **"file a _tracked_ issue"**, or a **plainly-scoped bug** → skip the Inbox. File a `needs-triage` issue directly.
- Unsure which → treat it as unqualified and capture it; capturing loses nothing.

## Resolve the repo

Parse `owner/repo` from `git remote get-url origin` only (`gh repo view` is GraphQL). Handle both forms, `https://github.com/owner/repo(.git)` and `git@github.com:owner/repo(.git)`, and strip a trailing `.git`. Never assume a repo name or issue number.

## Capture to the Inbox

1. Find the Inbox: `gh api 'repos/{owner}/{repo}/issues?labels=idea-inbox&state=open'`. Use the one open issue; if none, say so and ask before creating one.
2. Fetch the current body, then write a new body with one unchecked item at the **top** of `## Ideas` (newest on top). Leave everything else untouched, including the hidden breadcrumb comment on the first line.
3. Write the row from what is known now:
   - The raw idea, in the user's words.
   - Ambient context: the source file, issue, PR or link that prompted it.
   - One sentence on why it matters.
4. Update with `gh api -X PATCH repos/{owner}/{repo}/issues/<n> -F body=@<file>`. Write the body file with the Write tool, not a heredoc.
5. Confirm with the issue link and the row added.

Don't grill, expand or scope the idea. Don't add operating instructions to the issue body; it is human-facing.

## File a tracked issue

`gh api -X POST repos/{owner}/{repo}/issues -f title=... -F body=@<file> -f 'labels[]=needs-triage'`. Add category and size labels only if the repo's `docs/agents/triage-labels.md` (or `labels.md`) calls for them.

## REST only

GraphQL isn't available from Claude Code sessions. Use `gh api` REST routes, not `gh issue`.
