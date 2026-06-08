# The apply-agent-research harness prompt is consumer-portable via env, not vendored per-repo

[ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)
moved the proposal-loop **prompts** onto the fetch-fresh harness rail so a fix
reaches every loop on its next run. But the `apply-agent-research` prompt that
landed in `harness/prompts/apply-agent-research.md` was the **skills-repo's own
instance**: it hardcoded the in-tree skill path
(`skills/meta/apply-agent-research/…/lib/cli.py`), asserted "the skills repo is
public and has no private markers to pass," and carried none of a Consumer's
cross-repo wiring (`skill-request`/`skill-promotion`, `SKILLS_TRACKER_TOKEN`,
`$PRIVATE_MARKERS`). Yet `docs/onboarding/consumer-setup.md` and
`proposal-loop-harness.md` tell a Consumer to `cat` exactly that file as its
system prompt. A Consumer obeying the docs got a **broken** run (wrong skill
path) that was also **leak-unsafe** (no marker pass on a public tracker). See
[#144](https://github.com/dividedby/skills/issues/144).

## Decision

The single `harness/prompts/apply-agent-research.md` is **parametrized by the
environment the stub exports**, and serves both the skills-repo (tracker host)
and every downstream Consumer from one source:

| Env var | Host (skills-repo) | Consumer | Prompt use |
|---|---|---|---|
| `MIRROR_DIR` | set by stub | mirror clone or native `knowledge/` | KB read |
| `SKILL_DIR` | `skills/meta/apply-agent-research` | `~/.claude/skills/apply-agent-research` | `python3 $SKILL_DIR/lib/cli.py {gate,file,comment}` |
| `SKILLS_SRC` | checkout root | fresh `dividedby/skills` clone root | published-skill catalog (already-do-this + audit) |
| `PRIVATE_MARKERS` | empty | the repo's private markers | expanded to `--marker …` on every guarded `file`/`comment` |
| `SKILLS_TRACKER_TOKEN` | unset | set | **role discriminator** + cross-repo GH auth |

**Role is derived from `$SKILLS_TRACKER_TOKEN` presence, not a separate flag.**
Unset → **host mode**: drain `skill-request` issues locally, propose
skills-on-general-merit, no cross-repo writes. Set → **consumer mode**: file/+1
`skill-request`/`skill-promotion` to `dividedby/skills`, and run the supply-side
`skill-audit`/promotion **only if local non-published skills exist**. The host
writes to itself with the default `GITHUB_TOKEN` and never sets the cross-repo
PAT, so token presence is an honest discriminator that cannot drift out of sync
with the thing it gates (a `MODE=consumer` flag without a token would 403).

The skill's `cli.py` already accepts `--repo` and a repeatable `--marker`, so
this is a **prompt + stub + docs** change with no CLI change.

## Why ride the fetch-fresh rail at all

ADR 0014's stated reason for putting prompts on the rail is that a prompt and the
`publish` CLI share the `<output>`/`<body>` contract and must version in
lockstep. **That rationale does not apply to this prompt** — `apply-agent-research`
files through the skill's own guarded `cli.py` and never touches the publish
seam. This prompt rides the rail for a **different** reason: parametrized
portability preserves 0014's "one fix reaches every loop" property for the
`apply-agent-research` loop too. Recording this so a future reader does not
"correct" the prompt back toward the publish-lockstep framing that does not fit
it.

## Consequences

- One prompt, two roles. The drift between a skills-repo instance and a
  consumer-correct instance (which is what produced #144) cannot recur — there is
  one artifact.
- The stub ↔ harness interface grows by the env contract above. Per ADR 0014 a
  breaking change to it is a **manual rollout** across the ~3 owned repos; the
  contract is documented in
  [`docs/onboarding/proposal-loop-harness.md`](../onboarding/proposal-loop-harness.md)
  and `consumer-setup.md`.
- A private Consumer's leak safety now rests on the stub exporting
  `PRIVATE_MARKERS`; the prompt expands it onto every guarded `file`/`comment`.
  An empty value (the host case, and any misconfigured private consumer) falls
  back to the guard's structural checks only — onboarding calls this out.

## Rejected alternatives

- **A separate `apply-agent-research.consumer.md` variant.** Simpler per file, but
  reintroduces two prompts to keep in sync — precisely the drift class ADR 0014
  exists to delete.
- **Leave the prompt skills-repo-internal; have Consumers vendor their own.**
  Gives up 0014's single-source property for this loop and leaves the onboarding
  docs lying about what a Consumer `cat`s. Rejected for the same reason 0014
  de-vendored the harness in the first place.
