# Round 2d: Insight Defense After Re-Attack

Date: 2026-07-10

What was changed:
- `docs/autopaper/intentcap-paper-zh.tex`

Defense applied:
1. Re-centered the core insight.
   - Before: the introduction said the novelty was a runtime-visible commit object, but a reviewer could still call it a reference-monitor state object.
   - After: the paper states the falsifiable requirement: agent runtimes split field issuer, observation issuer, and lifecycle writer by default, so a sound monitor must linearize all three in the same pre-effect transition.

2. Made the propositions less definition-driven.
   - Before: owner-merge and split-lifecycle unsoundness could be read as logical possibilities.
   - After: each proposition now points to artifact-derived cases showing the premise occurs in MCP metadata, AgentDojo/InjecAgent/env traces, Skill placement records, and integrated workflow/delegation records.

3. Added a prior-derived baseline audit.
   - Before: the typed-provenance state guard could look like an author-defined weak baseline.
   - After: Table `prior-derived-interface-audit` maps IFC/taint/CaMeL, PACT, AuthGraph/AIRGuard, SkillGuard/SkillScope, ActPlane, and a stateful ABAC/provenance composite to available runtime fields and convergence fields.

4. Clarified ActPlane-style lowering without a strawman.
   - Before: the related-work text said ActPlane-style backends only receive env/local projections.
   - After: Table `actplane-observability` separates native OS/local visibility from upstream projections for prompt placement, instruction endorsement, tool schema, agent sink/approval, and lease lifecycle.

5. Reduced first-screen result clutter.
   - Before: the abstract carried three detailed result sentences.
   - After: it keeps the no-owner false accept result and the multi-boundary 0 unsafe execution/placement result.

Remaining concerns:
- Need a fresh Round 2e re-attack before claiming the idea-layer novelty framing is stable.
- Need an expanded integrated workflow experiment suite before claiming production-like system breadth.
