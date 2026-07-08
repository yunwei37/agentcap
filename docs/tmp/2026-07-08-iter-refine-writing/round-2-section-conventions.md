# Round 2: Section Conventions

Date: 2026-07-08

## What Was Checked

Round 2 checked section-specific conventions in `docs/autopaper/intentcap-paper-zh.tex`: abstract beats, introduction role separation, design goal conventions, evaluation/RQ alignment, related-work grouping, and conclusion structure. The read-only reviewer used `check-paper-structure-flow` with section-convention focus and checked the common pitfalls file.

## Findings

Must-fix findings:

- Abstract still read like mechanism definition plus pilot report, and the phrase "当前 prototype and pilot workloads" made the paper feel unfinished.
- Intro roles were clearer than before but still dense around thesis, technical challenge, lease mechanism, and system architecture.
- Contribution C3 still sounded like a project-stage contribution instead of a paper evaluation contribution.
- Evaluation E1--E4 still read partly like a proposal. Each experiment needed a clearer RQ/setup/metric/interpretation shape.
- E3 listed too many variants and did not foreground the central claim that a unified protected-decision transaction is necessary.
- Evidence Boundary looked like a progress report rather than a conventional limitations/scope section.

Should-fix findings:

- Design Goals mixed motivating trace, mechanism requirements, and goal taxonomy in one paragraph.
- System Overview lacked a concrete request path walkthrough.
- Evaluation Methodology needed an experimental matrix.
- Related Work should start with a grouping paragraph and reduce defensive semantic-equivalence prose.
- Conclusion should restate thesis, mechanism, key numbers, and implication rather than referring to E1--E4 plan names.

Consider findings:

- Mixed English subsection titles and coined-term density remain high; this is deferred to terminology/language rounds.
- Claim posture should stop expanding mechanisms and prioritize core experiments.

## Changes Made

- Changed the abstract result sentence to prototype-evaluation prose and removed "当前 prototype/pilot workloads" wording.
- Tightened the intro distinction between thesis, technical challenge, lease mechanism, and compiler/checker architecture.
- Changed contribution C3 to `Evaluation`, reporting prototype evaluation coverage rather than project-stage methodology.
- Added a PDF workflow walkthrough to `System Overview`: issuer creates intent, labeler assigns four context planes, compiler proposes effects, checker mints/consumes leases, and adapters enforce before side effects.
- Split the Design Goals lead-in and changed the goal-map caption to a neutral mapping caption.
- Added Table `Evaluation matrix` mapping E1--E4 to workloads, baselines, primary metric, and supported claim.
- Rewrote E3 around three core baselines: object/action guard, IFC/provenance guard, and split-state composite guard.
- Renamed `证据与主张边界` to `范围与局限`, with `Prototype Evidence` and `Limitations` subsections.
- Replaced `Evidence / Boundary` phrasing with `Evidence / Scope`.
- Added a Related Work grouping paragraph and shortened the defensive semantic-equivalence discussion.
- Rewrote the conclusion to state mechanism plus key prototype numbers directly.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` from `docs/autopaper`.
- Checked the LaTeX log for undefined citations, undefined references, LaTeX warnings, and overfull boxes; no matching warnings were found.
- Searched for stale progress-report phrases such as `当前 prototype`, `当前 artifact`, `claim boundary`, `Evidence Boundary`, `Claim Boundaries`, `full-paper`, `TODO`, and `Not yet`; no stale matches remained.
- Cleaned generated LaTeX artifacts before committing.

## Remaining Concerns

- The paper still reports prototype/pilot-level evidence. That is now framed as scope and limitations, but the research still needs stronger E1--E4 data to support a top-conference full-paper claim.
- Section titles are still mixed Chinese/English. Terminology and language rounds should decide whether to localize them.
- Evaluation prose is structurally cleaner, but later logic-flow and consistency rounds should check whether every claim in abstract/conclusion is fully supported by a table or result paragraph.
