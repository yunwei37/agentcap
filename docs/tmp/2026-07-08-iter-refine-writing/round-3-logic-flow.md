# Round 3: Logic Flow

Date: 2026-07-08

## What Was Checked

Round 3 checked whether the paper's claims are supported by the body: abstract/conclusion vs evaluation, C1-C3 vs design/formal/implementation/evidence, implementation scope vs system contribution, and whether the four-plane novelty claim overreaches beyond current prototype evidence. The read-only reviewer used `critique-like-senior-systems-reviewer` with logic-flow focus and checked the common pitfalls file.

## Findings

Must-fix findings:

- Abstract and conclusion gave concrete result numbers, but Evaluation still read like E1-E4 experiment design. Claim and evidence did not close.
- C3 was titled `Evaluation`, but current evidence is prototype-level: wrapper matrix, local env suite, Qwen probe, and author-adjudicated labels.
- C2 overclaimed cross-boundary adapters relative to implementation: instruction/delegation are trace-level contracts, ActPlane is an optional target, and production MCP broker/sandbox are not implemented.
- E1-E4 contained planning language and conditional claim statements.
- E2 could not support expert-oracle least privilege because current labels are author-adjudicated.
- E3 could support controlled residual attack results, but not benchmark-scale prevalence of four-plane necessity.

Should-fix findings:

- The formal model needed to foreground the three core invariants.
- Scope and limitations sounded like a project status report.
- Related-work comparison table should be read as first-class object coverage, not as "prior work cannot encode this."
- ActPlane positioning should be aligned with the system contribution: transaction API plus adapter contract, with ActPlane-style monitoring as an env adapter backend.

## Changes Made

- Updated abstract result sentence to include 3,813 benign reference-action coverage and phrase results as prototype evaluation.
- Narrowed C2 to a checker-centered transaction API with implemented tool/MCP and local-env gateways, trace-level instruction/delegation contracts, and an ActPlane-style env-side lowering target.
- Renamed C3 to `Prototype evidence and evaluation methodology`.
- Added three formal invariants at the start of the formal model: no substitution, atomic check/consume, and no promotion.
- Rewrote Evaluation as completed prototype evidence:
  - E1 now reports the 3,746-event safety matrix, 3,813/3,813 reference-action coverage, 2,554/2,556 tool-oracle proxy pass rate, and the 18-task local-Qwen utility boundary.
  - E2 now reports 24/24 author-adjudicated lease-label audit pass rate and explicitly avoids expert-oracle claims.
  - E3 now reports controlled residual-suite mechanism evidence and bounds the result away from benchmark-scale prevalence.
  - E4 now reports local env side-effect and Qwen3.6 model-loop results with unsafe side effects blocked before handlers run.
- Rewrote Scope/Limitations as normal scope assumptions rather than future-claim conditions.
- Shortened E3 wording to remove an overfull hbox.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` from `docs/autopaper`.
- Checked the LaTeX log for undefined citations, undefined references, LaTeX warnings, and overfull boxes; no matching warnings were found after the E3 line fix.
- Searched for stale planning markers including `does not yet`, `not yet`, `must add`, `full-paper`, `TODO`, and `claim boundary`; no matches remained.
- Cleaned generated LaTeX artifacts before committing.

## Remaining Concerns

- The paper is now logically consistent as a prototype-evaluation paper, not as a final top-conference result paper.
- To make the strongest OSDI/NeurIPS-style claims, the project still needs benchmark-scale E1/E3, independent E2 adjudication, and stronger E4 recovery/utility runs.
- Later writing rounds should reduce bilingual term density and verify citation/table precision.
