# Round 5: Reviewer Stress Test

Date: 2026-07-08

## What Was Checked

A read-only reviewer attempted to write the strongest remaining reject argument after all idea-layer revisions. The target was `docs/autopaper/intentcap-paper-zh.tex`.

## Reviewer Verdict

The reviewer found that the framing/logic is no longer easy to reject as EIM/ActPlane/IFC/ABAC/SkillGuard under a different name. The strongest remaining reject is evidence-driven:

> The paper identifies a clear authorization unit, but has not yet shown with workload-scale evidence that this unit is necessary, effective, and better than the strongest composite baseline in realistic agent workflows. The current draft is a mechanism plus claim scaffold with pilot evidence, not a complete OSDI/SOSP full-paper evidence package.

## Must-Fix Evidence Gates Identified

- E3: implement and report the split-state composite baseline: stateful ABAC + taint + counters + delegation table. Show whether it false-accepts stale reuse, cross-plane promotion, policy update, and delegation mismatch.
- Workload characterization: quantify protected-decision transitions in AgentDojo, MCPTox, InjecAgent, and tau2-style traces, including sink selection, approval widening, capability request, policy update, delegation, stale reuse, and cross-plane promotion.
- System path: add at least one real cross-boundary path where Skill/manual placement, MCP/tool gateway, local env pre-side-effect, and delegation check all call the same checker before side effect or authority transfer.
- Provenance proof completeness: report precise proof, conservative prompt-wide proof, and missing proof rates, plus false denial/recovery/utility impact.
- Evidence organization: keep main text claim-facing by E1-E4; move run IDs and sanity/probe details to artifact tables or appendix.

## What Was Changed

- Abstract, line 25 before edit: one long sentence contained problem, insight, mechanism, and evidence boundary.
  After edit: split into four sentence-level beats.

- Contribution C3 before edit: suitable for an extended abstract but did not state what happens in the full paper.
  After edit: C3 explicitly says the full-paper version should replace this contribution with completed workload characterization and evaluation results.

- E2 before edit: explained why trace labels cannot replace expert leases, but did not state a labeling rubric.
  After edit: added rubric fields: minimal object scope, allowed influence modes, argument predicates, budget/expiry, delegation bounds, and approval scope.

- E4 before edit: had one primary outcome phrased around API coverage but still read like recovery practicality.
  After edit: E4 now has two primary outcomes: adapter coverage before side effect/authority transfer, and valid recovery without broad authority.

- Related work before edit: matrix had concrete rows but lacked explanatory text for the no/partial claims.
  After edit: added a paragraph explaining the precise missing abstraction for CaMeL/IFC, AuthGraph/PACT/AIRGuard, SkillGuard/SkillScope, Progent/PCAS/AgentSpec, and ActPlane.

## Verification

Compiled from `docs/autopaper` with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex
```

Checked for undefined citations, undefined references, and overfull boxes. No matching warnings remained; only underfull table warnings remained.

## Remaining Concerns

Idea refinement is complete for the current extended abstract. Further improvement should prioritize experiments rather than conceptual rewriting:

- E1 benchmark security/utility.
- E2 independent expert-oracle replication.
- E3 workload characterization plus strongest composite baseline.
- E4 cross-boundary adapter/recovery/provenance-completeness evidence.
