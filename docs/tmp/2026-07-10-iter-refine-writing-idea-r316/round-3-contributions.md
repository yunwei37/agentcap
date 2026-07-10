# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 3 contributions and design-goal alignment.

## What was checked

The reviewer checked whether the current paper's contributions and design goals follow the Round 2c framing: authority-state commit interface, owner-equivalence/lifecycle-equivalence, the four authority-input owner classes, E1/E2/E3 claim structure, and a systems contribution beyond MCP/tool-call guards.

## Findings

- Must-fix: G2 blocked env/tool/instruction substitution but did not explicitly state that agent-owned context is not a super-owner for tool schema, instruction endorsement, or runtime observation.
- Must-fix: C1/C2/C3 were aligned but too compound. C1 and C2 packed model, invariant, interface, equivalence criterion, and falsifier explanation into single bullets.
- Must-fix: The evaluation overview mixed representability, safety, and enforcement numbers in one dense paragraph, risking a results-ledger reading.
- Should-fix: The authorization-input section alternated among context class, authority-input class, proof owner, owner projection, and context owner.
- Should-fix: The prior-system paragraph was long enough to bury the main novelty: pre-effect commit object plus checker-owned lifecycle state, not more predicate expressiveness.
- Should-fix: Safety properties P1--P5 read as equally central; P1--P3 should be identified as core, P4 as delegation-specific, and P5 as a no-promotion corollary.
- Consider: Keep ActPlane/OS as backend/contrast until production mediation and overhead exist.
- Consider: Reference the evidence-boundary table near the contribution list so missing utility, ActPlane, and expert-oracle evidence are visible rather than hidden.

## Changes made

- Prior-work positioning, introduction: split the strongest-alternative paragraph into an equivalence-boundary paragraph and a litmus-test paragraph. The text now states that a monitor exposing the same authority-state commit object implements the IntentCap interface, while a runtime missing the object must prove owner-equivalence and lifecycle-equivalence.
- Contribution list, introduction: rewrote C1/C2/C3 into three independent bullets: model, runtime interface, and claim-driven evidence package. Moved collapsed/split baseline explanations into the following paragraph.
- Contribution boundary, introduction: added a sentence after C3 that points to the evidence-status section for benchmark-scale utility, approval burden, independent expert oracle, and production ActPlane/MCP evidence.
- Design goals: rewrote G2 so any non-owner class is forbidden from filling a protected field. The text now explicitly says agent-owned context only mints or bounds goal/object/sink/approval/delegation root and cannot prove tool schema, instruction endorsement, or runtime observation.
- Authorization inputs: introduced "authority-input owner classes" as the canonical term and stated that raw artifacts are split into owner-typed proof cells before checker submission.
- Safety properties: added a classification sentence: P1--P3 are core safety properties, P4 is delegation-specific, and P5 is a no-promotion corollary.
- Evaluation overview: replaced the dense first paragraph with a claim-to-experiment spine: E1 rules out unusability, E2 validates owner/lifecycle necessity by removal, and E3 validates local multi-boundary enforceability. The quantitative results remain unchanged.

## Remaining concerns

- The paper still needs later writing rounds to reduce long paragraphs and enforce consistent terminology throughout the full document.
- Evidence gaps remain explicit: independent/blinded field-owner adjudication, benchmark-scale utility/recovery, approval-burden measurements, production MCP integration, and ActPlane/eBPF mediation.
- The next idea-refinement round should check cross-alignment from problem statement to insight, goals, contributions, formal properties, and E1/E2/E3.
