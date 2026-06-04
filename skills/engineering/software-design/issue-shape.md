# Issue Shape

The TDD-ready format the skill writes into each rewritten issue body.
The issue tracker is authoritative for issue bodies; the Design Plan
never duplicates this content (it links to the issue instead).

A TDD-ready issue is a unit of work that `/tdd` can execute without
asking "what should I test?" It names the observable behavior, the
entry point, and the key edge cases.

---

## The Problem with Raw Issues

Issues from `/to-issues` describe *what to build* at a feature level.
They are correct, but they are not TDD-ready because they don't specify:

- Which module owns the behavior
- What the test entry point is
- Which behaviors to test first
- What edge cases matter
- Where to put fakes

A raw issue is a destination. A TDD-ready issue is a map.

---

## The Format

Each rewritten issue body contains, in order:

```
**Module**: <module name>

**Behavior**: As a <actor>, I can <behavior> so that <value>.

**Acceptance criteria**:
- Given <precondition>, when <action>, then <observable outcome>
- Given <different precondition>, when <action>, then <different outcome>
- ...

**Frontend design** (invoke `/frontend-design` before `/tdd`):
- Stack: <e.g. Next.js 15 + Tailwind v4>
- Intent: <one-line user-facing intent>
- Aesthetic direction: see docs/design/direction.md
- Token authority: <path recorded in docs/design/direction.md>
- Review: required           ← only when AC explicitly mention a11y / contrast / design audit

**TDD notes**:
- Entry point: <public function / command / endpoint>
- Test first: <most critical behavior>
- Edge cases: <list>
- Fake strategy: <what to fake, at which seam>
- Must NOT test: <internal details to avoid coupling>
```

The `**Frontend design**` block is only present on **frontend-flavored
issues** (see detection rule below). For backend-only issues the block
is omitted entirely.

The body replaces (does not extend) the raw `/to-issues` content. The
issue title can stay; the body is rewritten.

---

## Durability: Write Briefs That Survive Code Drift

A TDD-ready issue may sit unworked for weeks, then be picked up cold by an
unattended agent (this is the brief `/autonomous-loop` consumes — it checks
for this durability before running, and bounces a brief that lacks it back
here). An issue body must stay correct as the codebase moves underneath it.
Write for **durability over precision**:

- **Name behaviours, interfaces, and types — not file paths or line
  numbers.** "the `OrderFulfillment` module's `fulfill` entry point", not
  `src/orders/fulfill.ts:42`. Paths and line numbers go stale while the
  issue waits; a named contract does not.
- **State *what* the system should do, not *how* to wire it.** Acceptance
  criteria are observable outcomes (the `Given/when/then` form above), not
  implementation steps.
- **Make acceptance criteria independently verifiable** and bound the work
  with an explicit out-of-scope note when the boundary is non-obvious, so a
  cold reader knows when they are done and what not to touch.

---

## Frontend-Flavored Detection (Two-of-Three Trigger)

Evaluate each issue against three signals. An issue is **frontend-flavored**
— and gets the `**Frontend design**` stamp — when **two of the three** are
true:

1. **Output surface is visible** — the issue describes something a user
   sees: a page, screen, component, modal, form, chart, theme, or layout.
   Keyword smell: *renders, displays, shows, page, screen, component,
   modal, form, button, layout, theme, responsive, mobile, desktop*.
2. **Module responsibility is presentational** — the cluster lands in a
   module whose one-reason-to-change is presentation (a React component
   tree, a page route, a style system). A pure data module with a
   downstream UI consumer does **not** count.
3. **Acceptance criteria mention visual or interaction behavior** —
   color, spacing, focus state, hover, animation, accessibility
   (keyboard nav, contrast, screen reader), responsive breakpoints.

One signal is too loose; three is too strict. Two is the right bar.

### Stamping Rule

Every frontend-flavored issue gets the `**Frontend design**` stamp,
**regardless of backlog size**. Even a one-issue UI tweak gets the stamp —
uniformity beats optimisation. `/software-design` performs the stamp pass
even when otherwise eligible for early-exit (see `SKILL.md`).

The four field values are written **mechanically**, not interpreted:

