# 2026-07-10 Iter-Refine-Writing-Idea Round 5

## What Was Checked

Round 5 was a reviewer stress test over `docs/autopaper/intentcap-paper-zh.tex`.
Reviewer `019f4b71-043f-7170-836a-018fb85d9be2` tried to construct the strongest OSDI/SOSP-style rejection argument against the current framing, novelty, system contribution, evidence boundaries, and four-context model.

## Findings

Must-fix items:

- The core novelty could still be rejected as stateful ABAC/IFC/provenance plus leases.
- The four context classes could still look like a hand-tuned taxonomy, especially because instruction-context evidence is thinner than agent/tool/env evidence.
- Large numbers could be read as natural workload evidence even though many labels are artifact-derived, controlled, or author-adjudicated.
- The current system evidence is still a Python checker plus local adapters and replay lowering, not production MCP/prompt/subagent/ActPlane integration.
- The top-level context-influence story and the measured owner-substitution/lifecycle metrics were not perfectly aligned.

Should-fix items:

- E1 utility proxy should be described as representability/reference-action coverage, not utility preservation.
- Baselines should be separated into implemented wrappers and interface-derived removal studies.
- Trusted issuer, labeler, and provenance tracker are in the TCB and need a clearer proof API / fail-closed story.
- General "necessary" language should be narrowed to tested removal families.
- ActPlane wording should avoid creating expectations of a real kernel or ActPlane integration.

## Changes Made

- Reframed the abstract and introduction around an agent-specific authority transition interface: issuer-owned field proofs, checker-owned lease state, and same-transition lifecycle mutation.
- Changed the contribution list from a "four-proof-owner" model to a per-field owner lease model, with agent/instruction/tool/env as the current prototype instantiation.
- Changed the authorization-input section to state that the general model is per-field owner; the four classes are a prototype owner set derived by safe merge over the current workloads and adapter surfaces.
- Changed the formal `Solve` judgment from a fixed four-context tuple to an owner-set formulation \(\{\pi_o(C_o)\}_{o\in\mathcal{O}}\), then instantiated \(\mathcal{O}=\{agent,inst,tool,env\}\) for this prototype.
- Rewrote the evaluation opening so E1 is a representability/sanity gate, not an end-to-end utility claim.
- Split baselines into implemented wrapper baselines and interface-derived removal/counterfactual predicates.
- Renamed E2 from a broad necessity experiment to an issuer-collapse and lifecycle-split removal study.
- Reworded the related-work interface table from "equivalent" language to "default runtime object / missing fields" language.
- Narrowed the evidence-boundary table from general necessity to counterexamples under tested removals and explicitly identified the `3,593/3,823` result as an artifact-derived ablation set.

## Remaining Concerns

The strongest remaining blockers require experiments rather than wording:

- A production-like vertical slice with real MCP-style broker, shell/script execution, prompt placement, subagent handoff, and sandbox/ActPlane-style backstop.
- Blinded second-pass field-owner labeling with disagreement reporting.
- A live paired data/control injection experiment that allows the same untrusted context as data while denying it as sink/approval/delegation control.
- A task-level utility/recovery run with success, false denial, approval burden, and recovery metrics.
