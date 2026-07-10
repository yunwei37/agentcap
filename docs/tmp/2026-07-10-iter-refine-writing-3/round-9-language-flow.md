# Round 9: Language Flow and Polish

Date: 2026-07-10

Target: `docs/autopaper/intentcap-paper-zh.tex`

Focus: topic/stress position, old-to-new flow, paragraph transitions, and register consistency. This round used `iter-refine-writing` Round 9 with `paper-writing-style` as a read-only reviewer pass.

## Findings

Must-fix findings:

- The evaluation method paragraph put artifact details such as kernel, Python, `llama.cpp` digest, model path, and context size in the stress position. The paragraph should instead emphasize that paper numbers come from saved summaries and that replay checks do not call models, execute tools, or sync datasets.
- E3's pre-side-effect paragraph mixed deterministic adapter enforcement with the Qwen3.6 proposer diagnostic. The deterministic multi-boundary claim should stand on its own, and model behavior should be reported as supporting diagnostics.
- The recovery paragraph read like a project status report. It should first state the evidence boundary: current recovery evidence supports constrained replacement safety, not benchmark-scale task recovery.
- The limitations paragraph described missing historical paths as repository state. It should instead state the reproducibility rule: only currently readable source artifacts enter primary evidence.

Should-fix findings:

- The motivation repeated the same Skill-manifest union-authority point.
- The baseline taxonomy packed implemented baselines, removal/composite baselines, same-event comparison, and oracle sources into one long paragraph.
- E2 characterization should state that trace characterization is boundary-existence evidence before giving counts.
- The three-class merge paragraph mixed evidence, scope, formal corollary, and non-claim boundaries.
- The E2 result paragraph should start from the mechanism conclusion, then give workflow, MCPTox, and Skill-placement numbers.
- The E3 aggregate paragraph should emphasize the system-contract result and move row-reuse caveats out of the stress position.
- Related work should focus on authorization-object differences, not lease-audit evidence boundaries.

Consider findings applied where useful:

- Split the introduction's "proof owners" sentence into a Chinese explanation followed by the four owner roles.
- Replaced the meta transition "后文用两张核心表" with a direct transition about fixing fields and proof projections.
- Reworded the E3 table transition around the shared falsifier: effects, placements, or handoffs can occur before checker acceptance without a pre-effect commit.
- Renamed `Supporting Diagnostics` to `辅助诊断` while leaving English experiment labels in tables unchanged.
- Strengthened the closest-abstractions recap so its stress position is interface convergence, not a table restatement.

## Changes Made

- Rewrote the four-owner introduction sentence so intent/agent-runtime, instruction, tool/interface, and runtime-observation/env are presented as proof responsibilities rather than component names.
- Compressed the benign Skill-manifest example to one union-authority argument.
- Reworked the evaluation method paragraph so saved-summary provenance is the main claim and platform/digest details are delegated to the evaluation ledger.
- Split baseline taxonomy into implemented wrapper baselines, interface-derived removal/composite baselines, and same-event/oracle scope.
- Made E2 claim-first in three places: trace characterization, three-class merge coverage, and weakened-variant results.
- Separated E3 deterministic adapter enforcement from Qwen3.6 proposer diagnostics.
- Moved the local Qwen env diagnostic numbers into `辅助诊断`.
- Reframed recovery evidence as constrained replacement safety and kept benchmark-scale utility as an open evidence boundary.
- Rewrote the limitations data boundary so missing historical paths are excluded provenance notes, not a primary-evidence weakness.
- Removed a related-work aside about lease-audit scope and made the closest-abstractions recap state the convergence condition directly.

## Rejected or Deferred

- Did not change any numeric results, run IDs, or evidence tokens. Round 9 is a writing-flow pass only.
- Did not remove the exact phrase for missing historical trace paths because the paper-number audit still checks that scope token. The paragraph now explains the phrase as an excluded provenance note.
- Did not start a new full experiment or model run. This round improves paper presentation and then verifies against saved artifacts.

## Verification Plan

- Run `scripts/audit_paper_evidence_numbers.py` with run id `R372PAPERAUDIT`.
- Run focused regression tests for the paper audit, protocol-gap analyzer, local task gateway, and local lease-corpus harness.
- Rebuild the Chinese paper with `latexmk -g -xelatex`.
- Run `git diff --check`.

## Verification Results

- `R372PAPERAUDIT` passed 192/192 paper-facing number and scope-token checks. The audit reads saved summaries only and records no model/tool/clone/sync/download.
- Focused tests passed: `74 passed in 0.21s`.
- `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` completed successfully and produced a 55-page PDF. The generated PDF/XDV build artifacts were not committed.
- `git diff --check` reported no whitespace errors.
