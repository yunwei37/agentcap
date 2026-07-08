# Round 2d: Repeated Insight Re-Attack

Date: 2026-07-08

## What Was Checked

A second read-only reviewer re-attacked `docs/autopaper/intentcap-paper-zh.tex` after commit `2671e2e`, focusing on whether the new multi-issuer commit protocol framing still looks like ordinary provenance/IFC plus capabilities, typestate counters, and a policy DSL.

## Findings

The revised framing is stronger than a tool/MCP guard and gives the idea a clearer center. The remaining top-conference rejection risk is evidence, not the basic idea: reviewers can still argue that the paper has described a stateful policy schema unless it shows that ordinary collapsed/provenance variants false-accept real or benchmark-derived protected decisions and that adapters can reliably produce required field proofs.

Must-fix findings:

- Strengthen the system-interface claim: the important object is the pre-side-effect field-proof commit plus atomic consume/update obligation at each adapter boundary.
- Add an E3 natural/benchmark-derived ablation table: Full IntentCap, no-owner, collapsed-context, and split-lifecycle should report unsafe protected-decision false accepts on existing traces, not only controlled examples.
- Add an adapter proof-completeness/attribution audit: for each boundary, report complete required-field proofs, missing-proof denials, and owner/substitution checks.
- Keep E4 bounded as local adapter feasibility unless a real ActPlane/kernel or production-like prompt/MCP/subagent runtime experiment is added.

Should-fix findings:

- Repeat the concise insight sentence: "Agent authorization should be a pre-effect multi-issuer commit protocol over authority-state transitions, not a post-hoc filter over completed actions."
- Prefer "issuer boundaries" over "context classes" where possible.
- State that no-owner/split-state variants represent natural collapsed baselines, not full reproductions of named policy systems.

## Resulting Plan

The next work items are:

1. Build an E3 weak-variant ablation over existing R220/R221 authority-input annotations.
2. Build an adapter proof-completeness audit over E4 boundary artifacts and existing trace annotations.
3. Update the Chinese paper and evaluation plan with these results if the audits produce clean, claim-facing numbers.
4. Run another novelty re-attack after those results are integrated.

## Remaining Concerns

Current wording is much closer to a top-conference claim, but a likely reject remains if E3/E4 stay at controlled examples and local replay only. The next evidence should be claim-facing rather than another prose-only revision.
