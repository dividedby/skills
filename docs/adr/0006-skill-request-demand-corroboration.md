# skill-request demand corroboration is allowed

The [`skill-request` flow](../design/skill-request-flow.md) **aggregates**
duplicate requests: when N Consumer repos each file a `skill-request` for the
same capability, the duplicates attach as "+1 / also wanted by `<repo>`" to the
existing issue rather than being suppressed. The count of repos wanting a
capability is **demand signal** that raises that skill's build priority.

This looks like it contradicts agent-research
[ADR 0018](https://github.com/dividedby/agent-research/blob/main/docs/adr/0018-no-cross-subject-corroboration-layer.md)
("no cross-subject corroboration layer"), which forbids strengthening a knowledge
*claim* by counting how many subjects assert it. It does not — **different layer,
different rule**:

- **0018 forbids corroborating a knowledge *claim*.** Marking a claim "asserted by
  N subjects" usurps a selection decision the *consumer* owns and pushes false
  confidence up into the knowledge layer, which must stay neutral. 0018's own gate
  for revisiting is "a concrete downstream decision that changes" — and no one
  could name one for claim-counting.
- **This corroborates *demand*, not a claim.** Counting how many repos request a
  capability changes a concrete, owned decision: which skill the maintainer builds
  next. That passes 0018's gate rather than failing it. Demand lives in a different
  layer (cross-repo build prioritization) than knowledge claims (cross-subject
  truth-weighting), so the prohibition does not reach it.

**Decision.** Duplicate `skill-request`s aggregate as demand corroboration; they
are never dedup-suppressed. This is deliberately *unlike* the exact-key
suppression in `runbooks/lib/proposal_gate.py` (which dedups a single repo's own
proposals to protect the one-issue-per-run cap) and *unlike* ADR 0018. Usefulness
of a *built* skill is still settled by **adoption**, not by request count — the
demand signal sets build order, it does not by itself justify a skill.

**Rejected alternative.** Treating duplicate `skill-request`s as dedups (drop the
later ones). Rejected: that discards the one signal the channel exists to capture
— that a gap is felt in more than one repo.
