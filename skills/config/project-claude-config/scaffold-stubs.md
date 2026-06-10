# Scaffold posture (additive)

Applied to whatever the detect pass found **missing or trivial**. The deliverable is an **earn-the-line stub**: the smallest config that captures what's known, built repo-first, presented with a "here's what I inferred — confirm/correct" summary. Stubs plus a correction pass beat a long interrogation; don't aim for completeness.

## What a stub is

- Built from **detected facts first** — commands from manifests, structure from the tree, triggers from the catalog. Interview answers fill only the gaps Explore couldn't (intent, goals, invisible conventions, what to enforce) — see SKILL.md's interview gate and stub bar.
- **Every line already passes its filter** ([CATALOG.md](CATALOG.md): annoyance filter for hooks, earn-the-line filter for instructions). A stub is small because the bar is high, not because it's unfinished.
- Marks genuine unknowns as explicit open questions in the confirm/correct summary — never as placeholder prose in the file.

## Harness stub

Propose only [CATALOG.md](CATALOG.md) Harness entries whose trigger matched, each with what it does, why it earns its place, and its annoyance cost.

## Instruction-file stub

CLAUDE.md is an **index, not a manual**. Scaffold only lines matching a [CATALOG.md](CATALOG.md) Instructions line class whose trigger holds, and nothing from its anti-catalog — in particular, no instruction a just-proposed hook enforces (the harness concern was settled first so this pass can omit those lines).

For a domain glossary (`CONTEXT.md`) or ADRs (`docs/adr/`), point at `/grill-with-docs` — this skill intentionally does not scaffold those.

## Output

Proposed file contents (or `settings.json` additions) with a one-line why per addition, the rejected-entries list, and the inferred-facts confirm/correct summary. Feeds the single batch approval in SKILL.md's final step.
