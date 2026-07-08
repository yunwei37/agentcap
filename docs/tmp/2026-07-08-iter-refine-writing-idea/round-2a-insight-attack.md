# Round 2a: Insight Novelty Attack

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 2 adversarial novelty attack.

## Reviewer-Style Attack

The strongest rejection risk is that IntentCap could be read as ordinary ABAC plus capabilities plus provenance/IFC plus counters, specialized to agents. If the paper only says "we track intent, provenance, tools, and environment," the reviewer can classify it as a composition of known mechanisms rather than a new systems boundary.

The weak points identified in the pre-defense draft were:

1. The opening still made the core abstraction sound like richer permission checking, not a new authorization unit.
2. The four context classes risked reading as attribute groups rather than independent authority planes with separate issuers and promotion rules.
3. The lease lifecycle was under-motivated by workload facts. The paper needed to show why the same action argument can be safe or unsafe depending on mint, consume, expiry, and delegation state.
4. The related-work text was too absolute: saying a semantic-equivalent system could do the same without explaining that it must adopt the same transaction object weakens the novelty claim.
5. E3 needed a stronger alternative baseline: not only object ACL or taint, but a composite stateful ABAC baseline with taint labels, counters, and delegation tables.

## Required Defense

The defense should make one sentence central:

> Agent least privilege should be authorized over an intent-minted protected-decision transition, not over a tool, context source, resource, or already materialized action.

The four context classes should be framed as authority planes, not taxonomy:

- Agent context answers why the run is authorized.
- Instruction context answers which procedure may guide execution.
- Tool context answers which interface and declared side effects are available.
- Env context answers which runtime objects, values, and observations exist.

The no-promotion rule must be explicit: one plane cannot fill a missing field from another plane. Tool metadata cannot supply user intent; env output cannot become instruction; instruction text cannot mint approval or choose a sink.

E3 should test this claim directly with collapsed-plane, misclassified-plane, lifecycle-ablation, and split-state baselines.
