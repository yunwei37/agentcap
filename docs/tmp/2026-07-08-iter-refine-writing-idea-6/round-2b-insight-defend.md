# Round 2b - Insight Defense

Date: 2026-07-08

What changed:
- Abstract: reframed the core insight from a policy predicate to a pre-side-effect authority-state commit record.
- Introduction: extended the running example so PDF text influences `spawn(summarizer, K_child)` rather than directly changing `repo`; this makes provenance/action checks appear clean while the handoff transition is wrong.
- Introduction: added the positive novelty claim that a policy DSL without issuer-owned field proofs and same-transition consume/update cannot prove authority was not substituted, reused, or widened across boundaries.
- ActPlane positioning: clarified that ActPlane-style backends receive checker-certified local/env lease contracts and cannot synthesize agent, instruction, tool, or env field proofs.
- Authorization inputs: added a minimality contract mapping the four context classes to four proof questions: who authorized, what procedure is endorsed, what interface is callable, and what happened at runtime.
- Runtime lowering: rewrote `check_and_consume` as a commit-record interface, not an ordinary allow/deny function. The checker returns `sigma'` with budget, temporal, audit, and delegation updates.
- Evaluation: added a direct E1/E3/E4 thesis: event-model expressiveness, mechanism necessity, and cross-boundary placement.
- E3: added provenance for counterexamples, tying them to MCPTox-derived tool/schema artifacts, AgentDojo/InjecAgent/local env provenance labels, local Skill placement records, and R217 workflow residuals.
- Related work: changed the closest-work table columns from capability coverage to default commit unit, pre-state event, issuer field proof, lifecycle, delegation, same-transition update, and lowering.
- Design doc: synchronized the minimum runtime commit interface and four-proof-question minimality contract.

Before -> after:
- Before: `agent 授权的最小对象不是已经发生的 tool call...`
- After: `agent 授权的正确接口不是一个 policy predicate，而是副作用发生前一次会改变 authority state 的 commit record.`
- Before: `所有 adapter 调用同一个状态转移接口`
- After: adapter submits a complete commit record and checker atomically returns `allow(sigma', audit)` or `deny(reason)`.

Remaining concerns:
- Need Round 2c re-attack to see whether the stateful-ABAC objection still lands.
- Evidence concerns remain: closed-loop utility, independent labels, and more production-like integration are not fixed by this writing round.
