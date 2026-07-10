Date: 2026-07-10

What was checked:
- Follow-up to the macro-structure review, focused on whether the Chinese paper presents IntentCap as a system contribution rather than only a model.
- Inspected `src/intentcap/checker.py`, `src/intentcap/gateway.py`, `src/intentcap/live_gateway.py`, `src/intentcap/boundary_gateway.py`, `scripts/lower_env_leases_actplane.py`, `scripts/run_integrated_workflow_probe.py`, and `scripts/analyze_multiboundary_system_evidence.py`.
- Checked whether the four context classes are framed as owner-equivalence proof boundaries rather than arbitrary terminology.

Findings:
- The paper already explains agent, instruction, tool, and env as four authority-input classes, but the opening of the design subsection could make the "four not three" claim sharper.
- The implementation section described contract surfaces but did not map them to concrete code paths, making the system contribution harder to audit.
- The ActPlane-related wording remains correctly bounded as an env/OS-monitor-style lowering target, not a production ActPlane integration.
- A read-only subagent review found two must-fix issues: E2 needed a visible three-class merge coverage matrix or a narrower claim, and the boundary-owner table described delegation as Agent+Env while the formal decision-requirement table treated delegation as a compound protected decision over four field families.

Changes made:
- In `docs/autopaper/intentcap-paper-zh.tex`, revised the authorization-input opening to define the four classes as an owner-equivalence partition over four proof questions: run authorization, endorsed procedure, callable interface, and runtime observation.
- Added explicit text explaining why tool and env cannot be merged: tool schema is a pre-execution interface promise, while env evidence is a runtime observation that can only bind already-authorized predicates.
- Added an implementation code-path table mapping checker, replay gateway, live gateway, boundary gateway, ActPlane-style lowering, integrated workflow probe, and paper-evidence audit scripts to the paper claims they support.
- Updated the delegation row in the owner-class table to state that handoff is not a fifth owner and is instead a compound decision over agent, instruction, tool, and env fields.
- Added a three-class merge coverage matrix in E2. The matrix reports tested aggregate collapse families, the local env-to-instruction Skill placement counterexample, and explicitly marks instruction+tool as not separately isolated, so the paper no longer overclaims exhaustive proof over all possible three-class partitions.
- Moved the raw-user-text canonicalization explanation earlier in the authorization-input subsection and added an E3 scope sentence stating that E3 is adapter feasibility, not owner minimality.

Remaining concerns:
- This is a writing/system-story refinement, not a new experiment.
- Stronger claims still require production MCP/prompt/subagent integration, kernel/ActPlane mediation, independent expert labeling, and benchmark-scale utility/recovery evidence.
