# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 2b defense against the ABAC/provenance novelty attack.

## Changes made

- Introduction, strongest-baseline paragraph: rewrote the stateful provenance/ABAC comparison so the paper no longer argues that such monitors lack Boolean expressiveness. The new claim is that the runtime must expose a single pre-effect authority-state object.
- Introduction: added the required object fields explicitly: concrete effect, issuer-owned field proofs, active lease version, and consume/delegate mutation.
- Introduction: added the failure mode for split checks: provenance and budget guards can each be locally correct while still allowing double-consume or over-delegation if lifecycle state is not linearized.
- Problem Characterization: changed the characterization sentence from "由问题本身导出" to "counterexample-backed design support" to avoid implying natural prevalence or independent workload evidence.
- Formal model: inserted an explicit checker rule using \(owner(f)\), \(\mathsf{proof}_{owner(f)}(f,\Phi_e)\), \(Req(d)\), \(Accept(e,\sigma,\kappa)\), and a commit rule that binds the concrete effect, lease version, field proofs, lifecycle mutation, and next checker state.

## Remaining concerns

- The evaluation section already states three claim questions, but the long evidence-boundary table may still read like a ledger. A later writing round should decide whether to move diagnostic rows out of the main narrative.
- The OS/bubblewrap contrast is present in limitations and related work, but a compact comparison table may still help if the next re-attack says ActPlane remains too central.
