# `/council` panel in the scheduled architecture-review loop

**Rejected (not now):** Wiring a multi-agent `/council` second-opinion panel into the scheduled `improve-codebase-architecture` proposal loop (headless `claude -p`, 3×/week).

**Why rejected:** Three independent reasons, any one sufficient (spike #495):

- **Cost.** A 5-seat panel runs ~$7–12/run vs the loop's current ~$0.50–1.00 (**7–12×**), ≈ $90–150/mo at 3×/week. It contradicts the deliberate **sonnet pin** (`improve-codebase-architecture-reusable.yml:151`, per the #161 verdict that sonnet ≥ opus on proposal-loop tasks) by adding opus seats, and trips the **`--max-budget-usd 3.00` backstop** (`:152`) mid-run — forcing a 3–5× backstop raise that destroys its "never trips a healthy run" property.
- **Wrong host.** `/council` drives the in-session `Workflow` orchestration tool, which repo doctrine routes to **interactive** sessions, not cron (`skills/engineering/autonomous-loop/FIREWALL.md:42`); the loop's `--allowedTools` allowlist (`:153`) carries no orchestration tool, and headless `Workflow` availability is itself unconfirmed.
- **Wrong problem.** The loop's quality failure mode is *over-proposing filler* (a filtering problem); a panel generates more candidates, it does not sharpen the ruthless-cut discipline already encoded in the three-lens structure.

**The alternative (do this instead):** Invoke `/council` **interactively at triage** on a filed `source:architecture-review` proposal when it is high-stakes enough to want a panel — pay-per-use, zero unattended spend, no loop change. Consistent with #496's interactive/scheduled cost split.

**Bar to revisit:** Either (a) the built-in `Workflow` tool is confirmed available and cost-bounded inside headless `claude -p` **and** a panel demonstrably raises proposal *precision* (not just volume) on a measured sample, or (b) the loop's budget model changes such that a 7–12× per-run multiplier no longer breaks the sonnet-pin / backstop invariants.

## Prior requests

- Idea Inbox (#91) → spike #495 (ratified NO, 2026-06-29)
- Refs: #492 (`/council` skill), #496 (Workflow-leverage survey — interactive/scheduled cost split); ADR 0019 (budget/cap + cadence), ADR 0014 (fetched-fresh envelope)
