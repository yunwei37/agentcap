# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 5 reviewer stress test.

## What was checked

The reviewer attempted to construct the strongest plausible OSDI/SOSP rejection argument against the current idea framing. The stress test focused on novelty versus stateful ABAC/IFC/provenance/reference monitors, whether the four authority-input owner classes are overclaimed, whether the authority-state commit object is a real systems contribution, and whether E1/E2/E3 support the bounded claim.

## Findings

- Strongest reject: the paper could still be read as renaming stateful reference monitor + ABAC/IFC provenance + capability lease + transactional check-and-consume, especially because it says a DSL/reference monitor exposing the same commit object would implement IntentCap.
- Strongest reject: the four owner classes are supported by tested removal witnesses, but author-adjudicated labels and controlled counterexamples do not prove natural prevalence, independent agreement, global minimality, or broad applicability.
- Strongest reject: E1/E2/E3 remain bounded feasibility and ablation evidence; without independent owner-label replication or a deployed end-to-end boundary, an OSDI/SOSP reviewer may call the paper an interesting model/prototype rather than a complete systems paper.
- Must-fix: narrow novelty from "new security model" to a strong interface invariant and equivalence test for agent authority transitions.
- Must-fix: make E2 explicitly about externally evidenced, same-event unsafe-collapse witnesses rather than a self-certifying type system.
- Must-fix: further downgrade the four-owner claim to proof-owner equivalence classes on the implemented surfaces.
- Must-fix: retitle E3 so it cannot be read as production enforcement.
- Should-fix: make C3 sound like methodology/prototype evidence rather than a generic evidence package.
- Should-fix: explain before the evidence-status table that missing rows are stronger-claim boundaries, not contradictions of the current bounded claim.

## Changes made

- Abstract: rewrote the prototype sentence to "five local/replay boundary classes" rather than an artifact-list main clause.
- Contributions: renamed C3 to "Claim-driven evaluation methodology and prototype evidence."
- Authorization inputs: changed the four-class claim to "proof-owner equivalence classes" obtained by safe-merge on the paper's Skill/MCP/cmd/env/subagent surfaces; removed language that sounded like a global default partition.
- Formal model: changed the owner-set discussion and lifecycle-equivalence paragraph to say other systems may use finer or differently named owners if they preserve per-field owner projections and lifecycle-equivalent commit.
- E2: changed the claim language from general necessity to the existence of unsafe-collapse witnesses in tested owner/lifecycle/local-boundary removal families.
- E3: renamed the subsection to "Local Multi-Boundary Enforceability" and added that it does not prove production MCP, ActPlane, real subagent runtime, or full prompt runtime.
- Evidence status: added that missing rows in the current-evidence table are boundaries for stronger claims, not a weakening of the current bounded claim.

## Remaining concerns

- The strongest remaining top-conference risk is evidence, not idea coherence: independent/blinded owner-label replication and at least one deployed end-to-end boundary would materially improve the paper.
- The full-paper prose still needs iter-refine-writing rounds for paragraph length, safety-property overlap, and related-work compression.
- The idea framing is now coherent for a bounded systems/security paper, but not yet enough to claim OSDI/SOSP-level completion.
