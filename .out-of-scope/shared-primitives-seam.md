# Shared-primitives seam ("our own lighter Sandcastle") / unifying the two fetch rails

**Deferred (not now):** Building a shared-library seam to deduplicate cross-rail
primitives, and/or unifying the two fetch-fresh rails (harness `git clone` +
skill `cp -R`) into one mechanism.

**Why deferred:** The only cross-rail code overlap today is `repair_json`, kept
byte-identical harness↔skill behind a CI drift guard (ADR 0026) because the skill
must ship self-contained (ADR 0008) with no shared-lib mechanism spanning the two
fetch-fresh rails (ADR 0014). A library solves a one-function problem we don't
have at scale. Matt Pocock's Sandcastle gets one-copy because it's an npm package
both halves `import`; we deliberately run a no-package-manager fetch-fresh-Python
model so the leak guard travels whole, and Sandcastle's framework weight
(sandbox/providers/session-resume) solves problems we don't have. The real
cross-repo divergence surface is the vendored workflow *envelope* (#325 epic, #359
rollup) — irreducible by a shared library; that's #366's reusable-workflows lever,
not this one.

**Bar to revisit:** Either (a) shared-primitive overlap grows to **≥3 functions
across ≥3 repos with real drift incidents**, or (b) consumer count makes the
two-step fetch compound into the "fix twice by hand" pattern (#119 / #211) that
originally justified the harness rail. If revisited, the merit version is
**unifying the fetch rails for onboarding ergonomics** — not a TypeScript
framework.

## Prior requests

- Idea Inbox (#91) — "Evaluate a shared-primitives seam / unify the two fetch rails"
- Refs: #369, #325, #359, #366; ADR 0008 / 0014 / 0024 / 0025 / 0026
