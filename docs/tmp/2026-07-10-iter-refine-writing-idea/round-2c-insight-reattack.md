# Round 2c: Insight Re-Attack

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex` after Round 2b owner-merge and split-lifecycle propositions.
- Focus: whether a skeptical OSDI/SOSP reviewer can still reject the idea as ABAC, IFC, a reference monitor, ActPlane policy synthesis, or Skill/MCP permissioning.

Findings:
> Overall: the direct “this is just ABAC/IFC” rejection is much weaker after the owner-merge / split-lifecycle propositions. The remaining strong rejection is about evidence and baseline legitimacy: reviewers may still say the paper names a stateful reference-monitor object, then evaluates against author-defined weakened variants and small controlled suites.

> Must-fix: State the core insight as a falsifiable field-issuer linearization requirement: agent runtimes split field issuer, observation issuer, and lifecycle writer by default; sound monitors must linearize all three in one pre-effect transition.

> Must-fix: Strengthen E2 with a strongest prior-derived baseline/interface table mapping PACT, IFC, ActPlane, SkillGuard, AgentSpec-style systems to fields they expose by default and fields they must add to converge to IntentCap.

> Must-fix: Add non-tautological evidence hooks after the propositions, because the propositions otherwise look definition-driven.

> Must-fix: Add an ActPlane observability table so the paper says ActPlane-style backends need upstream projections, rather than claiming OS enforcement cannot help.

> Must-fix for experiments, not this writing patch: broaden E3 from one 9-event integrated workflow to 3-4 integrated workflows across PDF-to-issue, Drive/report, calendar/email, and repo/code tasks.

What was changed in Round 2d:
- Abstract: removed one detail-heavy reference-action number from the first screen and kept the two strongest paper-facing results.
- Introduction: named the central insight as a field-issuer linearization requirement.
- Contributions: changed C3 from generic evaluation evidence to evaluation methodology and protected-decision counterexample artifacts.
- Formal model: added artifact-derived evidence hooks after both propositions.
- E2: added a strongest prior-derived baseline/interface audit table.
- Related work: added an ActPlane-style observability boundary table.

Remaining concerns:
- The expanded E3 integrated workflow suite is still required for a stronger system-scale claim.
- A further Round 2e re-attack should decide whether the current idea framing can move to contributions/goals review.
