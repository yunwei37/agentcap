# Round 3 - Contributions and Design Goals

Date: 2026-07-09

## What Was Checked

Read-only review of contribution statements, design goals, and goal-to-evaluation mapping in `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`, using `iter-refine-writing-idea` checklist Section 3.

## Findings

The reviewer found the main story aligned with the refined insight: the authorization granularity is a multi-issuer, lifecycle-mutating protected-decision transition exposed as a pre-effect runtime linearization object.

Must-fix items:

1. The contribution list still read partly like an artifact/evidence summary. It needed four one-sentence contributions ordered as model, runtime contract, system, and evidence.

2. The goal map connected goals to experiments but not explicitly to contributions. It needed a `Contribution` column so reviewers can trace G1/G2 to C1, G3 to C1+C2, G4 to C2+C3, and the guardrail to C4.

3. The `Guardrail` row used "utility/expressiveness" even though the paper does not currently claim benchmark-scale utility improvement. It needed to say reference-action coverage / expressiveness.

4. The typed-provenance convergence baseline was not visible in the goal map. G3/G4 needed a falsifier that names same-transition parent-child lease comparison and child-state update.

Should-fix items:

1. Distinguish G3 as semantic lease-state mutation from G4 as system exposure across boundaries.

2. Later writing rounds should reduce repeated context-class tables.

3. The evaluation opening should explicitly say E3 is the core mechanism experiment, E4 is the system-interface experiment, and E1/audit are guardrail/supporting evidence.

## What Was Changed

1. Lines 86--90 were rewritten into four tighter contributions: Model, Runtime contract, System, and Evidence.

2. G3 and G4 were separated: G3 is atomic lease-state mutation, while G4 is multi-boundary transition exposure.

3. Table `goal-map` now includes a `Contribution` column and maps goals to C1/C2/C3/C4.

4. The guardrail row now says reference-action coverage / expressiveness, not utility.

5. The G3 falsifier now names the typed-provenance convergence condition: a strong baseline lacking same-transition parent-child lease comparison or child-state update can false accept; adding them implements C2.

6. The evaluation opening now states E3 is the core mechanism experiment, E4 is the system-interface experiment, and E1/supporting audit are guardrail evidence.

## Remaining Concerns

Table redundancy and related-work table tone remain writing-level issues for the later `iter-refine-writing` rounds. Independent expert labels, benchmark-scale utility/recovery, and production ActPlane/kernel enforcement remain evidence gaps and are not current top-level claims.
