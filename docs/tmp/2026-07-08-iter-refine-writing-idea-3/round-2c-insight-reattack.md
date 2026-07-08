# Round 2c: Insight Re-Attack

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Idea-quality checklist Section 2: whether the revised issuer-typed protected-decision framing still looks like a generic policy DSL plus provenance.

Findings from the skeptical reviewer:
- Strongest remaining rejection argument: IntentCap may still look like a well-engineered policy DSL combining intent, provenance, capabilities, budgets, expiry, and delegation unless the paper proves issuer-typed protected-decision transitions are a necessary abstraction.
- The four-class model is sharper than ordinary taint/IFC/action guards, but it risks seeming author-defined if the only evidence is controlled residual cases that match the taxonomy.
- E3 needs a natural or benchmark-derived characterization of protected decisions that require agent/instruction/tool/env issuer boundaries.
- The paper must distinguish "prior systems do not make this the default authorization object" from "prior systems cannot encode this policy."
- The implementation contribution should separate implemented tool/local-env boundaries from trace-level instruction/delegation boundaries.
- E2 remains too weak for a strong expert-oracle least-privilege claim.

What changed:
- Added `No issuer substitution` as an explicit safety property in the formal model.
- Renamed E3 to `Authority-Input Characterization and Mechanism Ablation`.
- Added R220 authority-input characterization using existing local artifacts only: local env suite, residual workflow-policy suite, AgentDojo, MCPTox, InjecAgent, tau2-style traces, and R136 runtime-binding summary.
- Reported R220 as trace-level derived annotation: 8,696 events, 8,691 requiring multiple issuer classes, 198 requiring env issuer, and 3,593 checker-denied events exposing class-substitution attempts.
- Added R220 collapse edges: tool -> agent 1,928, env -> agent 1,663, env -> tool 1,662, instruction -> agent 2.
- Added R136 runtime-binding evidence in the E3 narrative: 29/29 runtime-binding successes and 25 runtime-evidence hint steps.
- Updated the current-evidence table with a dedicated R220 row.
- Updated limitations to state that R220 is not a blinded natural-decision label study.

Remaining concerns:
- R220 is still derived annotation, not independent expert labeling.
- Strong top-conference least-privilege claims still need blinded expert-oracle lease scoring.
- Strong utility claims still need a larger online user-simulator/recovery experiment.
- Instruction placement and delegation need stronger implemented-boundary evidence if the paper wants to claim full cross-boundary enforcement rather than checker semantics plus trace-level coverage.