- **Stack** — read from the project's package manifest / framework config.
- **Intent** — paraphrase the `Behavior:` line.
- **Aesthetic direction** — always the literal string
  `see docs/design/direction.md`. Do not invent a direction; do not check
  whether the file exists. `/frontend-design` self-bootstraps on first run.
- **Token authority** — the path recorded in `docs/design/direction.md`'s
  `Token authority:` field. If the direction doc does not exist yet,
  write the literal `recorded in docs/design/direction.md` placeholder.
- **Review** — only add the line `Review: required` when the issue's
  acceptance criteria explicitly mention accessibility, contrast, or a
  design audit. Otherwise omit.

The stamping pass never opens `docs/design/direction.md` and never asks
about typography, color, or motion. Those decisions belong to
`/frontend-design`, not here.

---

## Before and After Example

### Before (raw issue from `/to-issues`)

```
Title: Add order fulfillment
Body:  Implement the ability to fulfill orders once payment is confirmed.
       Should integrate with the shipment service and send a
       confirmation email.
```

### After (`/software-design` splits and rewrites into two issues)

**Issue A — OrderFulfillment**

```
**Module**: OrderFulfillment

**Behavior**: As the system, I can fulfill a confirmed order so that
inventory is reserved and a shipment is dispatched.

**Acceptance criteria**:
- Given a confirmed order, when fulfill(orderId) is called,
  then inventory is reserved and ShipmentDispatch.send() is called.
- Given an already-fulfilled order, when fulfill(orderId) is called
  again, then no duplicate shipment is dispatched (idempotent).
- Given a confirmed order where inventory is insufficient,
  when fulfill(orderId) is called, then a FulfillmentFailed result is
  returned.

**TDD notes**:
- Entry point: fulfillOrder(orderId, { inventorySeam, shipmentSeam })
- Test first: happy path — confirmed order → reserved + dispatched
- Edge cases: idempotency, insufficient inventory, missing order
- Fake strategy: FakeInventoryReservation, FakeShipmentDispatch
- Must NOT test: how shipment is sent internally (FedEx vs UPS)
```

**Issue B — NotificationSender**

```
**Module**: NotificationSender

**Behavior**: As a customer, I receive a confirmation notification
when my order ships so that I know when to expect delivery.

**Acceptance criteria**:
- Given a ShipmentDispatched event, when the notification handler
  processes it, then a confirmation is sent to the customer's
  preferred channel.
- Given a customer with no preferred channel set, when the event is
  processed, then the notification is skipped and a warning is logged.

**TDD notes**:
- Entry point: handleShipmentDispatched(event)
- Test first: customer receives notification on happy path
- Edge cases: missing preferred channel, duplicate event (idempotency)
- Fake strategy: FakeNotificationGateway at the outbound boundary
- Must NOT test: email template markup or push payload format
```

---

## Splitting Rules

Split an issue whenever it:

- Touches more than one module.
- Describes both a domain behavior *and* an integration step (e.g.
  "process payment and publish event").
- Mixes a core behavior with an edge case that belongs to a different
  flow.
- Contains the word "and" describing two distinct user-facing outcomes.

When you split, each resulting issue is independently implementable —
one does not require the other to be done first unless it is a real
data-flow dependency.

---

## Ordering Issues Within an Epic

After rewriting all issues, order them:

1. **Tracer bullet first** — the issue that proves the path works
   end-to-end.
2. **Core behavior** — happy-path issues for each module.
3. **Edge cases** — error paths, invariant violations, idempotency.
4. **Integration** — issues that wire adapters to real implementations.

Issues in the same module can often be worked in parallel. Issues that
cross a seam must respect the dependency order.

---

## TDD Notes Anti-Patterns

**"Test that it calls X"** — tests implementation, not behavior.
Replace with "test that the observable outcome Y occurs."

**"Fake the internal helper Z"** — helpers are not seams. If a helper
needs isolation, extract it as a module with its own interface.

**"Test via the database"** — tests should use the module's public
interface. Verifying through the database couples tests to persistence
details.

**"Test all edge cases in one issue"** — each issue is one RED→GREEN
cycle for `/tdd`. Keep each issue to one logical behavior. Edge cases
get their own issues.
