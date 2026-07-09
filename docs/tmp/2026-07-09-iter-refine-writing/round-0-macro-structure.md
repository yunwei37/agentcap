# Round 0 — Macro Structure

Date: 2026-07-09

## Findings (from subagent)

### Applied
- **Must-fix 2**: Removed `\paragraph{Four authority-input classes.}` and `\paragraph{Leases and lifecycle.}` — common-pitfalls bans \paragraph{} in short papers
- **Must-fix 3**: Removed `\textbf{RQ1-4}` bold run-in headers — common-pitfalls bans bolded lead-in phrases as \paragraph in disguise. Replaced with topic sentences ("To test whether...")
- **Should-fix 3**: Consolidated related-work positioning — Intro P4 (EIM/bpftime/ActPlane/SkillGuard) removed; content moved to Discussion section
- **Consider 3**: Renamed "Positioning" → "Discussion"
- **Should-fix 2**: Added future work sentences to Discussion

### Skipped
- **Must-fix 1**: Splitting Introduction into Background + Motivation — skipped; Introduction is standard for 2-page workshop papers, and this template requirement is overly prescriptive
- **Should-fix 1**: Moving root-cause to Motivation — skipped since we keep Introduction
- **Consider 1**: Abstract ~280 words — abstract now unfrozen per user, may trim in later rounds
- **Consider 2**: Reducing to 2 RQs — skipped; 4 RQs are concise and each adds distinct evidence

## Changes Made
- Design: \paragraph{} headers removed, prose flows naturally
- Evaluation: RQ labels removed, woven into topic sentences
- Intro P4 (related work comparison): removed entirely
- Positioning → Discussion: renamed, merged related work, added future work paragraph
- Citations: 5 \cite{} calls preserved (moved, not deleted)

## Compile: 2 pages, no errors
