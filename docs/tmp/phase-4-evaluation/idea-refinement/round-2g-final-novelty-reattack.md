# Round 2g: Final Novelty Re-Attack

Date: 2026-07-07

## What Was Checked

Final adversarial novelty re-attack after the paper added a state-transition lease lifecycle block.

## Findings

Subagent reviewer reported:

> No, after the new lifecycle block I cannot easily construct a strong reject argument that IntentCap is merely renamed intent/provenance/action guard/IFC work.

> The surviving novelty claim is that IntentCap models future protected-decision influence authority as an intent-derived, provenance-gated, consumable, expirable, attenuable run-time lease that cannot be amplified by untrusted context, and enforces it across context/tool/MCP/local-execution/delegation boundaries.

Remaining major risk:

> A reviewer may still call this a natural composition of stateful capabilities plus provenance policy unless the paper shows which compound traces need trusted mint provenance, per-lease consumption/expiration, protected-decision influence modes, and parent-child capability partial order together.

## What Was Changed

- Contribution 1 now states that the lease calculus is for protected decision authority, not only operation authority.
- Formal model now explicitly says a lease is a stateful authorization object for future protected decisions.
- Runtime state now includes active/exhausted leases, consumption counters, temporal automata, mint proof records, and parent-child delegation relation.
- Added Table 1 with a compound lifecycle trace covering consumed approval reuse, PDF-induced authority widening, and non-monotone subagent delegation.
- Related work now states that an equivalent system must maintain four state classes simultaneously: trusted mint provenance, per-lease consumption/expiration, protected-decision influence modes, and parent-child capability partial order.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Remaining warnings are font/underfull/very small overfull layout warnings, not compilation failures.

## Remaining Concerns

Round 2 can stop. The paper must keep the caveat that provenance labels, taint tracking, intent checking, and attenuable capabilities are not individually new; the claim is agent-specific authorization granularity and lifecycle composition.
