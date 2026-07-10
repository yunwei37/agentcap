# Iter Refine Writing Round 2: Section Conventions

Date: 2026-07-10

Skill workflow: `iter-refine-writing`, Round 2 section conventions.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Hilbert`.

## What Was Checked

The subagent used `check-paper-structure-flow` with full-paper conventions and first read `iter-refine-writing/references/common-pitfalls.md`. The review focused on abstract structure, introduction roles, design-goal prose, evaluation setup, RQ alignment, subsection naming, related-work grouping, diagnostics placement, and conclusion structure.

## Findings

Must-fix findings:

- The abstract was still too mechanism-dense and had too many beats for a full-paper abstract.
- The design-goal subsection mixed design requirements with contribution and evaluation bookkeeping.
- The `授权输入` subsection still carried design explanation, formal safe-merge reasoning, examples, rebuttal material, and lease synthesis logic.
- The evaluation setup lacked a full systems-paper setup paragraph describing replay/live methodology, local model/backend metadata, and aggregation policy.
- E2 still reads like an adjudication ledger rather than a compact experiment section.
- Adapter proof-completeness audit detail interrupted the primary E3 boundary-enforcement spine.
- The conclusion was split into two paragraphs and contained limitation-style phrasing.

Should-fix findings:

- The Chinese technical base remains much longer than a submission-shaped 12--14 page main paper.
- The introduction needed a cleaner lead sentence before the contribution list.
- Background is thin and partly motivational.
- Subsection names mix English titles, Chinese titles, and claim-style experiment labels.
- The E1 Qwen slice is diagnostic rather than primary RQ1 evidence.
- Related work remains structurally right but sometimes defensive.

Consider findings:

- Prefer one primary term for the four context classes, such as `proof owner`.
- Centralize non-claim caveats in the discussion/limitations section.
- Keep diagnostics as appendix-style support rather than a fourth main result.

## Changes Applied

- Compressed the abstract to the canonical context/problem/system/results structure while preserving audited result anchors.
- Added a direct contribution lead sentence before the contribution list.
- Removed contribution/evaluation bookkeeping from `设计目标`; the subsection now states four testable goals and maps each goal to a mechanism, experiment, and falsifier.
- Compressed `授权输入` so it focuses on four proof-owner classes, why env is a separate class, and why component identity is not the authority unit. ABAC/rebuttal-style language was reduced and formal safe-merge details are pointed to the formal section.
- Added a systems-paper setup paragraph to `评估方法`, covering replay vs live diagnostics, no dataset sync, platform metadata, local Qwen/llama.cpp controls, digests, and aggregation source.
- Moved detailed adapter proof-completeness audit paragraphs from E3 into a new `Adapter Proof Completeness` diagnostic subsection. E3 now keeps only the contract-level proof-completeness conclusion.
- Renamed E1/E2/E3 subsection titles into shorter Chinese noun phrases.
- Merged the two-paragraph conclusion into one paragraph with thesis, mechanism, key result, and bounded takeaway.

## Remaining Concerns

E2 still needs a later compression pass: the field-owner adjudication protocol, natural-label packet, prior-derived composite baseline, and merge-coverage evidence are useful, but they should become appendix material in a submission-shaped draft. The current Chinese file remains a technical base rather than a 12--14 page main-paper cut. The E1 Qwen slice also still sits in E1 as a diagnostic paragraph; a later pass should either move it under Supporting Diagnostics or reduce it to one sentence.
