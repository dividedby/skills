# Census cells are thin pointers; deep context lives on the linked issue

Prose-in-cells became the main token driver of the roadmap body. A single Notes
cell reached **1,500–3,000+ chars** of implementation history (moodreader), so the
census stopped being **scannable at a glance** — the Status column you read to pick
the next task was buried under paragraphs of journal. [ADR
0023](./0023-closed-waves-collapse-then-prune-census-is-an-execution-view.md)
already declares GitHub/git the archive and the census an execution view, yet the
cells drifted into an **implementation journal** anyway: the row stopped being an
index into the work and started trying to *be* the work's record.

## Decision

Census cells are **thin pointers** into the linked issue, not a place to keep the
narrative.

1. **Cells are a single line.** Notes/Status cells are one line (a ~120-char cap);
   **Status is a single token** from the Legend vocabulary. Deep context lives on
   the **linked issue #N**, not in the cell — the cell points, the issue holds.
2. **Mechanically enforced by `roadmap-guard`** (issue #227). An in-branch edit that
   produces an over-cap or multi-line cell is **denied** at edit time. Malformed
   input **fails open** (allows), preserving the guard's existing contract: the
   guard tightens the well-formed path and never blocks on input it cannot parse.
3. **The one-time migration is non-lossy.** Before trimming, the migration relocates
   any **orphan narrative** — cell text not already on the linked issue — to that
   issue as a comment, so the thinning loses no context (per the ADR 0022 amendment
   and issue #230). Trimming follows relocation; it never precedes it.

## Why this is consistent with 0023 / 0022

- **0023 (census is an execution view, GitHub/git is the archive).** The
  implementation journal **belonged on the issues, not the cells** — 0023 already
  named GitHub the archive. This ADR **completes 0023's execution-view intent** by
  closing the one place the journal still leaked back in: the Notes cell. The cell
  becomes the index 0023 always implied it was.
- **0022 (reconcile auto-applies on a green gate).** The cap is a **Tier-1
  mechanical rule** — a deterministic, no-judgment check the guard enforces in
  branch — so cap enforcement rides the same green-gate machinery as every other
  Tier-1 edit. (The one-time *migration* that first brings legacy cells under cap is
  the human-reviewed carve-out of the 0022 amendment, because relocating narrative
  faithfully is the judgment a green gate can't make.)

## Rejected alternatives

- **Structured-token-only Notes (no free text).** Too rigid: a one-line pointer
  often needs a few words of human context ("blocked on #N's review", "spike, not
  scoped") that no fixed token vocabulary captures. The ~120-char single-line cap
  keeps cells scannable **without** forbidding free text. Rejected.
- **Prune narrative only on Done rows, leaving open rows unbounded.** An **active
  Wave can still spike** — moodreader's exact failure mode was open in-flight rows
  accreting 3,000-char journals, not closed ones. Capping only Done rows leaves the
  live backlog (the part a human actually reads) unbounded. Rejected in favor of a
  cap on every cell.
