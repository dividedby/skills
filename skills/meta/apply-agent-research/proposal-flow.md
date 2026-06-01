# Proposal flow: dedup keys, the gate, and the leak guard

The capability is in [SKILL.md](SKILL.md). This file is the mechanical flow that
makes the "at most one, leak-safe, deduplicated" guarantees hold *without relying
on prompt discipline*. Two pure decisions enforce them, shipped with this skill at
`lib/` and invoked by file path: `python3 <skill-dir>/lib/cli.py` (not `-m` — the
skill folder is not an importable module; the script puts its own dir on the path).
`<skill-dir>` is wherever this skill is installed; the host's workflow substitutes
the concrete path.

## Dedup keys

Each candidate carries a stable **`dedup_key`** — a short kebab-case slug naming
the proposal's *target and intent*, not its prose (e.g. `claude-md-instruction-budget`,
`skill-request-context-forking`). The same gap on a later run must produce the same
key, so a re-proposal is caught.

Every filed issue embeds its key as an HTML comment so future runs can recover it:

```
<!-- dedup-key: claude-md-instruction-budget -->
```

Before proposing, gather the keys already spoken for:

- **Open** `source:agent-research` issues — never re-file an open proposal.
- **Recently closed** ones — and treat any closed as **`wontfix`** as *durable
  suppression*: that key is settled, do not raise it again.

Grep the `dedup-key:` markers out of those issue bodies to build the open-keys
list passed to the gate.

**Read the reasoning, don't just match keys.** Exact-key suppression catches a
verbatim re-file, but the maintainer's *why* on a closed `wontfix` is the durable
signal — read the **bodies and comments** of closed `wontfix` issues and learn the
principle behind each refusal, not just its slug. A candidate that is conceptually
the same refused thing under a *different* key must still be suppressed; and a
stated principle ("we don't add what an installed external skill already covers")
generalizes to candidates the maintainer never saw. When you suppress on reasoning
rather than an exact key match, say so in the `SKIPPED:` line.

## The leak guard (sanitizer)

Run the candidate's final `title + body` through the guard **before** filing.
Supply the host's private markers when the host has any (the public skills repo
has none to pass):

    printf '%s' "$TITLE
    $BODY" | python3 <skill-dir>/lib/cli.py sanitize [--marker <private-name> ...]

Exit `0` + `ALLOW` → safe to file. Exit `1` + `BLOCK: <reason>` → **revise the
body** to remove the structural trigger (a fenced code block, a pasted import, or
a `path/like.this` token), then re-check. Do not bypass it. The guard is
necessary, not sufficient — keep prose generalized regardless of what it catches.

## The one-proposal gate — run once per channel

The cap is **per channel**, not global ([ADR 0011](../../../docs/adr/0011-per-channel-proposal-caps.md)):
each channel (`self-improvement`, `skill-audit`, the skills-repo's
`general-merit`, and the cross-repo `skill-request` / `skill-promotion` file-or-+1
steps) gets its own gate pass over **only that channel's** candidates. The gate is
generic over the candidate set it is handed, so this needs **no code change** —
just invoke it once per channel-group. Feed each pass that channel's candidates
plus the keys already open *in that channel*:

    echo '{"candidates": [{"dedup_key": "...", "priority": 3, "title": "..."}],
           "open_issues": ["<keys already open or wontfix in THIS channel>"],
           "min_priority": 1}' \
      | python3 <skill-dir>/lib/cli.py gate

- `priority` is your integer ranking of the candidates (higher = stronger).
- The gate drops any candidate whose key is already open and any below
  `min_priority`, then picks the highest priority (ties break on the smallest
  key — deterministic).
- Output `{"file": {...}}` → file that one. `{"file": null}` → file nothing in
  this channel; print `SKIPPED: <channel>: <one-line reason>` and move to the
  next channel.

Do **not** merge candidates from different channels into one gate pass — that
reintroduces the cross-channel suppression ADR 0011 removed.

## Filing

Only when the gate returns a candidate **and** the guard allowed it:

    gh issue create \
      --title "<concise title>" \
      --label source:agent-research \
      --body "<body, ending with the dedup-key marker and a Sources line>"

Ensure the `source:agent-research` label exists first (the workflow does this
idempotently). File **one** issue, then stop — no second pass, no commits.
