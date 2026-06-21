# Adversarial spec critique — not a published skill

**Rejected as:** a published, distributable skill in this repo.

**Why:** the capability's whole value is a *fresh, isolated, skeptical context that sees only the spec*. That property is what a **subagent** provides natively; a skill is instructions loaded into the current context and yields no naive critic unless it spawns a subagent anyway (and pollutes the author's context, defeating "naive"). Prior-art scan (`cba-searching`, 2026-06-20) confirms the shape: no standalone tool ships this well — the pattern is *always* embedded as an agent/config step in a harness, never a distributed package. So the right home is global agent-meta (a `spec-critic` subagent + a one-line spec-review-gate convention), not a skill.

**Built instead as:** `dividedby/claude-config#63` (spec-critic subagent + convention).

**Bar to revisit (build it as a skill here):** evidence that the critique workflow needs to be *distributed to the wider ecosystem* as a reusable, invokable artifact — i.e. demand from consumers outside this maintainer's own harness — rather than wired once into the global config.

## Prior requests
- `dividedby/skills#362`
