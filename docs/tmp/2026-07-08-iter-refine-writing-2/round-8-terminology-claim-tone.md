# Round 8: Terminology And Claim Tone

Date: 2026-07-08

## What Was Checked

Applied the `paper-writing-style` terminology and claim-tone pass to `docs/autopaper/intentcap-paper-zh.tex`. The pass checked invented terms, terminology drift, unanchored absolutes, self-attacking sentences, and whether scope-bearing hedges were kept in the right sections.

## Findings

Must-fix findings:

- The same four-class concept was described as `proof-carrying input classes`, `authority-input classes`, `authority-input boundary`, and `proof-carrying system interfaces`.
- ActPlane/backend wording in the introduction and implementation still sounded like a project-status disclaimer.
- E3 baseline language said object/action guards and IFC/provenance guards “will fail,” which was too broad for the tested variants.
- `label packet`, `project-author first-pass`, and `counterexample lift` read like internal experiment names.
- Metrics mixed `dangerous accepts`, `unsafe accepts`, and `unsafe effects/placements`.

Should-fix findings:

- Use `protected-decision lease` as the main term after the initial `intent-carrying capability lease` definition.
- Move production-integration caveats out of the main claim path where possible.
- Define `env context` explicitly as shorthand for `env/runtime observation context`.
- Replace `closest baselines` with `baseline policies` or `baseline predicates`.
- Replace `ontology-level 最小分类证明` with a clearer bounded-taxonomy statement.
- Replace “模拟 \\sys” wording in related work with a neutral equivalence statement.

## Changes Made

- Unified the four-class terminology:
  - Before: `proof-carrying input classes`, `authority-input classes`, `proof-carrying system interfaces`.
  - After: `authority-input classes`, with each class described as a `proof-carrying issuer boundary`.

- Clarified the env term:
  - Added that `env/runtime observation context` is shortened to `env context` and is not Unix environment variables.

- Standardized result metrics:
  - `unsafe accept` now means the checker or baseline accepts a violating event.
  - `unsafe execution/placement` now means a local side effect or prompt placement actually occurs.
  - Replaced `dangerous accepts` and `unsafe effects/placements` in the abstract, E1, E4, and evidence table.

- Narrowed E3 baseline claims:
  - Before: “object/action guards、IFC/provenance guards 和 split-state counters 会失败.”
  - After: “在本文测试的 no-owner 和 split-state variants 中 ... 会 false-accept 某些事件.”

- Replaced internal experiment vocabulary:
  - `label packet` became `sampled protected-decision labels`.
  - `project-author first-pass` became `author-adjudicated labels`.
  - `counterexample lift` became `benchmark-derived counterexamples`.

- Toned down ActPlane/backend phrasing:
  - Main implementation now describes the `OS-monitor-style replay backend` as a reference lowering for local/env lease contracts.
  - Production ActPlane/kernel integration is left as an evidence requirement in the evidence-boundary and limitations sections.

- Related-work tone:
  - Replaced “它就在模拟 \\sys 的授权对象” with “it implements the same authorization object as \\sys for the covered fields and transitions.”

## Remaining Concerns

- Some strict negatives remain because they are formal no-substitution claims, not broad statements about prior work.
- Production integration caveats remain in `范围与局限`, where they protect the claim boundary.
- No quantitative results, citations, or theorem statements were changed.
