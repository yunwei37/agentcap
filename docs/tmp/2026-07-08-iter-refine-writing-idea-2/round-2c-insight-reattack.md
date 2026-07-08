# Round 2c: Insight Re-Attack

Date: 2026-07-08

## What Was Checked

A second read-only skeptical reviewer re-attacked the novelty of `docs/autopaper/intentcap-paper-zh.tex` after the Round 2b defense. The focus was whether IntentCap still looks like provenance/IFC/ABAC/capabilities/stateful policy, ActPlane with policy synthesis, or SkillGuard with different vocabulary.

## Findings

The reviewer concluded that the conceptual attack is now mostly blocked. The remaining rejection argument is evidence-driven rather than framing-driven:

- E3 must include workload characterization, not only residual suites.
- E3 must implement the strongest split-state composite baseline.
- Related work should compare concrete systems rather than only families.
- The system claim needs clearer adapter coverage and provenance-proof completeness metrics.
- The paper should present a conditional claim ladder rather than a flat set of claims.

## What Was Changed

- Abstract, line 25 before edit: still one dense sentence grouping problem, insight, mechanism, and evidence boundary.
  After edit: rewrote it into four sentence-level beats: problem, insight, mechanism, and current evidence boundary.

- Formal model, after the no-substitution rule before edit: stated that tool metadata cannot prove a user-authorized sink, but did not show an accepted/denied mini-example.
  After edit: added two judgments: a tool-issued proof is accepted for `github_schema` but rejected for `authorized_sink`; also stated tool results/metadata cannot prove `policy_update`.

- E1 and E4 metrics before edit: mentioned proof completeness only generically or not at all.
  After edit: added provenance-proof completeness metrics: precise structured proof, prompt-wide conservative proof, missing proof, and their relationship to false denial/recovery.

- Claim boundary before edit: honest but read like a general limitation paragraph.
  After edit: replaced with a conditional claim ladder: current extended-abstract claim, full-paper security claim, full-paper least-privilege claim, full-paper utility/recovery claim, and how to write negative outcomes.

- Related work matrix before edit: grouped closest work by family.
  After edit: changed it to concrete rows for CaMeL/IFC, AuthGraph, PACT, AIRGuard, SkillGuard/SkillScope, Progent/PCAS/AgentSpec, ActPlane, and IntentCap. Also changed IntentCap lowering wording from "all adapters" to "multi-boundary contract."

- Related work prose before edit: said equivalence would mean accepting IntentCap's boundary, which could read circular.
  After edit: softened to: if a baseline implements the same transaction object, the result is semantic equivalence and the paper's claim becomes identifying and evaluating that transaction boundary.

## Verification

Compiled from `docs/autopaper` with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex
```

Checked the log for undefined citations, undefined references, and overfull boxes. No matching warnings remained; only underfull table-line warnings remained.

## Remaining Concerns

- The next actual research work is experimental, not primarily writing: workload characterization, strongest composite baseline, and fuller adapter/provenance-proof measurements.
- Since Round 2c no longer found an easy conceptual novelty rejection, the idea-refinement process can move to Round 3 contributions and goals.
