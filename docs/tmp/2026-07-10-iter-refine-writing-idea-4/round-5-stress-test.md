# Iter Refine Writing Idea Round 5: Reviewer Stress Test

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 5 reviewer stress test.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Schrodinger`.

## What Was Checked

The subagent tried to construct the strongest OSDI/SOSP/NeurIPS-systems reject argument against the current idea framing. The review focused on whether IntentCap still reads as a predicate bundle over provenance/capabilities/stateful policy, whether the system claim exceeds the local prototype evidence, whether E2 depends too much on author-adjudicated labels, and whether the paper over-implies utility or production MCP/ActPlane integration.

## Findings

Overall judgment: weak-reject risk for a full top-conference systems paper if submitted as a complete agent authorization system today. The idea framing is now clearly stronger than "permission system for tools/MCP" and no longer centered on EIM/bpftime or ActPlane. The main risk is evidence maturity: the strongest reviewer can still describe the current paper as a well-scoped interface/model plus local probes rather than a fully validated agent security system.

Strongest reject argument:

> IntentCap frames agent security as an owner-typed pre-effect commit record. This is reasonable, but it may be a composition of provenance, capabilities, stateful policy, delegation checks, and pre-effect guards. The paper admits that another policy DSL or provenance runtime converges to IntentCap if it exposes the same fields and atomic update. Evaluation relies on author-defined owner labels, controlled counterexamples, local adapters, and replay diagnostics, while missing independent labeling, real end-to-end utility, production MCP/ActPlane/subagent integration, and approval-burden evidence.

Must-fix findings:

- Clarify whether the main claim is a minimal protected-decision authorization interface or a usable complete agent security system. If it is the latter, the paper needs a primary end-to-end utility/security experiment.
- Strengthen the equivalence boundary as an interface theorem/runtime ABI: protected-decision transition is the minimal authority-state linearization point; package-time, flow-time, action-time, and OS-time checks alone leave same-shape false accepts.
- E2 owner necessity still depends on author-adjudicated labels. Stronger wording needs blinded second-pass labeling, independent adjudication, inter-rater agreement, ambiguous-rate reporting, and a label artifact.
- E3 is still local prototype evidence: fake MCP-style broker, bubblewrap contrast, local prompt/delegation adapters. Production MCP, real prompt/subagent runtime, or ActPlane/eBPF integration would be needed for a stronger system deployment claim.
- Utility/recovery evidence is not yet a primary utility claim. The 5-task slice remains weak, so the abstract/intro should not imply benchmark-scale preserved utility.
- Context labeler is in the TCB; the paper must make clear it is not hiding semantic interpretation. Labeler should be channel/origin/issuer canonicalization, with semantic endorsement only from trusted issuer/policy/signed source/fresh approval.

Should-fix findings:

- Eventually rename the formal `agent` owner to `intent`, `root`, or `issuer` to avoid LLM self-authority confusion.
- Keep low task-loop utility numbers in diagnostics rather than presenting them as primary utility evidence.
- Keep E3 attempt counts as contract coverage, not scale evidence.
- Avoid saying runtime tool-result evidence "mints" authority; env evidence can only provide proof/value bindings that checker may use with intent-owned authority.
- Keep EIM/bpftime and ActPlane as backend/contrast, while treating CaMeL/AuthGraph/PACT/SkillGuard plus stateful policy as the dangerous closest abstraction.

Strong enough:

- Protected-decision transition as the authorization object should remain central.
- Four context classes as proof-owner projections, not component taxonomy, are a strength.
- Safe-merge, owner-equivalence, and lifecycle-equivalence should be strengthened rather than removed.
- E1/E2/E3 as the main spine is clearer than a run-led experiment narrative.
- Honest evidence boundaries should stay; next work should add evidence rather than inflate claims.

## Changes Applied

- Added a sentence after the contribution summary clarifying that the current main claim is a `minimal protected-decision authorization interface`, not a complete general-purpose agent security product.
- Expanded the TCB paragraph to define the context labeler as a channel/origin/signature/endorsement canonicalizer, not a semantic trust oracle. Default PDF text, tool results, stdout/stderr, subagent summaries, and unsigned Skill text remain env-owned cells.
- Updated the system overview to repeat that labeler behavior: only signed sources, trusted endorsement, or issuer confirmation can place an artifact into instruction/tool/intent-owned proof cells.
- Strengthened the Equivalence Boundary subsection with explicit runtime ABI language: package-time manifests, flow-time taint labels, action-time argument guards, and OS-time syscall monitors can be components, but none alone is the tested authority-state linearization point.
- Reworded runtime binding so tool-result evidence produces candidate value/proof bindings, not exact authority leases. Authority still requires intent-owned bounds, active leases, and checker approval.

## Remaining Concerns

The idea layer is now better scoped, but the strongest remaining evidence gates are empirical rather than rhetorical: independent owner-label adjudication for E2, at least one real vertical integration for E3, and a stronger end-to-end utility/recovery experiment before claiming a complete deployable agent authorization system.
