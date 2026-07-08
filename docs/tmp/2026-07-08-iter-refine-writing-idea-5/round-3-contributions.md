# Round 3: Contributions and Design Goals

Date: 2026-07-08

## What Was Checked

A read-only reviewer checked `docs/autopaper/intentcap-paper-zh.tex` against the idea-quality checklist Section 3, focusing on contribution statements, design goals, goal-to-evaluation mapping, the four authority-input framing, evidence boundaries, and whether E1-E4 read as coherent claim-facing experiments rather than run history.

## Findings

Must-fix findings:

- E2 was too weak to stand as a co-equal core experiment. The 24 project-author adjudicated labels are useful as a lease audit, but they do not yet support an independent expert-oracle least-privilege claim.
- C2 was too compound. It listed context placement, Skill placement, tool/MCP events, local env side effects, and delegation handoff in one contribution sentence, making the system contribution look like a feature list rather than a single API/adapter contract.
- The commit-record example mixed env context with checker state by putting active budget in an `env/state field`, even though budget and lease consumption belong to checker state `sigma`.

Should-fix findings:

- The design-goal table needed main falsifiers, especially for G1 intent-bounded authority and G3 stateful lease lifecycle.
- E1 mixed primary replay/reference-coverage evidence with local-Qwen diagnostics and feedback pilot details, which made it read like run history.
- The E3 title "Ordinary-DSL Collapse" could overstate the claim against all policy DSLs.

Consider findings:

- Keep the contribution list as the model/system/evidence three-piece structure, but make C2 and C3 less list-like.
- Organize the evaluation as three primary experiments plus one supporting audit: E1 safety/reference coverage, E3 mechanism necessity, E4 multi-boundary enforcement, and lease auditability as supporting evidence.
- Preserve the existing limitations against production ActPlane/kernel mediation, production MCP broker/prompt builder/subagent runtime, end-to-end utility, approval burden, and independent expert labels.

## What Changed

- Contribution list, around lines 84-87: rewrote C2 as a single checker-centered protected-transition API and adapter-contract contribution, and rewrote C3 so lease auditability is supporting evidence rather than a co-equal main experiment.
- Commit-record example, around lines 69-74: split `env field` from `checker state sigma`; active lease, budget, expiry, and delegation graph now live in checker state, not env context.
- Goal-map table, around lines 173-182: replaced generic obligations with explicit falsifiers for G1-G4, such as non-agent issuer supplying sink/approval/policy fields, class-substitution false accepts, exhausted-lease reuse, over-delegation, and pre-effect adapter bypass.
- Evaluation opening and summary table, around lines 703-727: reorganized the evaluation into three primary experiment blocks plus a supporting lease audit. E2 is no longer presented as a main experiment.
- E1 subsection, around lines 731-739: narrowed the primary E1 claim to unsafe accept and reference-action coverage, and moved local-Qwen/recovery numbers into explicitly labeled diagnostics.
- E2 subsection, around lines 741-747: renamed it to `Supporting Audit` and stated that independent labels, inter-rater agreement, and statistical authority-distance comparison are required before promoting it to expert-oracle least-privilege evidence.
- E3 subsection title and opening, around lines 749-751: renamed it to `Issuer-Collapse and Lifecycle-Split Ablation` and made the DSL boundary explicit.
- `docs/evaluation.md`: updated the evaluation consolidation, claim map, experiment matrix, and ordering rules to use E1/E3/E4 as primary experiments and lease auditability as supporting audit.
- `docs/design.md`: clarified that four classes are issuer-owned proof projections for one protected-decision transition and that checker state is separate from env context.

## Remaining Concerns

The contribution and goal structure is now cleaner. The main remaining evidence risks are unchanged: no independent expert-label replication, no benchmark-scale closed-loop utility/recovery result, no approval-burden measurement, and no production ActPlane/kernel mediation or production prompt-builder/MCP/subagent runtime.
