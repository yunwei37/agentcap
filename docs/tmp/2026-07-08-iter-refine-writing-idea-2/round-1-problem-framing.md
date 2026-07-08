# Round 1: Problem Framing

Date: 2026-07-08

## What Was Checked

Read `docs/autopaper/intentcap-paper-zh.tex` against `iter-refine-writing-idea/references/idea-quality-checklist.md` Section 1. A read-only fork reviewer focused on whether the paper states a concrete problem, separates root cause from solution, justifies the four context planes, and bounds claims against current evidence.

## Findings

Must-fix findings from the reviewer:

- Abstract and introduction lacked a concrete painful consequence. The reviewer asked for a failure trace where PDF text widens approval, delegation/reuse happens, the final repo argument remains legal, and ordinary tool/argument guards still pass.
- Root cause and solution insight were too close together. The root cause should be expressible without naming IntentCap.
- The four context planes were motivated by examples but needed a criterion for why there are exactly these planes.
- Evaluation framing mixed future full-paper experiments with current pilot evidence.
- Contribution C3 sounded like a roadmap rather than a top-conference contribution.

Should-fix findings applied:

- Reordered the abstract into problem, insight, mechanism, evidence boundary.
- Clarified signed/trusted Skill instructions versus unsigned or malicious Skill text.
- Mapped the running failure trace to the five design goals.
- Qualified the "intersection of four contexts" statement so it does not imply every lease has non-empty fields from all planes.
- Added a tighter formal-property scope for instrumented protected-decision events with adapter-supplied control-provenance proofs.

## What Was Changed

- Abstract, lines 24-25 before edit: one dense paragraph packed context, model, architecture, pilot numbers, and limitations.
  After edit: one paragraph with four beats: extensible agents create context-influence decisions; IntentCap's authorization unit is a protected-decision lease; checker validates four planes and provenance; current results are pilot evidence only.

- Introduction, lines 32-36 before edit: stated that a malicious PDF could induce broader approval or delegation, but did not spell out why ordinary guards would miss it.
  After edit: added a concrete failure trace: user asks for a single issue in `org/repo-x`; PDF induces full GitHub approval, subagent delegation, and one-shot reuse; final `create_issue(repo=org/repo-x)` still looks legal to an argument guard.

- Contribution C3, line 53 before edit: "Evidence plan and pilot results."
  After edit: "Evaluation protocol and pilot evidence," with explicit wording that current artifact only claims pilot/mechanism evidence.

- Threat model, lines 101-103 before edit: listed `Skill instruction` as attacker-controlled context without distinguishing trusted and untrusted cases.
  After edit: distinguished unsigned/malicious Skill text from signed/trusted Skill instruction endorsed into instruction context.

- Design goals, lines 105-113 before edit: goals were listed as a checklist.
  After edit: added a one-sentence mapping from the running failure trace to intent root, influence separation, stateful consumption, untrusted compiler, and adapter lowering.

- Authority inputs, lines 187-236 before edit: examples showed why planes differ, but the criterion and "intersection" wording were too broad.
  After edit: defined four plane criteria (issuer, forgery surface, authority field, adapter observation point), explained why each plane is non-substitutable, changed the table caption, and clarified that only the required fields for a protected decision must come from their designated planes.

- Formal properties, lines 503-506 before edit: properties were scoped to accepted traces but not explicitly to instrumented protected fields and adapter-provided proofs.
  After edit: scoped trace-level properties to accepted traces over instrumented protected-decision events with adapter-supplied control-provenance proofs.

- Evaluation opening, line 568 before edit: introduced E1-E4 without saying this was an evaluation design.
  After edit: explicitly states the section defines full-paper experiments and that current pilot evidence is summarized separately in the evidence-status section.

## Remaining Concerns

- The evaluation section is still long and contains one R217 example inside E3. It is now framed as pilot evidence, but later writing rounds should decide whether to move run IDs to an appendix/artifact table.
- The paper still needs the E1/E2/E3/E4 completion gates before it can claim full OSDI/NeurIPS-level end-to-end results.
