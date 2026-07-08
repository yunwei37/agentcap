# Round 4: Abstract / Intro Rebuild

Date: 2026-07-08

## Mapping Diagnosis

Abstract sentence roles:

- S1: context, LLM agents as extensible execution environments.
- S2: context/problem bridge, extensions influence future authority-bearing decisions.
- S3-S4: problem and consequence, existing permission mechanisms cannot say which context may control a protected decision.
- S5-S7: this paper, protected-decision leases, four issuer-owned context classes, deterministic checker, and implemented boundaries.
- S8-S10: results for protected-event safety, issuer-collapse/lifecycle ablations, and multi-boundary enforcement.

Intro paragraph roles:

- P1: background/context.
- P2: concrete problem example.
- P3: structural root cause.
- P4: four proof boundaries as the key insight.
- P5-P6: existing approaches and why action/provenance checks alone are insufficient.
- P7-P9: this paper and mechanism overview.
- P10: bounded evidence.
- P11: contribution list.

The optional root-cause paragraph is warranted because the paper's core claim answers issuer collapse and authority-state split. The optional challenge paragraph is effectively folded into P7-P9: the challenge is realizing the insight across tool/MCP, instruction placement, env/runtime, and delegation boundaries without trusting the LLM.

## Reorganization Plan

No large intro rewrite was needed after Round 3. The intro already follows the causal chain:

background -> concrete failure -> root cause -> four-boundary insight -> limitations of existing approaches -> protected-decision lease model -> implementation/checker -> bounded evidence -> contributions.

The one issue was abstract style: the result sentences used internal experiment labels `E1`, `E3`, and `E4`. Those labels make the abstract read like an evaluation ledger and introduce terms before the evaluation section. The fix was to rewrite the result sentences as claim-facing results: protected-event replay, issuer-collapse/lifecycle ablations, and local multi-boundary probes.

## Changes Made

- Replaced `E1/E3/E4` labels in the abstract with direct result descriptions:
  - protected-event replay: 0/3,746 dangerous accepts and 3,813/3,813 reference-action coverage;
  - issuer-collapse/lifecycle ablations: weak variants accept substitutions/promotions/reuse violations that \sys rejects;
  - local multi-boundary probes: 0 unsafe effects/placements across 38 attempts and 0 checker/monitor mismatches in the ActPlane-style lowering target.

## Self-Check

- Abstract follows context -> problem -> this paper -> results.
- Every abstract mechanism term appears in the intro: protected-decision lease, four issuer-owned context classes, deterministic checker, prompt placement, delegation, local/env boundary, ActPlane-style target.
- Every abstract number appears in the paper body.
- No citation count changed.

## Open Items

- The intro is still long because the paper is currently a full-paper draft rather than a two-page extended abstract. Further tightening belongs to later language/flow rounds, not this structural rebuild round.
