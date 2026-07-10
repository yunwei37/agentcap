# Iter Refine Writing Idea Round 2c: Insight Re-Attack

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 2c adversarial insight and novelty re-attack.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Dewey`.

## What Was Checked

The subagent reviewed the Round 2b novelty-defense draft against `idea-quality-checklist.md` Section 2. The focus was whether the new `minimal protected-decision interface theorem`, safe-merge criterion, four owner classes, and E2 evidence still look like repackaged provenance, IFC, capabilities, and stateful policy DSLs.

## Findings

Overall novelty risk: Medium.

Strongest reject argument:

> The paper's “minimal protected-decision interface theorem” is closer to an interface specification than a new systems insight. It states that equivalent systems must expose the same owner proofs and lifecycle state, then evaluates weakened systems that deliberately remove those fields. This shows those fields are useful, but not yet that IntentCap is the first or necessary abstraction beyond a well-designed stateful policy DSL, AuthGraph-style authority graph, PACT-style argument provenance, or CaMeL-style IFC extended with counters and delegation state.

Must-fix items:

- The theorem needs to separate an interface definition from the non-trivial systems insight. The missing point is that the authority-changing decision transition is the minimal authority-state linearization point; action-time, flow-time, package-time, or OS-time alone misses some same-action false accept.
- The typed-provenance state guard should be described as a strong prior-style composite: CaMeL/IFC control provenance, PACT argument source, AuthGraph/AIRGuard intent/action edge, SkillGuard package policy, stateful counters, and budget/temporal checks.
- Blinded second-pass owner-label adjudication over the 83 current-source labels remains the most important evidence-side gate.
- The paper should keep saying that four context classes are not the contribution. The contribution is the safe-merge test and owner-projection obligation; four classes are the current workload's canonical projection.

Should-fix items:

- Add a short “why surprising” sentence in the abstract explaining why tool-call granularity is tempting but insufficient.
- Rephrase the policy DSL response so it does not sound like “if you implement my interface, you are me.” The claim should be that IntentCap identifies a missing runtime object and tests whether published/default objects expose it.
- Call the 93.98% number a removal-family false-accept rate, not a natural security rate.
- In related work, state that AuthGraph/PACT/CaMeL naturally expose graph edges, argument contracts, or flow labels, while IntentCap's object is a pre-effect authority-state transition.

## Remaining Concerns

The novelty risk is reduced from high to medium, but not low. The strongest missing evidence is still independent/blinded field-owner adjudication plus a stronger composite-baseline implementation and a few end-to-end workflow examples with benign completion.
