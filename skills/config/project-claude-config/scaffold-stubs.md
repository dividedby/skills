# Scaffold posture (additive)

Applied to whatever the detect pass found **missing**. The deliverable is an **earn-the-line stub**: the smallest config that captures what's known, built repo-first, presented with a "here's what I inferred — confirm/correct" summary. Stubs plus a correction pass beat a long interrogation; don't aim for completeness.

## What a stub is

- Built from **detected facts first** — commands from manifests, structure from the tree, triggers from the catalog. Interview answers fill only the gaps Explore couldn't (intent, goals, invisible conventions, what to enforce) — see SKILL.md Step 4 for the gate and the stub bar.
- **Every line already passes its filter** ([CATALOG.md](CATALOG.md): annoyance filter for hooks, earn-the-line filter for instructions). A stub is small because the bar is high, not because it's unfinished.
- Marks genuine unknowns as explicit open questions in the confirm/correct summary — never as placeholder prose in the file.

## Harness stub

From [CATALOG.md](CATALOG.md) "Harness": propose only entries whose trigger matched, each with what it does, why it earns its place, and its annoyance cost. List the catalog/anti-catalog entries you deliberately rejected and why. `deny`-only for permissions. Writes route through `update-config` to the shared `settings.json` — never `settings.local.json`, never a nested package file (root-only loading).

## Instruction-file stub

CLAUDE.md is an **index, not a manual**. From [CATALOG.md](CATALOG.md) "Instructions", the typical stub:

- Build / test / lint / run commands — the exact incantations.
- A short architecture map — where the important things live.
- Pointers (by path) to domain docs, conventions, or workflows that live elsewhere; load on demand, don't inline.
- Conventions that **differ** from sensible defaults.

Do NOT scaffold global preferences, generic best practices, anything `/init` would boilerplate, or any instruction a hook now enforces (the harness concern ran first — if a PostToolUse formatter or test-on-Stop hook now exists, omit the matching "remember to..." line).

**Monorepo:** short root file (cross-cutting only — repo layout, how to find the right app, shared tooling) + per-app files (that app's specifics; inherits global + root, so no repetition).

For a domain glossary (`CONTEXT.md`) or ADRs (`docs/adr/`), point at `/grill-with-docs` — this skill intentionally does not scaffold those.

## Output

Proposed file contents (or `settings.json` additions) with a one-line why per addition, the rejected-entries list, and the inferred-facts confirm/correct summary. Feeds the single batch approval in SKILL.md Step 5.
