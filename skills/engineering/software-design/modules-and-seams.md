# Modules and Seams

The unit of design. Vocabulary, depth, the deletion test, seam placement,
adapter strategy at boundaries, decomposition heuristics, and the
anti-patterns to avoid.

---

## Vocabulary

Use these terms exactly. Do not substitute "service," "component," or
"layer."

- **Module** — anything with an interface and an implementation: a
  function, class, package, domain slice.
- **Interface** — everything a caller must know: operations, inputs,
  outputs, invariants, error modes. Not just the type signature.
- **Implementation** — the code inside the module. Callers should not
  need to know it.
- **Depth** — the leverage a module provides. A *deep* module hides a
  lot of complexity behind a small interface. A *shallow* module has an
  interface nearly as complex as its implementation.
- **Seam** — the location where an interface lives. A place where
  behavior can be changed or substituted without editing internals.
- **Adapter** — a concrete thing that satisfies an interface at a seam.
- **Boundary** — a seam at the edge of the system: database, payment
  provider, queue, filesystem, clock, another team's service. Boundaries
  are where adapters live and where tests use fakes.
- **Deletion test** — a heuristic: if you deleted this module, would its
  complexity vanish, or reappear across callers? Vanishing → shallow
  pass-through. Reappearing → the module was earning its keep.

---

## Deep vs Shallow

```
DEEP MODULE (good)

┌───────────────────┐
│  Simple Interface │  ← 2–3 operations, simple params
├───────────────────┤
│                   │
│  Complex          │  ← Validation, retries, state
│  Implementation   │      coordination, error handling
│                   │
└───────────────────┘

SHALLOW MODULE (avoid)

┌────────────────────────────────┐
│  Complex Interface             │  ← Many params, many operations,
│  nearly matches internals      │      callers must know internals
├────────────────────────────────┤
│  Thin Implementation           │  ← Mostly passes through
└────────────────────────────────┘
```

A shallow module is a tax on callers. It forces them to know details they
shouldn't need. A deep module is leverage: callers get a lot of behavior
from knowing very little.

### Deepening a shallow module

When you spot a shallow module, ask:

- Can I reduce the number of operations on the interface?
- Can I move error handling or validation inside?
- Can I hide a decision (retry, fallback, default) that callers currently
  make themselves?
- Can two modules collapse into one if they always change together?

---

## Module Responsibilities

Each module has exactly one reason to change. If you can describe the
module's responsibility with the word "and," split it.

```
BAD:  "Handles payments and sends confirmation emails"
GOOD: PaymentProcessor — "charges and records a payment"
      NotificationSender — "dispatches confirmation events to subscribers"
```

"Reason to change" means: one actor (person, team, external system)
whose requirements drive changes to this module. If two different actors
could independently request different changes to the same module, split.

### Single-responsibility check

For each proposed module, ask:

- Who would request a change to this module?
- What kind of change would they request?
- Could two *different* actors request *different* changes to the same
  module?

If yes: split. The two actors own different responsibilities.

---

## Seams

A seam is where an interface lives. It is the point where one module
hands off to another.

- **One adapter = a hypothetical seam.** You could swap it, but you
  haven't yet.
- **Two adapters = a real seam.** Proven by use: tests use one adapter;
  production uses another.

### Why seams matter

Seams are the design decisions that survive implementation. They define:

- What gets faked in tests (at seams only — see the boundary section
  below).
- Where change is expected and contained.
- Where you could later replace one implementation with another.

When naming a seam, use a domain noun for the role it plays:
`PaymentGateway`, `OrderStore`, `ShipmentDispatch`. Not
`PaymentServiceInterface` or `IRepository`.

### Finding seams

Look for these signals in the issue set:

- Two issues that could be implemented in parallel by different people
  → likely a seam between them.
- An issue that mentions an external system (email, payment, queue)
  → seam at that boundary.
- Two issues where the second consumes the first's output → seam at
  the handoff.

---

## Boundaries — Seams at the Edge

A boundary is a seam where the code meets something it doesn't control.
Boundaries are the only place tests should use fakes.

### Identifying boundaries

| Signal in the issue / PRD | Boundary type |
|---|---|
| "calls the payment API" | External service |
| "writes to the database" | Persistence |
| "publishes an event to the queue" | Async messaging |
| "sends an email / push notification" | Notification gateway |
| "reads the current time" | Clock |
| "calls another team's service" | Inter-team boundary |
| "reads from / writes to disk" | File system |

### Naming boundaries

Use domain language, not the technology:

```
BAD:  StripeClient, PostgresRepository, KafkaProducer
GOOD: PaymentGateway, OrderStore, DomainEventBus
```

The name describes what the boundary does *for the domain*, not *how*.
The adapter (Stripe, Postgres, Kafka) lives behind the seam.

### Adapter strategy

For each boundary, decide the adapter strategy before writing issues.

