# Round 5 - Reviewer Stress Test

Date: 2026-07-08

What was checked:
- Full stress test of `docs/autopaper/intentcap-paper-zh.tex` after Round 4.
- Focus: whether a reviewer can still easily reject the paper as a stateful policy DSL, reference monitor transaction, adapter demo collection, taxonomy argument, or under-evidenced top-conference system.

Findings:
- Verdict: the reject is no longer easy. The direct "this is just MCP/tool guard/ActPlane/EIM" rejection is weaker because the paper now centers on issuer-owned field proofs, same-transition lifecycle update, and a pre-effect commit contract.
- Strongest remaining hard reject: evidence maturity. The paper currently supports a mechanism/prototype claim with controlled counterexamples and local boundary tests, not a production-grade OSDI/SOSP system claim.
- Must-fix: define equivalence against stateful policy DSL/reference monitor more positively.
- Must-fix: keep C3 scoped as a local multi-boundary authorization-substrate prototype.
- Must-fix: keep E1 as reference-action coverage plus replay sanity only; move Qwen/feedback diagnostics out of the E1 claim.
- Must-fix: keep expert minimality, prevalence, utility preservation, and production enforcement as missing evidence.
- Should-fix: reduce taxonomy flavor by emphasizing issuer-owned field projections.
- Should-fix: add a commit-path figure.
- Should-fix: reduce abstract result density.

What changed:
- Abstract: shifted from four-class context wording to issuer-owned field projections, and removed the monitor-mismatch result from the abstract.
- Introduction: described the four classes as the current implementation of field-owner projections rather than the central object of the claim.
- Runtime design: added Figure `commit-path`, showing adapter proofs, checker sole writer, `allow(sigma', audit_id)`, and bound side effect / prompt placement / handoff.
- Formal section: added an explicit equivalence rule. Any equivalent policy DSL/reference monitor must expose field-owner proof projections, checker-owned lease state, same-transition consume/delegate update, and audit commit id bound to the side effect.
- E1: removed local-Qwen and structured-denial diagnostic paragraphs from the main E1 subsection. E1 now only reports reference-action coverage and replay sanity.
- Evidence boundary already separates lease auditability from preliminary closed-loop utility/recovery and lists independent labels, larger natural protected-decision labels, fresh matched model-loop comparison, and production enforcement as missing evidence.

Remaining concerns:
- The paper still needs stronger evidence for a top-conference submission: independent/blinded adjudication, larger fresh model-loop utility/recovery, and a production-like prompt/subagent/MCP/ActPlane boundary or overhead study.
- R243/R244 should be completed before deciding whether the larger local-Qwen matched comparison belongs in the main paper or only in limitations/supporting diagnostics.
