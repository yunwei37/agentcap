# Round 2c: Insight Re-Attack

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 2 re-attack after defense edits.

## Re-Attack Question

Can a skeptical reviewer still dismiss the paper as "ABAC + IFC/provenance + stateful capability counters applied to agents"?

## Current Assessment

The strongest version of that attack is now much weaker. The draft no longer frames the contribution as richer tool permissions or richer provenance labels. It states that the authorization unit is an intent-minted protected-decision transition that changes future authority state. This is repeated in the abstract, introduction, contribution list, formal model, lifecycle rules, E3 design, and related work.

The four context classes are also no longer just a taxonomy. They are now formal authority planes:

- `agent` supplies intent, selected objects/sinks, approvals, workflow state, and delegation root.
- `instruction` supplies procedure guidance and workflow scope.
- `tool` supplies interface/schema/credential/sandbox descriptors.
- `env` supplies observed runtime facts, values, files, tool results, script outputs, and resources.

The formal model uses `Solve_Gamma(C_agent, C_inst, C_tool, C_env)`, projection functions, `Req(d)=<A_d,I_d,T_d,E_d>`, and a no-promotion invariant. The key rule is missing-field fail-closed: one plane cannot fill another plane's required field. This is the point that prevents collapsing four planes into three.

## Remaining Reviewer Risks

1. Evidence risk remains higher than idea risk. The paper still needs the planned E3 benchmark-derived residual lift to show that no-promotion/lifecycle violations occur in realistic workflows, not only controlled suites.
2. E2 least-privilege claims remain limited until independent human replication exists. Author-adjudicated labels are useful but cannot be presented as independent expert oracle evidence.
3. Env/ActPlane-style coverage is currently a local pre-side-effect backend plus model-loop probe. The paper correctly frames ActPlane as a production lowering target, not as already implemented kernel-level enforcement.
4. E1/E4 utility and recovery are still partial: local-Qwen results separate authority surface from reward, but planner/CEGAR recovery must improve task-correct progress without broad leases.

## Result

No additional idea-layer paper edits are required in this round. The next blocking work should be evidence-facing:

- implement or strengthen E3 residual-lift baselines over existing benchmark-derived workflows,
- continue E4 planner/CEGAR recovery,
- keep all results organized as four core experiments rather than many run IDs,
- preserve the current claim boundary in the paper until stronger evidence lands.
