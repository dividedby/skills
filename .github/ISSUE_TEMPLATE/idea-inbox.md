---
name: 💡 Idea Inbox
about: Living scratchpad for half-formed feature/enhancement ideas. One per repo — keep adding.
title: "💡 Idea Inbox"
labels: idea-inbox
---

## Ideas

Un-actioned ideas first, newest on top. One idea per item — capture the raw idea
**plus the ambient context/links available at file time** (where it came from, the
file/issue/PR that prompted it, a sentence of why). Do **not** grill or scope it
yet — enrich now, drain later.

- [ ] 

---

<details>
<summary>✅ Actioned — Drained ideas move below, checked, linked to the issue/PR they became.</summary>

<!-- - [x] <idea> → #123 -->

</details>

---

<details>
<summary>🤖 Agent operating instructions — read these when pointed at this issue</summary>

You are pointed at this repo's **Idea Inbox**. The unchecked items under `## Ideas`
are raw, enriched, un-actioned ideas.

### Capture (enriched intake)
A new idea I give you goes in as an unchecked item at the TOP of `## Ideas`.
Capture the idea **and the ambient context** available right now — the source
file/issue/PR/link that prompted it and a sentence of why it matters — so a later
drain isn't starting cold. Do **not** grill, expand, or scope it yet; that happens
at drain.

### How to drain
When I ask you to "drain the inbox" (or to drain a specific item), promote the item
end-to-end, adapting to what *this* idea needs:

1. **Dedup / relate** — before acting, review the OPEN issues in this repo. Decide
   whether the idea (a) already exists → note it and move it to the `✅ Actioned`
   section pointing at the existing issue, (b) fits INTO an open issue → comment there
   instead of filing new, or (c) BLOCKS / DEPENDS ON an open issue → record that
   relationship.
2. **Pick only the steps it needs** — do not run the whole pipeline by rote. Choose
   from:
   - `/grill-with-docs` — when the idea is fuzzy or contends with the domain model
     (CONTEXT.md / ADRs); build shared understanding first.
   - `/to-prd` — when it's big enough to warrant a spec before issues.
   - `/to-issues` — to carve it into independently-grabbable tracked work.
   - `/software-design` — when the work spans modules/seams and needs a design pass.
   A small, clear idea may need only `/to-issues`.
3. **Aim for a strong agent brief** — strive to emit a `ready-for-agent` issue that
   clears the strong-agent-brief bar (clear module + acceptance criteria + TDD
   notes; a determinism/offline boundary that stubs external deps; a report-only
   boundary where applicable; explicit out-of-scope + a single named follow-up
   owner). Where full automation isn't safe, **fold in deliberate HITL** —
   step-by-step instructions and QA checkpoints for the human-in-the-loop parts —
   rather than handing an agent unbounded judgment. Split a blocked/human-only idea
   into an AFK-able slice plus a human sibling when that's the cleaner carve.
4. **Move to Actioned** — once the idea becomes an issue/PR (or is resolved as a
   dup/relation), move it into the `✅ Actioned` section, check it, and append `→ #<num>`.

Never delete an idea silently — either drain it or move it with a one-line disposition.
Keep `## Ideas` sorted newest-on-top.
</details>
