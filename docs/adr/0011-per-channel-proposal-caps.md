# Proposal caps are per channel, not one global cap per run

The `apply-agent-research` loop's "**at most one issue per run**" cap becomes
**one issue per *channel* per run**. Each kind of output gets its own "one or
none" budget, each run through the [one-proposal gate](../../skills/meta/apply-agent-research/proposal-flow.md)
independently:

| Channel | Label / action | Destination | Basis |
|---|---|---|---|
| **self-improvement** | `source:agent-research` | Consumer's own tracker | a KB knowledge note |
| **skill-audit** | `source:skill-audit` | Consumer's own tracker | catalog comparison ([ADR 0010](0010-consumers-audit-local-skills-supply-side.md)) |
| **general-merit skill** *(skills repo only)* | `source:agent-research` | own tracker | a KB note warranting a net-new published skill |
| **skill-request** | `skill-request` | `dividedby/skills` | a KB note → a wished-for capability |
| **skill-promotion** | `skill-promotion` | `dividedby/skills` | a promotable local skill ([flow](../design/skill-promotion-flow.md)) |

**Why the change.** The single global cap forced orthogonal concerns — a
KB-sourced self-improvement, a redundant-local-skill flag, a cross-repo demand —
to compete for *one* slot, so a strong candidate in one channel suppressed a
strong candidate in another, discarding signal the channels exist to capture.
The channels target different concerns and (for skill-request / skill-promotion)
different repos; they are not substitutes.

**What is preserved.** The "**no menu, pick the single best**" discipline holds
*within* each channel — the gate still forces exactly one winner per channel, so
no channel sprays a backlog. Most channels emit zero on most runs; the bar per
channel is unchanged. Mechanically this is cheap: invoke the existing `gate`
once per channel-group instead of once globally — **no `lib/` change**, the gate
is already generic over the candidate set it is handed.

**Consequence.** A single run can now file up to one issue per applicable channel
(realistically ≤ ~3 in a Consumer's own tracker plus ≤ ~2 cross-repo), versus a
former hard ceiling of one. We accept the higher per-run ceiling because each
issue still clears a high, independent bar and zero remains the common case.

**Rejected alternative.** Keep the single global cap and let the new
skill-audit / skill-promotion candidates compete in it. Rejected: it reintroduces
exactly the cross-concern suppression above, and conflates a demand channel, a
supply channel, and two self-improvement concerns into one slot.
