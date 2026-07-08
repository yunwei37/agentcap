# Round 0: Macro Structure

Date: 2026-07-08

## What Was Checked

Round 0 checked whether `docs/autopaper/intentcap-paper-zh.tex` reads like a coherent full-paper scaffold rather than a loose extended abstract or experiment log. The review focused on section order, design/evaluation separation, whether system contribution is visible, and whether current pilot evidence is separated from final claims.

## Findings

- Must-fix: the paper mixed "extended abstract" wording with a full-paper scaffold. This weakens the claim boundary because the document now contains design, implementation, formal model, evaluation plan, evidence status, and related work.
- Must-fix: threat model and design goals were mixed in the same section. Threat model should state assumptions, attacker, TCB, and non-goals; goals belong at the start of Design.
- Must-fix: Evaluation contained a local E3 pilot paragraph inline, which made the section feel like a run log. The four experiments should define full-paper obligations; pilot evidence belongs in the evidence boundary section.
- Should-fix: Background and Motivation were too thin as independent sections. They now form one `背景与动机` section with the running example as a subsection.
- Should-fix: the system contribution needed to be visible as more than MCP/tool-call guarding. The contribution and runtime design now emphasize cross-boundary adapters and an ActPlane-style env-side lowering target.
- Consider: the formal section is still long and may need later micro-structure and language passes, but the current round did not rewrite it.

## Changes Made

- Renamed `背景` and merged `动机` into `背景与动机`, with `Motivating Workflow` as a subsection.
- Renamed `威胁模型与目标` to `威胁模型与非目标`; moved design goals out of threat model.
- Added `System Overview` and `Design Goals` at the beginning of `系统设计`.
- Clarified that the four context planes are system interfaces: agent context is issuer-maintained intent/approval/workflow state, instruction context is policy/Skill/manual guidance, tool context is schema/credential/sandbox contract, and env context is runtime facts.
- Strengthened C2 from prototype adapters to cross-boundary transaction adapters, including an ActPlane-style env-side lowering contract.
- Changed C3 and claim-boundary wording from "extended abstract" to "full-paper scaffold" / "current scaffold claim".
- Added `Evaluation Methodology` before E1.
- Moved the local E3 pilot paragraph out of E3's main experiment narrative by replacing it with a forward reference to `证据与主张边界`.
- Renamed `讨论与局限` to `证据与主张边界`.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` from `docs/autopaper`.
- Checked the LaTeX log for undefined citations, undefined references, LaTeX warnings, and overfull boxes; no matching warnings were found.
- Cleaned generated LaTeX artifacts before committing.

## Remaining Concerns

- The formal model is conceptually aligned, but later rounds should shorten or subdivide it so it does not read like a definition dump.
- E1--E4 remain mostly protocol plus pilot evidence. A final OSDI/NeurIPS-style claim still needs completed benchmark-scale experiments, stronger recovery data, and independent/blinded lease adjudication for E2.
