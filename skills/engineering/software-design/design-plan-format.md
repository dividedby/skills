# Design Plan Format

The Design Plan is the strategic artifact this skill writes to
`docs/design/<feature-name>.md`. It records modules, seams, testing
strategy, invariants, and a one-line **issue index** linking to each
rewritten issue.

The plan does **not** duplicate issue bodies. The issue tracker is
authoritative for those (see [issue-shape.md](issue-shape.md)). The
plan's Issue Index is a thin pointer table.

A Design Plan is **short-lived implementation scaffolding**. It is not
an ADR. Durable items (vocabulary, hard trade-offs) get extracted to
`CONTEXT.md` and `docs/adr/` via `/grill-with-docs` during the design
session — this skill surfaces them; it does not write to those files
itself.

---

## File Naming and Location

```
docs/
  design/
    <feature-name>.md         ← Design Plan (this file's subject)
  adr/
    <decision>.md             ← Architecture Decision Records (owned by /grill-with-docs)
CONTEXT.md                    ← Domain vocabulary (owned by /grill-with-docs)
```

---

## Template

```markdown
# Design Plan: <Feature Name>

> Status: approved | shipped
> Created: YYYY-MM-DD
> Epic: <PRD link or parent issue>

## Context

One paragraph: what problem this feature solves, for whom, and why now.
No implementation details. Domain vocabulary only.

## Domain Vocabulary Used

Terms from CONTEXT.md that this plan relies on. If a term surfaced
during the design session and is not yet in CONTEXT.md, the skill
surfaced it for /grill-with-docs extraction — not captured here.

- **Order** — a customer's confirmed intent to purchase items
- **Fulfillment** — reserving inventory and dispatching a shipment

## Module Map

| Module | Responsibility | Interface (operations) | Seams |
|---|---|---|---|
| OrderFulfillment | Coordinate fulfillment of a confirmed order | `fulfill(orderId) → FulfillmentResult` | InventoryReservation, ShipmentDispatch |
| NotificationSender | Dispatch notifications to customers | `handleShipmentDispatched(event)` | NotificationGateway |

## Seams

| Seam | What crosses it | Adapter in tests | Adapter in prod |
|---|---|---|---|
| InventoryReservation | Reserve items for an order | FakeInventoryReservation (must enforce stock limits; return InsufficientStock on shortage) | InventoryServiceAdapter |
| ShipmentDispatch | Send a shipment | FakeShipmentDispatch (must record dispatched orderId; reject duplicate dispatches) | FedExAdapter |
| NotificationGateway | Send customer notifications | FakeNotificationGateway (must track sent notifications; support no-preferred-channel path) | EmailAdapter |

The parenthetical in *Adapter in tests* records the **fake contract** — the
behavioral expectation the fake must honor. A fake with no recorded contract
defaults to happy-path returns, which defeats its purpose (see
[modules-and-seams.md](modules-and-seams.md)). Keep it to one scannable line.

## Invariants and Contracts

Rules that must hold regardless of implementation.

- Fulfillment must be idempotent per orderId.
- Fulfillment may only proceed on a confirmed order.
- Notification handler must be safe to call more than once with the
  same event.

## Testing Strategy

| Module | Test entry point | Test level | Fake strategy |
|---|---|---|---|
| OrderFulfillment | `fulfill(orderId, { inventory, shipment })` | Unit | FakeInventoryReservation, FakeShipmentDispatch |
| NotificationSender | `handleShipmentDispatched(event)` | Unit | FakeNotificationGateway |
| End-to-end path | POST /orders/:id/fulfill | Integration | Real DB, FakeShipmentDispatch |

## Issue Index

One row per rewritten issue. Bodies live in the tracker; this is a
pointer table only. Frontend-flavored issue bodies additionally carry the
`**Frontend design**` routing block (see [issue-shape.md](issue-shape.md)).

| Issue | Module | One-line description |
|---|---|---|
| #12 | OrderFulfillment | Happy path: fulfill a confirmed order |
| #13 | OrderFulfillment | Idempotency: re-fulfill is a no-op |
| #14 | OrderFulfillment | Insufficient inventory returns FulfillmentFailed |
| #15 | NotificationSender | Confirmation sent on ShipmentDispatched |
| #16 | NotificationSender | Skip-with-warning when channel missing |

## Open Questions

Questions that need resolution before or during implementation. Close
each one with a decision or, for hard trade-offs, an ADR via
`/grill-with-docs`.

- [ ] Should partial fulfillment (some items available) be supported?
      (blocks #14)
- [ ] Is shipment dispatch synchronous or async? (affects seam design)
```

---

## Status Field

- **approved** — the user approved the batch; rewritten issues are
  live in the tracker; implementation can begin. The plan is **born in
  this state**: it is rendered in conversation and written to disk only
  after batch approval (SKILL.md step 9), so it never lands as a draft.
- **shipped** — the last issue in the index closed. Future agents read
  `CONTEXT.md` and ADRs first; the plan stays for historical context
  only.

There is no `draft` status — the skill never writes the plan to disk
before approval (that would break the one-batch-approval invariant in
SKILL.md step 9). There is no `stale` status either; drift is handled
inline (see next section).

---

## Handling Drift (Stale Sections)

The Design Plan will drift from reality as `/tdd` reveals corrections.
Handle drift inline rather than re-running the skill: add a callout
directly under the affected section heading.

```markdown
## Seams

> **Stale:** `PaymentGateway` was split into `PaymentAuthorizer` and
> `PaymentCapture` during implementation — the two-phase auth flow
> forced the split. See #47 and ADR-0009.

| Seam | What crosses it | Adapter in tests | Adapter in prod |
| ...
```

Then capture any durable lesson via `/grill-with-docs` (a new ADR for
the split decision; a new CONTEXT.md term if the split introduced
domain language).

If drift is so large the plan is unrecoverable, the user may re-invoke
`/software-design` on the remaining issues. That is the user's call,
not the skill's prescription.

---

## What the Design Plan Does Not Contain

- Issue bodies (those live in the tracker; the Issue Index links to
  them).
- File paths, class names, library choices (those go stale).
- Domain vocabulary definitions (those live in `CONTEXT.md`).
- Hard architectural decisions with real trade-offs (those become
  ADRs).
- Implementation details, code, or pseudo-code.
