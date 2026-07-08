# Round 2c: Insight Re-Attack

Date: 2026-07-07

## What Was Checked

Adversarial re-review after Round 2b's defense, focusing on whether the new framing blocks the "just capability + provenance + stateful policy" rejection.

Revised framing under review:
- Protected decisions are authority-state transitions.
- A lease atomically binds trusted mint provenance, decision-specific influence authority, consumption/expiry, and delegation partial order.
- E3 now tests strict subsets of the lifecycle components.

## Findings

Reviewer verdict:

> The attack is no longer as easy, but a strong rejection argument still exists. The paper now blocks the coarse "just taint/provenance" attack, but a reviewer can still argue that the lease is a conventional stateful authorization policy with transactional updates.

Strongest remaining rejection argument:

> A policy engine can maintain a table containing provenance constraints, counters, expiry predicates, and delegation edges, and update them atomically before executing a side effect. The paper does not yet show a property, interface, or workload constraint that forces these fields to be one "lease" abstraction rather than a well-engineered policy state machine.

Key remaining issues:
- `line 276`: saying an equivalent baseline needs an equivalent atomic object may make the contribution sound like naming/organization.
- `line 236`: atomic update is claimed but the runtime boundary is not explicit.
- `lines 227-234`: the lease tuple lacks an explicit "system interface" role.
- `lines 367-371`: E3 is stronger, but does not yet distinguish ordinary stateful provenance policy from a lease-style transaction API.
- The table around `lines 280-294` lacks a split-state failure trace showing why separate policy records are risky.

## User-Identified Missing Axis

During this round, the user pointed out a related gap:

> We need to discuss what context each component carries: Skills carry Skill context, tool calls carry tool-call context, and the agent has its own intent. The actual capability should be decided by these three together.

This is a useful defense direction. A capability is not just a policy row with provenance/counters. In agent extensions it should be synthesized from:
- agent/task context: current intent, selected objects, allowed sinks, approval state, plan state;
- extension context: Skill/MCP/tool metadata, declared workflow, scripts/resources, trust/endorsement;
- invocation/runtime context: concrete call arguments, observed tool results, runtime evidence, parent/child delegation state.

## Required Next Defense

Round 2d should revise the paper to state that the lease API is the minimal transaction interface over these three context sources:

`capability = solve(agent_intent_context, extension_context, invocation_context, policy)`

The checker should expose transitions such as `mint`, `check_and_consume`, `attenuate`, and `expire`, and these transitions should be the only way to change authority state before side effects.

## What Was Changed

No paper edits in Round 2c. This round is adversarial review only.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`.
- Build completed successfully.
- Final log check found no undefined citations, undefined references, fatal errors, or LaTeX errors.

## Remaining Concerns

- Need one more defense pass before moving to Round 3. The goal is not to prove no stateful policy engine can be equivalent, but to make the paper's abstraction clearer: IntentCap formalizes the agent-specific transaction API over agent intent, extension context, and invocation/runtime context.
