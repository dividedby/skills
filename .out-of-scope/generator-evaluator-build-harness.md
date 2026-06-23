# Generator-Evaluator Build Harness as a Standalone Skill

This repo will **not** publish a separate engineering skill for the
"generator-evaluator harness" pattern (a generator agent implements, a separate
evaluator agent grades against weighted criteria, looping until a score passes a
threshold). The discipline is real and valued — the pattern is just well-established
prior art, and the genuinely additive part folds into the existing
`autonomous-loop` skill rather than a new published surface.

## Why this is out of scope

**The mechanism is saturated prior art, not an unshipped capability.** The
generator→evaluator loop graded on criteria is textbook:

- **Reflexion** (`noahshinn/reflexion`, ~3.2k★, NeurIPS 2023) — the canonical
  verbal actor-critic self-improvement loop.
- **Self-Refine** and the broader actor-critic / generator-discriminator family.
- The evaluator half ships as mature tooling: `confident-ai/deepeval` (~16.4k★)
  and a long tail of LLM-as-judge evaluation frameworks.
- The build-loop half ships in autonomous coding agents (`cline`, ~63k★).

A skill restating the loop would be re-documenting well-trodden ground.

**The additive residual is discipline, and it belongs in `autonomous-loop`.** The
genuinely useful bits the request names — criteria design for non-binary/subjective
quality, evaluator calibration via few-shot examples, generator↔evaluator "sprint
contracts," and the "when does the ~20× harness earn its cost vs. a solo loop"
heuristic — are *discipline*, not a new capability. `autonomous-loop`
(`skills/engineering/autonomous-loop/`) already owns loop mechanics, feedback
gates, stop conditions, and HITL→AFK graduation; its feedback gate is currently
binary (tests pass or halt). The non-binary-quality evaluator split is the natural
extension of that gate, not a fourth place to restate loop discipline.

This mirrors the #100 precedent (tracer-bullet build skill): a real discipline
already delivered by an existing surface; a standalone skill re-states it. The
difference here is favorable — the fold target (`autonomous-loop`) is in-repo and
ours to edit, unlike #100's upstream `tdd`.

## If this is ever reconsidered

Two bars, either one:

- A demonstrated gap where folding the evaluator-split discipline into
  `autonomous-loop` proves insufficient — real runs where authors need
  generator-evaluator guidance and can't find it under the loop skill.
- The pattern stops being adequately covered by external prior art (unlikely while
  Reflexion/Self-Refine/deepeval-class tooling remains the de facto reference).

The likely first action if revisited is a **non-binary-quality evaluator-gate
section in `autonomous-loop`**, not a new published skill.

## Prior requests

- #422 — "New engineering skill: generator-evaluator harness for autonomous
  building" (`source:agent-research`, `skill-request`; source:
  anthropic/artifacts/generator-evaluator-harness). Rejected via the skill-request
  flow (ADR 0021) after a `/cba-searching` prior-art scan.
- #100 — sibling precedent (tracer-bullet build skill), folded not published.
