# Round 4: Cross-Alignment

Date: 2026-07-07

## What Was Checked

Problem statement, thesis, G1--G4 design goals, C1--C3 contributions, formal model, implementation boundary, and E1--E4 evaluation alignment.

## Findings

Subagent reviewer reported that the main spine now works:

> context influence -> intent-derived stateful lease lifecycle -> checker/runtime -> four claim-gated experiments.

Must-fix issues:

> E1/E2 still mix evaluation design with current run history.

> C2/G4 claim multi-boundary execution, while the implementation says full MCP broker and production sandbox are still open items.

> Protected decisions mention policy/capability request, but the formal event grammar does not expose these events.

> Influence modes and decision classes drift: `sink_select` appears like a mode, and `mode_d` is undefined.

## What Was Changed

- Calibrated C2 and G4: the paper now says \sys defines lowering contracts for context/tool/MCP/local/delegation boundaries, while the prototype implements checker/gateway, trace replay, local callable gateway, and benchmark-derived MCP/delegation adapters.
- Updated the abstract to distinguish design contracts from implemented adapters.
- Added `request(kappa, reason)` and `policy_update(patch)` to the formal event language.
- Clarified that capability requests and policy updates are protected decisions that cannot themselves mint authority; only a trusted issuer can produce a later `lease(kappa)` event.
- Separated `InfluenceModes` from `DecisionClasses`, and replaced the undefined `mode_d` in Property 1 with `req(d)`.
- Compressed E1/E2 so they read as hypothesis/baseline/metric/success-gate sections, with current pilot evidence moved to the evidence-status section.
- Added a current-evidence table summarizing what pilot results support and what they do not yet support.
- Added explicit E3 baseline semantics for object ACL, taint/IFC-style, action-provenance, stateful policy, and full \sys variants.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Remaining warnings are font and underfull table warnings from mixed Chinese/English prose, not compilation failures.

## Remaining Concerns

Round 5 should act as a final skeptical reviewer pass. The likely remaining risk is not idea incoherence, but whether a reviewer still thinks C3 is too proposal-like until more final measured evidence is available.
