# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body-file <file>` (write the body to a file first — heredocs clobber hook stdin).
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Label conventions

When filing or triaging a new issue, apply:
- A **state** label (`needs-triage` if unclear, or `ready-for-agent`/`ready-for-human` if the scope is known)
- A **category** label (`bug`, `enhancement`, `chore`, or `epic`)
- A **size** label (`size:S`, `size:M`, `size:L`, or `size:XL`) as a best-effort estimate

See `docs/agents/labels.md` for the full label reference.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
