# Iter Refine Writing Round 4: Abstract/Intro Rebuild

Date: 2026-07-10

Skill workflow: `iter-refine-writing`, Round 4 abstract/intro rebuild.

Direct skill used: `rewrite-abstract-intro`.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

## What Was Checked

I read `rewrite-abstract-intro/references/abstract-intro-structure.md` and `iter-refine-writing/references/common-pitfalls.md`, then mapped the current abstract and introduction against the full-paper convention: context, problem, root cause, existing-solutions limitation, insight, challenges, this-paper/results, and contributions. The paper body was used as the source of truth for claims and numbers.

## Mapping Diagnosis

| Current text | Current role | Target role / action |
|---|---|---|
| Abstract sentences 1--2 | Context + problem mixed | Keep context first, then state context-influence problem |
| Abstract sentences 3--4 | Problem + consequence | Keep, but make the problem flow from context to authority-bearing decisions |
| Abstract sentences 5--7 | System/mechanism | Keep system name, four proof owners, and checker outside LLM TCB |
| Abstract sentences 8--9 | Results | Keep audited numbers and multi-boundary result |
| Intro paragraph 1 | Background + root cause mixed | Make it pure background/context |
| Intro paragraph 2 | Problem example | Keep PDF-to-issue example as concrete pain |
| Intro paragraph 3 | Root cause | Keep as separate structural-cause paragraph |
| Intro paragraph 4 | Existing work + defensive equivalence boundary | Keep existing-work limitations, move defensive boundary out of intro |
| Intro paragraph 5 | Insight | Keep four proof owners and pre-effect commit insight |
| Intro paragraph 6 | Challenges | Keep three implementation challenges, split semicolon chains |
| Intro paragraph 7 | This paper + example | Keep system mechanism, remove detailed PDF replay from intro |
| Intro paragraph 8 | Evaluation | Keep primary results and move scope caveat to Discussion |
| Intro paragraph 9 | Contributions | Keep three contributions |
| Intro final scope paragraph | Boundary/caveat | Remove from intro because `讨论与局限` already carries the boundary table |

## Reorganization Plan

The rebuilt opening follows the canonical chain:

1. Background: agents are extensible execution environments.
2. Problem: context can influence authority-bearing decisions.
3. Root cause: no first-class pre-effect authorization object records who proves each authority field and how lifecycle state changes.
4. Existing-solutions limitation: tool guards, approval gates, OS monitors, and IFC/provenance defenses inspect formed actions, resources, flows, or syscalls rather than the protected-decision transition.
5. Insight: pre-effect commit record plus four proof owners is the authorization unit.
6. Challenges: owner separation, checker-owned lifecycle state, and multi-boundary exposure.
7. This paper/results: leases, checker, prototype, and audited E1/E2/E3 numbers.
8. Contributions: model, runtime contract/prototype, bounded evaluation evidence.

## Changes Applied

- Rewrote the abstract into context/problem/system/results order without adding new claims or numbers.
- Rewrote the introduction paragraph by paragraph to keep paragraph roles unmerged.
- Removed the defensive end-of-intro scope paragraph and left evidence boundaries in `讨论与局限`.
- Kept all existing citation groups in the opening.
- Split new semicolon chains in the abstract and introduction to match the common-pitfalls language rules.

## Verification

- `PYTHONPATH=src:. python3 scripts/audit_paper_evidence_numbers.py --run-id R367PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R367PAPERAUDIT`
- Result: 192/192 paper-facing evidence checks passed, 0 failures.
- The audit reported `no_dataset_sync=true`, `not_a_model_run=true`, and `not_a_new_experiment=true`.

## Remaining Concerns

The opening is now more conventional, but the paper body is still technical-report length. The next writing rounds should check whether the new introduction remains consistent with later terminology and whether the main paper should move E2 adjudication details and E3 per-surface provenance into appendix material.
