# Round 4: Cross-Alignment

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Mill`, read-only. The reviewer checked problem, insight, design goals, contributions, evaluation, limitations, and related work alignment.

## Findings

Must-fix:

- Abstract, intro, and conclusion over-emphasized E1/E4 safety numbers while under-reporting E3, even though E3 supports the core novelty claim around issuer-owned atomic transitions.
- E3 title and first paragraph overclaimed `necessity`, while the section itself correctly admits independent field-owner labels and more natural events are still future gates.
- System overview still said context/delegation were validated as trace-level events, conflicting with later local live probe descriptions.

Should-fix:

- G3 mapped to E2, but E2 is auditability rather than lifecycle safety evidence.
- C2/G4 needed clearer MCP scope: tool/MCP policy events are part of the transition model, while current MCP evidence is trace-derived/residual, not production broker integration.
- E2 should be explicitly auxiliary.
- Related-work table's `Default root` column was ambiguous.

## Changes

- Abstract, intro result paragraph, and conclusion now report E3 ablation evidence: 48/48 MCPTox-derived policy/approval promotions and 3/3 Skill instruction-source substitutions rejected by IntentCap but accepted by weakened variants.
- E3 is retitled `Ablation Evidence for Issuer-Owned Atomic Transitions`; the opening now says `necessity-oriented ablation`, not completed necessity proof.
- System overview now says context placement, Skill instruction placement, and delegation handoff are tested by local live probes; benchmark-derived traces are for large-scale semantic replay.
- G3 now maps to E3/E4, not E2.
- Evaluation opening and matrix mark E2 as auxiliary auditability evidence, not a main expert-oracle safety claim.
- Related-work table column is now `Run-intent mint root`, with a caption definition.

## Remaining Concerns

- Cross-alignment is materially improved, but the same evidence gates remain: independent field-owner adjudication, more natural protected-decision false-accept rates, production boundary integration, and end-to-end utility/recovery.
- The paper is now longer and needs writing-refine compression after idea rounds finish.
