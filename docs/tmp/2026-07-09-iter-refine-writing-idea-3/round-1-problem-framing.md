# Round 1 - Problem Framing

Date: 2026-07-09

## What Was Checked

Read `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` against `iter-refine-writing-idea/references/idea-quality-checklist.md` Section 1. A read-only fork reviewer (`Huygens`) inspected the abstract, introduction, motivation/background, design goals, and evidence boundary for concrete problem framing, root-cause clarity, non-prompt-injection motivation, claim scope, and the four authority-input context framing.

## Findings

Must-fix:

- The introduction's PDF/subagent example said that PDF text controlled an authority transfer, but the concrete harm was not visible enough if the final repository and body still looked valid.
- The four context classes were explained well in the design section, but the motivation did not yet make them feel necessary before the system taxonomy appears.
- The first page used `protected-decision transition` and `commit object` too early, making the problem look defined in solution terms.

Should-fix:

- The prior-work paragraph risked sounding like a straw man unless it acknowledged that systems exposing issuer-owned proofs and same-transition lifecycle state could implement the same interface.
- The motivating workflow still leaned too heavily on hidden-PDF injection; it needed a benign least-privilege/usability failure.
- The introduction's result paragraph was too numeric for problem framing.
- The design-goal paragraph needed a clearer failure-mode-to-goal mapping.

Consider:

- Reduce first-page terminology load.
- Compress the recovery row in the evidence-boundary table.
- Clarify that delegation is not a fifth authority-input owner class.

## What Changed

- Strengthened the introduction example at lines 40--42 so the failure is now unauthorized authority transfer under otherwise valid-looking arguments.
- Reframed the root cause at line 42 as the absence of a pre-effect atomic record binding field issuer, proof source, control context, and lifecycle mutation before naming the transition abstraction.
- Updated the related-defense paragraph at line 44 to avoid a straw-man claim: prior systems can implement part of the interface if they expose issuer-owned field proofs and same-transition lifecycle mutation.
- Rephrased the insight paragraph at line 46 as a runtime-visible pre-effect authorization record before naming the commit object.
- Compressed the introduction result paragraph at line 52 to claim-facing takeaways instead of dense run numbers.
- Added a non-adversarial Skill/MCP/cmd authority example and the four non-substitutable proof questions in the motivating workflow at lines 80--82, including why three classes are insufficient without env/runtime observations.
- Tightened the design-goal mapping at line 117 to connect wrong sink/approval widening, data-as-authority, stale reuse/delegation, and boundary bypass to G1--G4.
- Clarified the delegation row in Table 1 at line 217 as not a fifth owner class.
- Compressed the recovery row in the evidence-boundary table at line 907 while preserving the key R263--R268 numbers in the paper.

## Remaining Concerns

- Later idea rounds still need to attack whether the commit-object framing is novel enough against stateful policy DSL / IFC / provenance systems.
- The paper remains explicit that current results are bounded to instrumented protected-decision boundaries and do not prove full end-to-end utility or approval-burden reduction.
