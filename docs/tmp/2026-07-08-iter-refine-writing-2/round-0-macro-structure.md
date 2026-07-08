# Round 0: Macro Structure

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Nietzsche`, read-only. The reviewer used the `check-paper-structure-flow` macro-structure checklist and `common-pitfalls.md`.

## Findings

Must-fix:

- Design mixed abstraction with implementation coverage and experiment status.
- Formal model was too long and contained residual examples that made the paper read like a formal/ledger hybrid.
- Implementation was too thin for C2 and did not clearly explain checker state, adapter invocation path, failure path, or side-effect blocking path.
- Evaluation, especially E4 and the evidence-status table, read like run ID ledger rather than claim-facing experiments.
- Threat model was too short for the strength of the later formal/eval claims.

Should-fix:

- Background subsections are short compared with motivation.
- Architecture caption carried implementation coverage status.
- Evaluation section weights were uneven.
- Limitations and evidence table repeated run summaries.
- English/Chinese subsection titles were inconsistent.

## Changes

- Expanded threat model into four paragraphs: attacker-controlled context, attacker goals, TCB, and per-boundary non-goals.
- Removed implementation coverage state from the design overview, G4, architecture caption, and transition-interface design paragraph.
- Shortened the formal model by deleting residual trace tables and replacing them with a concise split-guard interleaving explanation that points E3 to ablation evidence.
- Added implementation detail for checker state, adapter-submitted field proofs, atomic check/update, structured denials, and local env side-effect block point.
- Rewrote E4 from a run-by-run ledger into setup, baselines, metrics, results, and interpretation paragraphs.
- Marked the current-evidence table as an artifact summary rather than an additional main claim.
- Started normalizing Chinese subsection titles while preserving core technical terms.

## Remaining Concerns

- Formal model is still large and may need another writing round to compress further.
- Implementation is stronger but still shorter than Design/Formal; later rounds should keep shifting operational details out of Design and into Implementation.
- The artifact summary table is still long; a camera-ready paper should probably move it to appendix or an internal evidence ledger.