**Real adapter (preferred where practical).** Use a real implementation
in tests against a test database, local server, or sandbox. High
confidence, slower, catches real integration bugs.

**In-memory / fake adapter.** A simple in-memory implementation that
satisfies the interface. Fast, deterministic, good for domain logic
tests. Must faithfully implement the contract — not just happy-path
values.

**Stub / mock (last resort, at boundaries only).** Hardcoded returns or
call capture. Only at external services with no sandbox. Never mock your
own modules — that couples tests to implementation.

Record the strategy in the Design Plan's Seams table (see
[design-plan-format.md](design-plan-format.md)). Embed the behavioral
expectation — the **fake contract** — as a parenthetical in the *Adapter in
tests* cell:

```
FakePaymentGateway (must simulate declines; return a PaymentResult for any charged amount)
```

One-line parentheticals keep the table scannable. A fake with no recorded
contract obligation defaults to happy-path returns — which defeats the purpose
of the fake.

### What belongs inside vs outside

```
INSIDE the domain (no boundary needed):
  Business rules
  Validation logic
  State transitions
  Computations

OUTSIDE the domain (needs a boundary):
  Persistence reads and writes
  External API calls
  Event publishing / consuming
  Time and randomness
  File I/O
  Email, SMS, push
```

The more domain logic that lives inside, the easier it is to test
without fakes.

### Async and event boundaries

When an issue involves publishing or consuming events:

1. Name the event in domain terms: `OrderConfirmed`, `PaymentFailed`.
2. Define publisher and consumer as separate modules.
3. The boundary is the event bus seam — not the payload shape.
4. Design for idempotency at the consumer: consuming the same event
   twice must be safe.

TDD note for issues at event boundaries: *test the consumer by calling
its handler directly with a synthetic event — do not test by publishing
to a real queue.*

### Cross-team boundaries

If an issue depends on another team's module or service:

1. Name the seam after what your domain needs, not what they provide.
2. Write a fake adapter your team controls.
3. Add an integration issue (separate) for wiring to the real
   implementation.
4. Never block domain issues on another team's schedule.

```
Seam: ShipmentDispatch (wraps LogisticsTeam's API)
  Domain issue: test via FakeShipmentDispatch
  Integration issue: #42 — wire ShipmentDispatch to LogisticsAPI
```

---

## Decomposition Heuristics

Reading the issue set, look for the cuts.

**Different actors.** Issues that serve different stakeholders
(customer-facing vs internal tooling vs system automation) often belong
in different modules.

**Different change rates.** Business rules change frequently;
infrastructure adapters change rarely. Different rates → different
modules.

**Different origins of complexity.** A module that is complex because
of business rules is different from one that is complex because of I/O
coordination. Keep them separate.

**Natural-language conjunctions.** If the issue description uses "and"
to describe two distinct outcomes, it describes two behaviors. Split.

**Reuse signals.** If an issue describes something that "also needs to
happen" in another context, that's a module. Give the shared behavior
a home.

### Patterns to reach for

- **Domain core + boundary adapters.** Business logic has no external
  dependencies; adapters satisfy the core's seams.
- **Command / query separation.** State-changing operations are
  separate from data-returning ones. Each tests differently.
- **Event-driven handoff.** When module A's output triggers module B's
  work, model the handoff as a domain event. Neither knows about the
  other.
- **Orchestrator + workers.** An orchestrator knows the steps and their
  order; workers know how to do each step. Test the orchestrator with
  fake workers; test each worker independently.

---

## Module Map Format

When presenting a module to the user:

```
Module: <Name>
  Responsibility:  <one sentence, one reason to change>
  Interface:       <operations — verbs from domain vocabulary>
  Invariants:      <rules this module owns>
  Depends on:      <other modules or seams>
  Must not depend on: <e.g., transport layer, persistence>
```

Example:

```
Module: OrderFulfillment
  Responsibility:  Coordinate the steps required to fulfill a confirmed order.
  Interface:       fulfill(orderId) → FulfillmentResult
  Invariants:      Order must be confirmed before fulfillment begins.
                   Fulfillment is idempotent per orderId.
  Depends on:      InventoryReservation (seam), ShipmentDispatch (seam)
  Must not depend on: HTTP transport, database directly
```

---

## Anti-Patterns

**Layer-cake decomposition.** Splitting by controller / service /
repository is technology structure, not domain structure. These layers
always change together and can rarely be tested in isolation.

**Nano-modules.** Interface complexity is roughly equal to
implementation complexity. Apply the deletion test: if deleting it just
moves the code to the caller, it wasn't earning its keep.

**God module.** Everything depends on one module named `AppService` or
`Core`. Decompose by finding the distinct actors or behaviors it
serves.

**Premature seams.** Adding a seam "in case we need to swap it later"
without a concrete second adapter. One adapter = hypothetical seam;
only promote to a real seam when two adapters exist.
