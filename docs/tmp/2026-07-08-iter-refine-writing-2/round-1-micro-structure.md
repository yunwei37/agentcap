# Round 1: Micro Structure

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Skill workflow: `iter-refine-writing`, Round 1 micro-structure.

## Findings

The read-only micro-structure review found that the paper still mixed paragraph roles in several places:

- The abstract carried too many result details and read like a mini evidence ledger.
- The introduction bundled implementation scope, evidence status, and the central insight in one paragraph.
- The authority-input subsection repeated the four-class argument instead of presenting a clean definition, rationale, and formal hook.
- E3 was too run-ledger-like and should be organized around the claim that issuer-owned fields and atomic lifecycle checks are necessary.
- The Evidence Boundary table listed artifacts rather than claim-facing evidence and missing evidence.

## Changes Made

- Rebuilt the abstract into the four expected beats: context, problem, system, and bounded results. It now keeps only the highest-signal numbers and moves detailed Qwen/env evidence to E4.
- Split the introduction into separate roles: closest-gap paragraph, field-owner challenge paragraph, system paragraph, evidence-boundary paragraph, and contribution list.
- Rewrote `授权输入` around the four system proof interfaces. The section now explicitly answers why three semantic sources are insufficient and why env/runtime is required for execution-time facts.
- Added a formal hook in `授权输入`: \(C=C_{agent}\uplus C_{inst}\uplus C_{tool}\uplus C_{env}\), with \(Solve_\Gamma\) described as a conjunction over owner-typed proof sets rather than a permission union.
- Reworked E3 into trace characterization plus controlled residual stress tests, with run IDs moved into sentence-end provenance rather than paragraph subjects.
- Replaced the large artifact-summary Evidence Boundary table with a claim-facing table: supported claim, current evidence, and missing evidence for stronger claims.
- Tightened the conclusion so it states the object shift, the IntentCap unit, current evidence boundary, and next evidence requirements without replaying all numbers.

## Remaining Concerns

- The paper still needs independent field-owner adjudication, closed-loop utility/recovery, and production adapter evidence before it can support a full top-conference systems claim.
- Later writing rounds should reduce English/Chinese term density and check table widths after LaTeX compilation.
