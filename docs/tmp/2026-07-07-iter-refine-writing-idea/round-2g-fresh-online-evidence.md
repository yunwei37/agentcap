# Round 2g: Fresh Online Evidence Update

Date: 2026-07-07

## What Was Checked

The paper had already reframed IntentCap around four authority inputs: agent context, instruction context, tool context, and env context. This update checked whether the fresh local Qwen/llama.cpp all-tool exposure run changes the E1 evidence boundary and whether the Chinese paper explicitly says why the four classes cannot collapse into three.

## Findings

- The four-context boundary needed one stronger explanatory paragraph: instruction must not become agent intent, tool metadata must not collapse into env observations, and env outputs must not become instruction merely because they contain imperative text.
- The formal model already used `Solve_\Gamma(C_{agent}, C_{inst}, C_{tool}, C_{env})`; it needed a clearer checker-facing projection statement for intent/procedure/interface/evidence fields.
- R209E1ALL provides a fresh local online all-tool comparison against the prior R197 leased run on the same 11 tau2 tasks and local Qwen/llama.cpp configuration family.

## Result Added

R197 leased exposure:

- tasks: 11
- average visible tool schemas: 4.27
- gateway blocks: 0
- off-lease blocks: 0
- missing-value-proof blocks: 0
- bound-reference calls: 51
- all-reference-executed/action-reward tasks: 8/11
- exact-sequence tasks: 6/11
- official tool-oracle tasks: 0/11

R209E1ALL all-tool exposure:

- tasks: 11
- average visible tool schemas: 14.73
- gateway blocks: 3
- off-lease blocks: 2
- missing-value-proof blocks: 1
- bound-reference calls: 49
- all-reference-executed/action-reward tasks: 8/11
- exact-sequence tasks: 6/11
- official tool-oracle tasks: 0/11

## Interpretation Boundary

This is a useful fresh online slice, not a benchmark-scale utility result. The result supports the narrow claim that broader tool exposure does not automatically improve task progress and can introduce more checker-visible overreach/missing-proof events. It does not yet prove end-to-end utility preservation, recovery success, or final E1 security dominance.

## Paper Changes

- Added a paragraph in `docs/autopaper/intentcap-paper-zh.tex` explaining why four context classes cannot be collapsed into three.
- Added projection functions for the formal four-input checker model.
- Added the R197/R209 evidence row and claim-boundary caveat in the Chinese paper.
