# Round 4: Cross-Alignment

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Cross-alignment of problem, insight, design goals, contributions, formal properties, and E1-E4 evidence after R220 and Round 3 scope edits.

Findings from the reviewer:
- The main story is mostly aligned: context controls future authority state; the right authorization unit is an issuer-typed protected-decision transition; four authority inputs and lease lifecycle realize the model.
- E3 remained the weakest support point because R220 could still look like a taxonomy-driven aggregate and R219 is a residual lift.
- R220's 8,691/8,696 multi-issuer number needed decomposition by decision class and basis.
- G4/architecture wording still risked implying full enforcement across instruction/delegation boundaries.
- E2 must remain auditability, not a least-privilege/expert-minimal claim.

What changed:
- Extended `scripts/characterize_authority_inputs.py` to emit `decision_class_characterization.csv`.
- Updated R220 artifacts with mode-level characterization: tool selection, authorization, sink selection, policy/delegation, and env/data modes.
- Added a compact E3 table summarizing decision class, dominant required issuer sets, env requirements, and substitution edges.
- Changed the architecture caption to say the transition API covers all boundaries, while the prototype fully enforces tool/local-env and validates instruction/delegation at trace level.
- Changed the evaluation contribution to three bounded claims: same-event protected-decision safety, issuer/lifecycle ablation necessity, and local pre-side-effect enforceability.
- Changed the evaluation overview so E2 is machine audit and structured policy-distance analysis, not least-privilege proof.
- Added an explicit mapping from E3 evidence to formal properties: R220 characterizes P1/P5 demand, residual suites test P1/P3/P4/P5 failures, and R219 tests tool-to-agent substitution.
- Clarified the ActPlane-style result as lowering a lease contract with issuer/provenance/influence predicates to an OS-monitor policy shape, not production ActPlane integration.

Remaining concerns:
- R220 is still derived annotation. A stronger version needs independent natural protected-decision labeling.
- Live instruction-placement and delegation enforcement remain future work.
- E2 still needs blinded independent expert replication before supporting expert-oracle least-privilege claims.
