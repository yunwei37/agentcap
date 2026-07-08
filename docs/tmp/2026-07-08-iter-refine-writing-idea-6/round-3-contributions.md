# Round 3 - Contributions and Design Goals

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex` abstract, introduction contribution list, design goals, goal-map table, formal model, implementation scope, evaluation framing, and related-work abstraction tables.
- Focus: whether contributions are independent, whether system contribution goes beyond MCP/tool-call guards, whether four context classes are framed as a runtime interface requirement rather than taxonomy, whether goals map cleanly to evidence, and whether claims exceed current prototype evidence.

Findings:
- Must-fix: the contribution list was still three items and conflated the model, commit API, prototype, and evidence.
- Must-fix: "three-class models are insufficient" could be overread as a taxonomy claim; a three-class system with explicit per-field owner projections and atomic lifecycle commit could be equivalent.
- Must-fix: E1 reference-action coverage is a utility/expressiveness guardrail rather than a direct safety goal.
- Must-fix: system claims should remain scoped to a local multi-boundary prototype, local boundary suite, and simulated OS-monitor replay backend, not production MCP broker, production prompt builder, real subagent runtime, or kernel/ActPlane mediation.
- Should-fix: abstract result sentences needed explicit scope cues.

What changed:
- Abstract: added scope cues for `local authorization substrate prototype`, `saved-trace protected-event replay`, `controlled local boundary suite`, and `simulated OS-monitor replay backend`.
- Introduction: narrowed "three classes are insufficient" to "interfaces that do not expose per-field owner projections and same-transition lifecycle update are insufficient."
- Contributions: split the previous 3-item list into four independent contributions: model, commit API, multi-boundary prototype/lowering, and evidence.
- Design goals: updated the goal map so E1 is a separate utility/expressiveness guardrail rather than a safety goal.
- Formal section: clarified that further merges are acceptable only if they preserve owner projections and same-transition lifecycle update; otherwise E3 counterexamples expose unsafe merge.

Remaining concerns:
- Evidence maturity remains the primary top-conference risk: the paper still needs stronger end-to-end utility/recovery, independent adjudication, and a production-like multi-boundary integration or real monitor backend for an OSDI/SOSP-strength system claim.
