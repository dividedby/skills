# Designing for Testability

A testable interface is one where tests can exercise real behavior with
minimal setup and without knowing internals. Testability is a design
quality, not a testing trick.

---

## The Core Rules

### 1. Accept dependencies — don't create them

If a module creates its own external collaborators internally, tests
can't replace them. Pass dependencies in. The seam is at the parameter,
not inside the function.

```typescript
// Testable: seam at the parameter
function fulfillOrder(order: Order, shipment: ShipmentDispatch): FulfillmentResult

// Hard to test: seam buried inside
function fulfillOrder(order: Order): FulfillmentResult {
  const shipment = new FedExClient(process.env.FEDEX_KEY) // can't replace this
}
```

### 2. Return results — don't produce hidden side effects

A function that returns a value is trivially testable: call it, inspect
the result. A function that produces side effects via hidden
collaborators requires intercepting those effects.

```typescript
// Testable: result is the test surface
function calculateFulfillmentCost(order: Order, rateTable: RateTable): Money

// Hard to test: side effect is the only observable outcome
function applyFulfillmentCost(order: Order): void {
  order.cost = lookupRate(order.weight) // mutates shared state
}
```

Where side effects are unavoidable (persistence, messaging), push them
to the boundary and test the domain logic separately from the I/O.

### 3. Small surface area

Fewer operations = fewer tests needed. Simpler parameters = simpler test
setup. If a module's tests require 10 lines of setup before every
assertion, the interface is too complex. Ask: can I push some of that
setup inside the module?

### 4. Prefer SDK-style interfaces over generic ones at seams

At boundaries, define specific operations rather than one generic
dispatcher. Each operation is independently testable and produces one
specific shape.

```typescript
// GOOD: each operation is independently fake-able
interface OrderStore {
  load(id: OrderId): Order
  save(order: Order): void
  findByCustomer(customerId: CustomerId): Order[]
}

// BAD: requires conditional logic in every fake
interface OrderStore {
  execute(query: Query): unknown
}
```

---

## Designing the Public Interface for a Module

When the skill sketches the interface for a module:

1. **Name operations in the domain's language.** `fulfillOrder`, not
   `processRequest`.
2. **Use value types, not primitives.** `OrderId` not `string`. `Money`
   not `number`. This prevents callers from passing the wrong thing and
   makes tests self-documenting.
3. **Make the happy path obvious.** The zero-setup call is the common
   case.
4. **Make failure explicit.** Return a typed result or throw a typed
   error. Don't hide failure in `null` or `undefined`.
5. **Avoid boolean flags.** `ship(order, true)` — true *what*? Use named
   variants or separate operations.

---

## Testability Checklist for Proposed Interfaces

Before finalizing a module's interface in the Design Plan:

```
[ ] Dependencies are injected, not created internally
[ ] Operations return values or typed errors — no hidden side effects
[ ] External I/O lives at a named seam, not embedded in logic
[ ] Value types used for domain concepts (no primitive obsession)
[ ] Interface is narrow enough that test setup is simple
[ ] Seam operations are specifically named — no generic dispatcher at seams
[ ] No boolean flag parameters — use named variants or separate operations
[ ] Each operation tests cleanly without requiring other operations first
```

---

## Testability Anti-Patterns

**Static singletons as dependencies.** Global state means tests share
state and can't run in isolation. Pass state explicitly or use a factory
that accepts a context.

**Temporal coupling.** "You must call `initialize()` before `process()`
before `finalize()`." Each operation should be callable independently,
or the required order should be encoded in the types — e.g. `reserve()`
returns a token that `dispatch()` requires as input, so the wrong order
won't compile.

**Void commands with no observable result.** If a function does
something but returns nothing, tests must check side effects. Where
possible, return a result even for commands: the new state, the ID of
what was created, or an event.

**Deep call stacks before reaching testable behavior.** If the public
interface immediately delegates through five private helpers before
doing anything testable, tests are forced to use the outermost call with
full setup. Consider whether the helpers should be extracted as a
deeper module with its own interface.
