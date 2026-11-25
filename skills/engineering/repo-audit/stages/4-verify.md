Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 4 — Verify (main session)

The lens reports are claims. At `standard`, the main session may first hand them
to one `findings-extract (helper)`. It reads the lens reports and writes to a
scratchpad file one structured findings list (id, lens, area, severity, title,
evidence cite, `file:line`) and its proposed duplicate merges. It decides
nothing: the main session reads that file, applies or drops each merge,
re-checks every Blocker and High at its source and sets the verdicts. Before
anything reaches the page:

1. **Route, re-area, then merge, before any re-check.** In this order:
   - **Route notes.** A lens report may hold a `## For other areas` section.
     Route each note into the area that owns it as a finding, verified as
     usual: "also reported by" the noting lens when the owner raised it too,
     otherwise the noting lens's finding in that area.
   - **Re-area.** A finding filed under an area whose check it is not moves to
     the right area and its owning lens's section, with a "re-areaed" line in
     the correction list (a backup-checksum finding filed under `code-quality`
     is `data-integrity`).
   - **Merge duplicates.** Two findings are duplicates when they cite the same
     evidence (a `file:line` or a command output), or name the same subject at
     different lines and one fix resolves both (the `--version` banner is wrong:
     the code lens cites `cli.py:12`, the product lens cites `README.md:40`).
     - Keep one, in the lens that owns the finding's area
       ([`rubric.md`](../rubric.md)). Record the other lenses as "also reported
       by".
     - Keep the highest severity that survives verification.
     - A finding that restates a fleet-standards row is folded into that row.
     - Each merge is a "merged" line in the correction list.
   - **Reuse previous keys.** With a previous run, match each finding to a
     previous one that cites the same file and the same defect, whatever its
     area or check name (`code-quality:null-body` re-raised as
     `security:null-body`), or that breaks the same rule (a fleet row or a
     repo rule's text) or makes the same repo-wide claim with a different
     example path (`tests:untested-risky-path` on another script), and give it
     the previous key. Each reuse is a "key reused" line in the correction
     list. Do this before the diff.
   - **Partial overlap is not a duplicate.** One fix covers only part of the
     other (a code finding on a file's parse cost, an architecture finding on
     that file's rotation): keep both, each naming the other ("overlaps
     `<id>`"), with a "linked" line in the correction list.

2. Re-check every **Blocker** and every **High** finding, every area marked
   **Not ready**, and any finding the plan's "Now" column rests on, at its cited
   source. Read the line; rerun the command. This includes fleet-standards
   fails and failed repo rules at those severities; read the rule's line too.
3. Correct what does not hold: lower the severity, fix the evidence, or drop the
   finding. Keep a list of every correction with the reason. On the page,
   "linked", "re-areaed" and "key reused" lines go under Merged and "added
   (main session)" lines under Corrected (`checked` in `page-extra.json`).
4. Where lenses disagree with each other or with the code (a research claim
   versus what the code does), list it as a "disputed" line in the correction
   list.
5. Context a lens lacked can change a rating (sandboxing, single-user scope,
   data size). Apply it and note it. Add the user-facing text of each fault
   response in the architecture lens's report to the `ops-release` error-copy
   review, which the product lens ran without it.
6. Fill the go-public minutes-saved line. The architecture and product lenses
   run together, so the architecture report leaves it as "from the CI cost
   table": fill it from the product lens's CI cost table as
   [`briefs.md`](../briefs.md#security-privacy-and-data)
   **Minutes saved** says, labelled measured or estimated as that table labels
   it. With no product lens or no figure, write that table's reason instead.
7. A finding the main session sees itself (while verifying, filling the page or
   reading for the scrub) enters with its evidence, goes through **Route, re-area, then
   merge, before any re-check** (merge
   and key reuse) and is re-checked like a lens finding, sits in the area that
   owns it, the verdicts are set again (the "Set each area's verdict" step), and it gets an "added (main session)"
   line in the correction list. A hard-coded home ZIP default seen in the Stage
   6 demo-data read goes back here as a `privacy` finding.
8. Set each area's verdict and the overall verdict from the corrected findings,
   as [`rubric.md`](../rubric.md) directs.

**Done when:** duplicates are merged, every Blocker and High is confirmed or
corrected, every applicable area has a verdict or a Not-assessed reason, and the
correction list (merged, linked, re-areaed, key reused, added, corrected and
disputed lines) is written.
