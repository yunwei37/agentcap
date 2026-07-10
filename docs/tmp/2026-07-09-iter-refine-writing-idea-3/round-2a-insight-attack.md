# Round 2a - Insight and Novelty Attack

Date: 2026-07-10

## What Was Checked

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Focus: idea-layer novelty, especially whether IntentCap still sounds like ordinary ABAC, a policy DSL, Skill/MCP permissions, or ActPlane policy synthesis rather than a distinct systems abstraction.

Checklist source: `iter-refine-writing-idea/references/idea-quality-checklist.md`, Section 2.

## Findings

Must-fix findings from the reviewer attack:

1. The core insight could be attacked as ordinary transaction semantics plus capabilities. The paper admitted that any stateful reference monitor or policy DSL with issuer attributes, counters, a delegation graph, and an audit id could implement the same result. The fix should reframe novelty as a minimal protected-decision commit object: issuer-owned field proofs plus lifecycle mutation in one pre-effect transition.

2. The four authority inputs still looked like ABAC namespaces. The paper needed to define a safe-merge equivalence relation before naming `agent`, `instruction`, `tool`, and `env`: two sources can merge only if they have identical forgeability surface, observation point, lifecycle authority, and protected-field ownership.

3. The insight needed evidence before design. The paper claimed the commit object was necessary, but most evidence appeared after the system was defined. The fix should add a pre-design characterization paragraph or table using existing traces/counterexamples.

4. ActPlane positioning was still too easy to read as "IntentCap is ActPlane policy synthesis with provenance labels." The fix should state that IntentCap decides agent/instruction/tool/env field proofs above ActPlane, while ActPlane-style monitoring can only enforce the env/local-effect projection.

Should-fix findings:

1. Qualify "commit object" as "authority-state commit object" and define its non-generic contents.

2. Replace yes/no related-work comparisons with a default runtime-object comparison, because programmable systems may encode similar predicates if extended.

3. Add lifecycle-linearization equivalence in addition to owner-projection equivalence.

4. Strengthen Skill/MCP distinction around field ownership: even per-run manifests are insufficient if package/server text can own user fields such as sink, approval scope, or delegation root.

Consider findings:

1. Keep the intro focused on one headline insight.

2. Add concrete implementation falsifiers for safety properties.

3. Keep recovery as a utility diagnostic rather than a novelty pillar.

## Remaining Concerns

This was an adversarial attack round only. It did not edit the paper. The next step is Round 2b defense edits, followed by compile/audit and a Round 2c re-attack.
