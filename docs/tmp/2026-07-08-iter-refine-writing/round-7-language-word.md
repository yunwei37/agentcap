# Round 7: Language - Word Choice

Date: 2026-07-08

## Findings

Read-only reviewer `Ohm` invoked `paper-writing-style` with focus on word choice and checked `references/common-pitfalls.md`.

Must-fix findings:

- Abstract result sentences were in abrupt English and read like an experiment ledger.
- Introduction paragraphs inserted English note-style prose (`Realizing this view`, `A lease is`, `Runtime adapters lower`) into Chinese text.
- Contribution bullets used artifact/status vocabulary such as `implemented checker core`, `pre-side-effect probes`, and `authority-surface/utility slice`.
- Design and implementation repeated overlapping compound terms: `transaction API`, `adapter contracts`, `lowering target`, and `checker verdict`.
- Authority Inputs used abrupt English wording for raw user text.
- Evaluation and scope sections used `system claim`, `model-loop probes`, `slice`, and project-status phrasing.
- Related work buried the contrast under a long stack of coined mechanism terms.
- Conclusion repeated abstract numbers in experiment-log style.

Should-fix findings:

- Intro and background mixed English phrases such as `failure trace`, `gap`, and `full GitHub approval`.
- Definition sections overused `protected-decision transition`, `protected events`, and `decision classes` in close succession.
- Authority Inputs overused `plane`; after definition, prose should prefer `四类输入` or `四类来源`.
- Context Authority mixed `lowering`, `mapping`, and `lattice` without a clean hierarchy.
- Effect IR used reviewer-note phrases such as `fail closed`, `utility cost`, and `provenance always precise`.
- Compiler section used colloquial terms like `authority escape hatch` and `broad permission fallback`.
- Implementation and evaluation used repeated English openings (`The setup`, `The prototype result`, `The real local probe`).

## Changes Made

- Rewrote abstract and conclusion result sentences in Chinese while preserving all numbers.
- Converted the English introduction mechanism paragraphs into Chinese prose with only necessary technical terms retained.
- Rewrote C2/C3 so they describe the mechanism and evidence contribution instead of listing implementation status artifacts.
- Standardized the main design phrase around `checker 仲裁的状态转移接口` and removed repeated `transaction API`, `adapter contracts`, and `checker verdict` wording.
- Replaced `Raw user text itself is not a fifth plane` with Chinese authority-input wording.
- Reframed implementation and evaluation sections around what each experiment tests, rather than project status.
- Renamed the evidence subsection to `Evidence Boundary` and rewrote scope/limitations with explicit subjects.
- Rewrote related-work contrast as a plain lifecycle/object-granularity difference before listing mechanisms.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- Warning scan for undefined citations/references, LaTeX warnings, and overfull boxes returned no matches.
- `git diff --check` passed.
- Term regression check: `prototype`, `probe`, `transaction API`, `adapter contracts`, `Prototype evaluation`, and `saved security traces` no longer appear in the paper source.

## Remaining Concerns

- Core terms such as `context`, `authority`, `lease`, and `checker` remain frequent because they are the paper's central vocabulary. Round 8 should check whether each is defined early enough and whether any invented compound term still sounds unsupported.
- Some tables still use compact English labels for space. Round 9 can improve table/caption flow if needed.
