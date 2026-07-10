# Round 2e: Insight Re-Attack After Prior-Baseline And ActPlane Tables

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex` after Round 2d.
- Focus: whether the prior-derived baseline/interface audit, formal evidence hooks, and ActPlane observability table are enough to move past Round 2.

Findings:
> Verdict: novelty framing is stable enough to move to Round 3. The strongest remaining rejection is no longer “this is just ABAC/IFC/reference monitor renamed.” It is that the abstraction looks plausible, but the evidence still needs stronger baseline legitimacy and broader system-scale experiments.

> Must-fix for later experiments: E2 prior-derived baseline should become a citation-backed/machine-readable audit table, and the typed-provenance state guard should run over more E2/E3 key cases rather than only the workflow residual slice.

> Must-fix for later experiments: E3 needs 3-4 integrated workflows, such as PDF-to-issue, Drive/report, calendar/email, and repo/code, each crossing agent/instruction/tool/env/delegation and comparing object-only, stateful ABAC/provenance, OS-only, and IntentCap.

> Should-fix: name the main theorem form as the Field-Issuer Linearization Requirement, clarify lease vs commit object, and make the ActPlane wording say that OS backends do not sign upstream field proofs by default.

What was changed:
- Introduction: added the relationship between lease and commit object.
- Formal model: added `Field-issuer linearization requirement` as the combined theorem-shaped obligation over owner equivalence and lifecycle equivalence.
- Related work: changed ActPlane/backend wording from “does not decide policy source” to “does not sign upstream field proofs by default.”

Remaining concerns:
- Proceed to Round 3 contributions/goals review.
- Do not continue adding novelty defense text unless the Round 3 or later reviewer identifies a concrete misalignment.
- Open experiment work remains: stronger integrated workflow suite and a unified strongest-baseline run.
