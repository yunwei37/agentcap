# Round 5: Consistency Audit

Date: 2026-07-08

## What Was Checked

Consistency between abstract, introduction, contribution bullets, four-plane design, formal model, evaluation claims, evidence table, related work, and conclusion in `docs/autopaper/intentcap-paper-zh.tex`.

## Findings

Must-fix items addressed:

- The abstract, intro, and conclusion used broad result wording for three different evidence sources. They now distinguish saved security traces, tau2/tau3 reference-action proxy, and local env probes.
- C2 implied production-grade tool/MCP and local-env gateway coverage. It now states the implemented checker core, live tool/local callable gateway, local env pre-side-effect probes, trace-level instruction/delegation contracts, and ActPlane-style env lowering contract.
- G4 mixed side-effect transaction enforcement with recovery. The goal row now only claims that adapters call the checker before side effects or authority transfer.
- The local-Qwen evidence row used ambiguous "fresh online" wording. It now says local-Qwen trajectory slice and reports it as a utility boundary rather than benchmark-scale recovery.
- The paper used abstract influence modes and concrete trace mode names without explaining the mapping. The context-authority section now defines influence mode, decision class, and decision mode, and maps quote/summarize/parameterize, plan/instruct, authorize, and delegate to concrete protected-decision fields.
- E3 now states the R217 controlled residual result directly: 2 legitimate workflow events execute and 7 residual violations are blocked by IntentCap, while closest labelers accept all 9.

Should-fix items addressed:

- Added the missing clarification that raw user text is not a fifth plane. The trusted issuer partitions it into agent-owned intent fields and instruction-owned workflow preferences.
- E1 now includes the local-Qwen trajectory slice in the evaluation matrix but keeps it separate from same-event safety and reference-action feasibility.
- Related work now uses completed, scoped evaluation wording rather than future-obligation wording.
- The conclusion now repeats the same scoped result wording as the abstract and intro.

## Changes Made

- Abstract result sentence:
  - Before: "0 dangerous accepts on 3,746 protected events" and "preserves all 3,813 benign reference actions" as one broad prototype result.
  - After: saved security traces admit 0/3,746 dangerous protected events; tau2/tau3 reference-action proxy covers 3,813/3,813 benign assistant actions and passes 2,554/2,556 applicable replay oracles; local env probes block scripted and Qwen3.6 unsafe calls before side effects.

- Contributions and goal map:
  - Before: C2 said implemented tool/MCP and local-env gateways, and G4 included recovery.
  - After: C2 is bounded to implemented checker/gateway/probe surfaces plus trace-level contracts and ActPlane-style lowering; G4 is bounded to pre-side-effect and pre-transfer checking.

- Four-plane model:
  - Before: the text explained agent/instruction/tool/env classes but did not explicitly state what happens to raw user text or how abstract modes map to trace fields.
  - After: user text is partitioned by the issuer; influence mode, decision class, and decision mode are separated; implementation mapping is stated in the Context Authority subsection.

- Evaluation:
  - Before: E1/E4 language could be read as utility/recovery evidence.
  - After: E1 is safety/reference-action/trajectory-boundary evidence; E4 is transaction API and local env practicality; benchmark-scale recovery and approval burden are left as separate claims.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- Warning scan for undefined citations/references, LaTeX warnings, and overfull boxes returned no matches.
- `git diff --check` passed.

## Remaining Concerns

- The prose still mixes Chinese and English heavily. Round 6--9 should improve sentence structure, word choice, terminology, and flow without changing numbers.
- The main evidence is still bounded. Stronger top-conference claims require benchmark-derived residual lift, independent expert-oracle lease review, and stronger end-to-end utility/recovery evidence.
