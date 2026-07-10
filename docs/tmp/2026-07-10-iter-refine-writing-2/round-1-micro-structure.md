# Round 1 — Micro Structure

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `iter-refine-writing`, Round 1. The review subagent was instructed to use `check-paper-structure-flow` with Level 2 paragraph roles and Level 3 paragraph-internal flow, after reading `iter-refine-writing/references/common-pitfalls.md`.

## What Was Checked

- Abstract sentence roles and abstract/intro correspondence.
- Introduction paragraph roles and causal order.
- Topic sentences and one-idea-per-paragraph flow.
- Why-before-what structure in design paragraphs.
- Whether evaluation subsections answer RQs rather than read as a ledger.
- Whether limitations and related work carry the right paragraph roles.

## Reviewer Findings

Must-fix findings:

- Abstract had the right broad beats but the system beat was too implementation-heavy. It debuted five local/replay boundary classes, non-TCB details, and exclusions before the main result.
- Abstract terminology did not mirror the introduction: abstract emphasized boundary classes, while the intro emphasized four proof owners and authority-state commit.
- Introduction had the required roles but too many rebuttal/equivalence-boundary paragraphs before the system insight.
- The root-cause paragraph contained root cause, failure modes, interface requirements, four owners, and a definition in one paragraph, with bold run-in labels.
- `授权输入` was doing design rationale, taxonomy derivation, formal safe-merge, E2 preview, and anti-baseline argument at once.
- Several design paragraphs opened with component definitions instead of the failure they prevent.
- Evaluation still had ledger-like flow; E1 opened by saying it excluded a failure mode rather than directly answering RQ1.
- Boundary statements were repeated in several sections.

Should-fix findings:

- Background/motivation still mixes neutral substrate explanation with preliminary design evidence.
- System overview walkthrough should appear directly after the architecture figure.
- Formal model should start with positive invariants rather than negative scope.
- Evaluation setup should separate primary experiments from diagnostics.
- Related work should start with narrative before the heavy interface-audit table.

## Changes Made

1. Abstract:
   - Rewritten from 10 implementation-heavy sentences to 8 sentences following context/problem/system/mechanism/result roles.
   - Removed the five-boundary implementation taxonomy from the abstract.
   - Aligned abstract terminology with the intro: protected decisions, pre-effect authority-state transition, four proof-owner classes, deterministic checker, E1/E2/E3 evidence.

2. Introduction:
   - Collapsed rebuttal/equivalence-boundary paragraphs.
   - Split the root-cause material into root cause and four-owner consequence.
   - Removed bold run-in failure labels from the root-cause paragraph.
   - Kept the intro as background, problem example, root cause, owner consequence, existing approaches, insight, challenges/system, evidence/contributions.

3. Design paragraph flow:
   - Rewrote `意图证书` opening to start from authority-root collapse.
   - Rewrote `上下文影响权限` opening to start from the need to preserve legal data use while blocking authority use.
   - Rewrote `Effect IR 与 Leases` opening to start from the checker's need to see safety-relevant effects before protected fields are submitted.
   - Rewrote `Compiler 与 Checker` opening to start from the boundary that LLM planning must not become authority issuing.

4. `授权输入`:
   - Removed the E2-preview paragraph that directly explained the tested-removal contract, because E2 already carries that role.

5. Formal model:
   - Rewrote the opening paragraph positively around the formal object and moved model boundary to the end of the paragraph.

6. Evaluation:
   - Labeled E1--E3 as primary experiments and diagnostics as non-claim supporting material.
   - Rewrote E1's opening to answer RQ1 directly.

## Remaining Concerns

- Introduction is much shorter but still has 11 paragraph blocks if the contribution list and follow-up contribution explanation are counted separately.
- `授权输入` still contains a formal equation and safe-merge details; a later round should decide whether to move them to the model section.
- E2 remains table-heavy and has several sub-experiments in one subsection.
- Boundary statements are less prominent in abstract/intro but remain frequent in E3 and limitations. A later tone pass should keep only those needed to prevent overclaiming.
- Related work still opens with a heavy comparison table before the narrative groups.
