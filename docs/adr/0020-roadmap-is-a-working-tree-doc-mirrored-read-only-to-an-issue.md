# The Roadmap is a working-tree doc; a durable issue is only a CI-rendered read-only mirror

The maintainer wanted the execution roadmap to "live as a durable issue in all
repos" — glanceable from the GitHub UI without a clone or a session. But the
roadmap's authority comes from **file-based integrity** a GitHub issue cannot
host: the PreToolUse commit guard forces an issue-referencing commit to touch the
doc, the SessionStart drift nudge diffs the doc against `gh`, and `/roadmap`
(now `/roadmap`) edits the doc for `git diff` review. A single issue body has no
commit, no diff-review, no guard, and concurrent edits clobber instead of merge.

## Decision

The **working-tree markdown doc stays the source of record.** A durable GitHub
issue is at most a **read-only mirror**: a machine-owned issue whose body is
**CI-rendered from the doc on push** (commit-if-changed), giving the
glance-from-the-web property without moving authority off the file. The mirror is
refreshed by a small deterministic CI job, **never by the skill** — so it sits
outside the skill's write-posture rules.

This is **not** a body-rewrite in the sense [ADR 0017](./0017-roadmap-write-posture.md)
forbids: 0017 protects *human-authored* issue bodies from the skill. The mirror
issue is a machine-owned artifact whose body *is* the render target; CI owns it.

## Rejected alternatives

- **Issue (or GitHub Project) as the authoritative roadmap.** Discards the
  hook+reconcile integrity model for none, and GitHub Projects is paid. Rejected.
- **Self-hosting a PM tool (e.g. Plane).** Replaces the markdown+`gh` substrate
  entirely — the opposite of roll-our-own-minimal. Out of scope; a separate infra
  spike if ever pursued.
- **Mirror refreshed by the `roadmap` skill.** Tangles the mirror into ADR 0017's
  posture and the loop-suppression invariant. The deterministic CI job is simpler
  and matches the existing Knowledge-mirror pattern.
