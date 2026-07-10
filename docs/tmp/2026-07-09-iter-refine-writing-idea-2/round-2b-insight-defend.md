# Round 2b - Insight Defense

Date: 2026-07-09

## What Was Changed

Updated `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` to defend the paper's novelty against the "just a strong policy DSL" rejection.

## Changes

1. Abstract insight tightened.

Before: the abstract said agent authorization is not a policy predicate.

After: line 30 now says the missing object is a `pre-effect commit interface` that agent runtimes do not expose by default.

2. E1/E4 result interpretation narrowed.

Before: the abstract and evaluation could make `0 unsafe accepts` read like the main security proof.

After: lines 36--38 and 786 frame saved-trace replay and local boundary rows as implementation consistency, coverage, and boundary checks. E3 is now named as the mechanism evidence.

3. Policy-DSL equivalence boundary added.

Before: the paper compared against weaker policy variants but did not clearly state what happens if a strong DSL implements all required state.

After: line 55 and line 585 state that a DSL/reference monitor/IFC runtime becomes IntentCap-equivalent on covered fields if it exposes field-owner projections, checker-owned lease state, same-transition consume/delegate update, and an effect-bound audit commit id at the same linearization point.

4. Four context classes tied to workload-derived owner classes.

Before: the text explained agent/instruction/tool/env mostly as conceptual classes.

After: Table `boundary-owner-classes` around line 251 derives them from protected fields across user selections/approvals, Skill/manual workflow instructions, MCP/cmd schemas, runtime observations, and subagent handoff state.

5. E3 strongest baseline surfaced.

Before: E3 focused on no-owner collapse and split-state variants.

After: lines 786, 808, and 832 explicitly include the `typed-provenance state guard` as a strong convergence baseline. The text explains that it blocks 6/7 workflow residuals and only fails over-delegation because it lacks same-transition parent-child lease comparison and child-state update. If it adds those pieces, it implements the IntentCap commit interface on that residual class.

## Remaining Concerns

Round 2c should re-attack the revised paper. The likely remaining reviewer concern is whether the paper has enough independent labeling and end-to-end utility evidence for a top-conference claim. That is now explicitly scoped as missing evidence rather than hidden behind the current safety numbers.
