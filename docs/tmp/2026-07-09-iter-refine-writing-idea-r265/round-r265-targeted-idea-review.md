# R265 Targeted Idea Review

Date: 2026-07-09 America/Vancouver

## What Was Checked

Target file: `docs/autopaper/intentcap-paper-zh.tex`.

Scope: idea-layer and claim-scope review for the R263/R264/R265 closed-loop recovery evidence that was newly integrated into the Chinese paper. The check focused on whether the blinded-candidate recovery result is framed as bounded diagnostic evidence rather than as end-to-end utility or natural recovery.

## Reviewer Findings

Subagent reviewer: Franklin.

Must-fix:

- Line 730 used `labels`, which could be read as oracle labels. The correct meaning is context/provenance labels. The text should explicitly say no expected-outcome/oracle labels are provided.
- Line 730 said checker feedback can guide blocked unsafe proposals to narrow authorized alternatives. Without no-feedback/generic-feedback ablations and with pre-enumerated candidate events, this is a causal overclaim. The result shows structured denial is actionable in the constrained harness, not that feedback alone causes recovery.

Should-fix:

- R263/R264/R265 were placed in E1, whose primary role is reference-action coverage / expressiveness. They should be framed as a supporting recovery diagnostic rather than an E1 primary metric.
- The blinded-candidate scope should state that R264/R265 only hide candidate IDs and descriptions; event fields, tool names, operation names, and provenance scaffold remain semantic.
- In the evidence-boundary table, the row title `Closed-loop utility and recovery remain preliminary` makes a preliminary result look like a supported claim. Rename the row to a bounded diagnostic claim.

Consider:

- Add no-feedback/generic-feedback/candidate-only ablations as missing evidence before attributing recovery to structured denial feedback.
- Make clear that R265 is an output-budget sensitivity run, not a same-budget reproduction of R264.

## Changes Made

- E1 recovery paragraph: changed the opening from an E1 add-on to `作为 E1 主指标之外的 supporting recovery diagnostic`.
- E1 recovery paragraph: changed `labels` to `context/provenance labels` and added that no expected-outcome/oracle labels are shown.
- E1 recovery paragraph: added that blinded mode hides candidate names/descriptions only, while event fields and provenance scaffold remain semantic.
- E1 recovery paragraph: changed R265 wording to `output-budget sensitivity run`.
- E1 recovery paragraph: replaced causal feedback wording with a bounded statement: in a controlled harness with enumerated candidate actions and visible lease/event/provenance scaffold, structured denial does not necessarily force abort; this does not isolate feedback's independent causal contribution or prove free-form replanning recovery.
- Evidence-boundary table: renamed the row from `Closed-loop utility and recovery remain preliminary` to `Structured denials are actionable in a constrained recovery diagnostic`.
- Evidence-boundary table: added missing evidence for no-feedback/generic-feedback/candidate-only ablations.

## Remaining Concerns

- The recovery diagnostic still uses hand-written tasks and enumerated candidate actions.
- R265 improves output budget rather than reproducing R264 under the same budget.
- The result should remain supporting evidence only until benchmark-derived recovery, approval burden, and free-form replanning experiments are run.
