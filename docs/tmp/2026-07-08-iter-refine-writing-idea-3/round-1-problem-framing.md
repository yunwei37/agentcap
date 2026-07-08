# Round 1: Problem Framing

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Idea-quality checklist Section 1: concrete consequence, structural root cause, no straw-man gap, scope control.
- Focus: whether the four authority-input classes are introduced early enough, whether the paper looks broader than MCP/tool-call checking, and whether R219 is scoped correctly.

Findings:
- Must-fix: the four-context rationale appeared too late; intro needed to state why agent/instruction/tool/env are separate issuer classes.
- Must-fix: the motivation table used PDF text and script/tool output as separate rows, which obscured that both are env/runtime evidence.
- Must-fix: the motivating failure needed a stronger authority-lifecycle consequence, not just a legal final repo argument.
- Must-fix: system contribution needed to distinguish fully implemented checker/gateway/env backend from trace-level instruction/delegation semantics and ActPlane-style policy-target lowering.
- Must-fix: abstract result numbers needed scope qualifiers.
- Should-fix: R219 closest-baseline wording needed to say trace-level abstractions, not full prior-system reproductions.
- Should-fix: local command/cmd tools needed an explicit tool-vs-env example.
- Should-fix: E3 needed a direct owner-field-violation bridge from formal model to residual cases.

Changes made:
- Abstract now labels the three headline numbers as same-event protected-event replay, reference-action proxy, and isolated local env gateway.
- Intro now states the concrete authority-lifecycle failure: full GitHub scope approval, delegable write authority, lease reuse, and policy update despite a legal final repo argument.
- Intro now introduces the four authority-input classes before related work: agent intent/approval, instruction/Skill/manual, tool/MCP/cmd metadata, and env/runtime evidence.
- Motivation table now has four rows matching the model, with PDF text, stdout/stderr, file existence, and extracted values folded into env/runtime evidence.
- Contribution and implementation sections now state the prototype boundary: implemented checker/tool-live gateway/local env gateway; trace-level instruction/delegation semantics; ActPlane-style lowering target.
- Methodology now says closest baseline labelers are trace-level policy-family abstractions, not full AuthGraph/PACT/AIRGuard reproductions.
- Authority-input section now explains `pdftotext`: binary path, argv schema, and sandbox profile are tool context; cwd, input existence, stdout/stderr, and created files are env context.
- E3 now maps residuals to owner-field violations, with R219 as a tool-issued proof trying to fill agent/admin policy or approval fields.

Remaining concerns:
- This is Round 1 only. Later idea-refine rounds should stress-test novelty against AuthGraph/PACT/AIRGuard/IFC and make sure the insight is not framed as generic provenance checking.
- The paper still needs a future figure showing `agent/instruction/tool/env -> typed fields -> lease -> checker transition`.
