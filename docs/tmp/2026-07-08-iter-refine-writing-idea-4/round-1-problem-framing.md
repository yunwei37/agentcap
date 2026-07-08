# Round 1: Problem Framing

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reference: `iter-refine-writing-idea/references/idea-quality-checklist.md`, Section 1.

Reviewer: forked subagent `Anscombe`, read-only. The reviewer was asked to focus on concrete consequences, root-cause clarity, straw-man risk, and scope alignment.

## Findings

Must-fix:

- The motivating example described authority lifecycle corruption, but the concrete painful consequence was too abstract. The reviewer asked for explicit threat consequences such as unauthorized repositories, unauthorized sinks, or future policy corruption.
- The root cause had several competing phrasings: data/authority boundary breakage, mixed planning channel, missing stateful future authority, and four issuer classes. The reviewer asked to collapse this into a two-part root cause: issuer collapse plus authority-state split.

Should-fix:

- The related-work gap could still read as a straw man. The reviewer asked to say that prior policy DSLs could encode similar rules if extended, while IntentCap makes them the default authorization object.
- The four-context taxonomy appeared early and dense. The reviewer asked for one concrete local-exec example in the intro, leaving the full taxonomy for the design section.
- The intro could over-suggest production MCP/prompt-builder/ActPlane coverage. The reviewer asked for a scope guard before the contributions.
- The motivation was too adversarial. The reviewer asked for a non-malicious operational consequence: run-specific authority avoids union permission, broad approvals, and false denial.

Consider:

- Define protected decision before the background paragraph uses it.
- Make the related-work table header emphasize default authorization object and lifecycle support.

## Changes

- Lines 40-46 now add concrete consequences, define the root cause as issuer collapse plus authority-state split, and limit the four-context taxonomy in the intro to a local PDF extraction example.
- Line 46 now clarifies that the comparison is about the default authorization object, not an impossibility claim about prior DSL expressiveness.
- Line 56 now adds a scope guard: current evidence supports instrumented protected-decision boundaries, not full production runtime, production ActPlane integration, or benchmark-scale utility.
- Line 74 now defines protected decision before the motivation subsection.
- Line 83 now adds the non-malicious operational motivation: the same Skill/MCP/cmd needs different authority across runs, so static permissions force union permission, broad approval, or false denial.
- The related-work table header now uses `Default root` and `Default object`.

## Remaining Concerns

- This round did not run the full adversarial novelty round. Round 2 still needs to attack whether issuer-typed protected-decision leases are a genuinely new abstraction rather than a policy-DSL encoding.
- Scope remains intentionally conservative. End-to-end utility, independent labels, and production boundary integration are still evidence gaps, not writing issues.
