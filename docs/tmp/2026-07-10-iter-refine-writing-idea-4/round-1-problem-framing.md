# Iter Refine Writing Idea Round 1: Problem Framing

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 1 problem framing.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer input: read-only subagent review using a senior systems-reviewer framing and the idea-quality checklist Section 1.

## Main Findings

The draft already has a coherent core idea: the authorization object is a protected-decision record committed before side effects, prompt authority placement, or handoff. The main weakness was not the mechanism itself but framing clarity:

- `agent context` could be misread as the LLM or agent plan being a trusted issuer.
- The introduction used solution vocabulary before the reader had seen the concrete pain.
- The four owner classes needed to be motivated earlier as proof-ownership boundaries derived by a safe-merge criterion, not as an arbitrary taxonomy.
- The motivation and evidence-status sections still exposed too much run-log detail in the main narrative.

## Changes Applied

- Renamed the first paper-facing authority owner to `intent/agent-runtime` in the abstract, introduction, design overview, owner-class table, and related-work positioning.
- Added an explicit statement that `intent/agent-runtime` means trusted issuer canonicalization of user intent, object selection, sink, approval, and delegation root, not LLM-generated plan authority.
- Rewrote the introduction problem setup with a concrete bad trace: hidden PDF text causes delegation, child reuse of one-shot issue authority, and an action guard misses the violation because the repo argument is still legal.
- Added an early convergence statement for prior work: any runtime or policy DSL that exposes the same owner-typed pre-effect record with same-transition lifecycle update implements the IntentCap interface on those fields.
- Moved the safe-merge criterion into the introduction: context sources can merge only when issuer, forgeability surface, observation boundary, and lifecycle authority are equivalent.
- Simplified Problem Characterization so it motivates the design qualitatively and forwards detailed numbers to E2.
- Compressed benchmark diagnostics into gate-level takeaways: output-protocol failure, context-capacity/backend failure, and remaining planner/compiler recall.
- Shortened the Current Evidence table so it reads as claim boundary rather than an experiment ledger.

## Remaining Risks

- The paper still uses the implementation symbol `agent` in formal sets and edge labels such as `tool->agent`; the draft now explains that this denotes `intent/agent-runtime`, but a future notation pass could rename the symbol itself.
- Benchmark utility is still an explicit evidence boundary, not a top-level supported claim.
- Independent blinded field-owner adjudication and expert-oracle minimality scoring remain future evidence requirements for a stronger top-conference claim.

