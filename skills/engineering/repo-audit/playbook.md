# Repo Audit — Leverage-Hunt Catalog

What to look for under each leverage category in Stage 2. Load this when running the hunt.

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

**Vocabulary to use (`codebase-design`):** module, interface, depth, seam, adapter, leverage, locality. Every finding names the module(s) and describes the deepening opportunity in these terms.

**Security as an optional input.** For repos handling auth, user data, or external APIs, layer a security scan over the architecture walk: data-flow boundaries, auth surfaces, token/secret handling, CI workflow permissions. High-severity findings (auth bypass, secret exposure, privilege escalation) are filed as standalone `ready-for-agent` issues and elevate the epic that owns that surface.

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

**Docs as an optional input.** Where docs appear stale or sparse, surface mismatches between documented and actual behaviour as missing-capability findings (the capability to trust the docs is missing). Apply `doc-it`'s posture: report-only on ADRs and CONTEXT.md, apply changes to reference docs.

---

## Altitude bar reference

| Rating | Criterion | Action |
|--------|-----------|--------|
| **File** | Meaningful impact; justifies its own issue or epic | File or fold into an existing issue/epic |
| **Batch** | Low individual impact; worth tracking collectively | Collect into a single "minor cleanups" issue |
| **Drop** | Trivial; not worth the cost of tracking | Drop — do not file |

Err toward Drop over Batch, and Batch over filing trivia as standalone issues. One tight "minor cleanups" issue is better than five low-signal tickets.
