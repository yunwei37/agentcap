# Round 2c: Insight Re-Attack

Date: 2026-07-08

## What Was Checked

A forked reviewer re-attacked the current Chinese paper after Round 2b, focusing on whether the protected-transition framing still looks like ordinary provenance/IFC plus capabilities and a policy DSL.

## Findings

The re-attack found that the paper is now clearly different from a simple MCP/tool-call guard, but a strong reviewer could still reject the idea as "provenance/IFC + capabilities + typestate/policy DSL" unless the paper frames the contribution as a runtime commit protocol and adapter contract.

Must-fix findings:

- Abstract/intro still risk reading as a predicate bundle. The fix is to state that IntentCap is a multi-issuer commit protocol over protected decisions, not a new predicate family.
- The four authority-input classes risk reading as ABAC namespaces. The fix is to emphasize the safe-merge criterion: classes merge only when issuer, forgeability surface, provable fields, observation boundary, and lifecycle authority match.
- The system contribution needs an earlier concrete API example, before the reader reaches implementation details.
- E4 evidence must remain bounded to local adapter-contract feasibility and OS-monitor-style lowering, not production ActPlane/kernel enforcement.

Should-fix findings:

- Compress the insight into a quotable sentence: the protected object is a future authority-state transition, not a completed action.
- Present E3 as an ordinary-DSL/provenance collapse test: same action/argument/prompt slot, only issuer or lifecycle state changes.
- Avoid defensive language that makes the idea sound trivially replaceable by adding a few attributes.

## What Was Changed

- Abstract, lines 30-31: changed the thesis to "agent 授权的最小对象不是已经发生的 tool call，而是即将改变 authority state 的 protected-decision transition" and introduced the multi-issuer commit protocol framing.
- Introduction, lines 53-64: reframed the prior-work distinction around runtime commit objects rather than predicate expressiveness.
- Introduction, lines 64-75: added an early `create_issue` commit-record example with agent, instruction, tool, and env/state fields.
- Contributions, line 85: included lease auditability as a bounded E2 evidence block.
- Design, lines 216-224: recast the four classes as issuer boundaries and made the safe-merge criterion explicit.
- Formal model, line 511: replaced defensive equivalence wording with a requirement for a multi-issuer check-and-consume object.
- Evaluation, lines 690-734: reorganized the evaluation into E1-E4, with E2 as bounded lease auditability rather than an auxiliary loose end.
- E3, lines 736-752: renamed and reframed it as an ordinary-DSL/provenance collapse and lifecycle ablation.
- E4, lines 790-820: bounded the claim to local adapter-contract feasibility and deterministic lowering target.
- Evidence-boundary table, line 843: rewrote the E4 claim as local multi-boundary adapter contract evidence.

## Remaining Concerns

Another Round 2c re-attack is required after compilation and evidence audit. If the reviewer still sees the work as a predicate bundle, the next fix should likely reduce term count and move the commit protocol even earlier into the abstract/intro.
