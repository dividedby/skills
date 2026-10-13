# Repo Audit — Leverage-Hunt Catalog

Per-lens signal guide. Seats load their own section; Stage 1 loads `Stage 1 evidence pack`.

## Stage 1 evidence pack

Built once in the main session and handed to every seat as digests (counts plus top items), never raw dumps.

**Deterministic detectors.** Where Stage 1 shows a JS/TS stack (`package.json`/`tsconfig`) or Python (`pyproject`/`requirements`), run mechanical detectors; they beat eyeballing at the mechanical layer. Pick by concern, using the stack's current tool of record (representative today): dead exports/files/deps → `knip`/`ts-prune` (JS/TS), `vulture` (Python); orphan modules and cycles → `madge`/`dependency-cruiser` (JS/TS); copy-paste duplication → `jscpd`. Run ephemerally (`npx <tool>`, `uvx`/`pipx run <tool>`) so the host repo gains no dependency and there is no install step. If a runner is absent, skip and log it; never block the audit. Raw output is triage input, not report content: framework entrypoints and CLI mains read as "unused". Detectors do the mechanical 80%, leaving the LLM the semantic 20% — "this *looks* like it should call X but doesn't", conceptual duplication, capability gaps.

**Hotspot ranking.** Rank files by churn over a recent window (commit counts per path from `git log`, e.g. 12 months), excluding lockfiles, generated and vendored paths. Multiply by a cheap complexity proxy available without an install (line count, or a figure a detector already produced); if none is cheap, rank by churn alone and say so. Keep the top ~15 as attention hints, not verdicts — evidence for churn × complexity is thin. Upstream `improve-codebase-architecture` scopes by git-log hot spots; defer to it for the idea.

```
# illustrative only
git log --since="12 months ago" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -15
```

---

## Delete / lean

**Signals:**
- Dead code: functions, modules, or files with no callers (check `git log` recency, not just static analysis).
- Feature flags that are fully rolled out or permanently off — the flag and both branches can be deleted.
- Orphaned workflows: CI jobs that no longer have a trigger, or that duplicate what another job already does.
- Unused dependencies: packages imported nowhere, or used only in one narrow call that could be inlined.
- Abstraction layers that are pure pass-throughs — no logic, just delegation. Apply the deletion test: if deleting it concentrates complexity, it was earning its keep; if complexity just moves to callers, it was overhead.
- Docs that describe features or behaviour no longer present in the code.

**Optional: staleness scan.** Where the repo appears large or long-lived, scan for stale toolchain pins, EOL runtimes, and outdated CI matrix entries. Feed results to the delete/lean category — a stale dep or pin is a deletion or upgrade candidate.

**Optional: prior-art check.** Where the repo may be reimplementing something that already exists (a client library, a CLI tool, a SaaS API), note it. A deletion finding is stronger if a maintained alternative exists.

---

## Performance

**Signals:**
- N+1 query patterns: a loop that calls a database or external API per iteration instead of batching.
- Synchronous work on a hot path that could be deferred or parallelised.
- Large allocations or copies where streaming or mutation would serve.
- Missing caching on repeated, expensive, pure computations.
- Heavy dependencies pulled into critical paths (startup, hot import, render).

**Note:** flag where measurement is needed before optimising. A pattern that looks expensive may not be the actual bottleneck; surface the hypothesis, not a premature fix.

---

## Architectural deepening

**Explore walk (from `improve-codebase-architecture`).**  
Move through the codebase organically, noting where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their **seams**?
- Which parts are untested, or hard to test through their current interface?

Apply the **deletion test** to anything suspect: would deleting it concentrate complexity in one place, or just scatter it to callers? "Scatters to callers" means it was a pass-through — prime deletion candidate. "Concentrates" means it was earning its keep.

**Vocabulary to use:** module, interface, depth, seam, adapter, leverage, locality. Every finding names the module(s) and describes the deepening opportunity in these terms.

**Security as an optional input.** For repos handling auth, user data, or external APIs, layer a security scan over the architecture walk: data-flow boundaries, auth surfaces, token/secret handling, CI workflow permissions. High-severity findings (auth bypass, secret exposure, privilege escalation) are high-priority leverage findings — mark them top-priority and expedite them through Stage 3 (reconcile, epics, approval gate) like all other findings; they elevate the epic that owns that surface but are not filed standalone before Stage 3.

**Test coverage as an optional input.** Where coverage appears thin, map which architectural seams have no test surface through them. Feed into the deepening findings — an untestable seam is a shallowness signal, not just a coverage gap.

---

## Missing features / capabilities

**Signals:**
- User journeys documented in the README or CLAUDE.md that have no implementation path.
- Error states that are caught but not handled (bare `catch` that swallows, empty error UI).
- Configuration surfaces that exist in docs but have no validation or error messaging.
- Observability gaps: no logging, no metrics, no alerting on failure modes that matter.
- Agent/automation capabilities described as goals but not yet wired (common in this repo class).

**Frontend/UX as an optional input.** For repos with meaningful UI, scan for: visual hierarchy problems, missing empty states, inaccessible patterns (contrast, keyboard nav, ARIA semantics), and onboarding friction. Feed findings into this category.

**Docs as an optional input.** Where docs appear stale or sparse, surface mismatches between documented and actual behaviour as missing-capability findings (the capability to trust the docs is missing). Posture: report-only on ADRs and CONTEXT.md; reference docs may be changed directly.

---

## Convention & backlog

**Signals (Convention & Backlog Keeper lens):**
- Convention drift: naming, structure, or patterns that diverge from the documented conventions (ADRs, CLAUDE.md, CODING_STANDARDS.md, label vocabulary, changelog format) without a recorded decision behind the divergence.
- Structural inconsistencies across sibling skills or modules — fields missing in some but present in others, register entries out of sync with the actual directory.
- Open issues in the Stage 1 backlog that duplicate each other.
- Backlog entries already implemented but not closed — a gap between `git log` and open issues.
- ADRs with `Proposed` status where the decision has already been made in code.

**Note:** this lens is blind to the other seats, so it must not claim to know what they will find; synthesis detects supersession and obsolescence across findings. It is cross-cutting and generates no epics of its own; its value is enriching the Stage 3 reconcile step through the open-issue field.
