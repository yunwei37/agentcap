# Round 0: Macro Structure

Date: 2026-07-07

## Findings

The structure reviewer reported several macro-level issues:

- The draft did not yet follow a full systems-paper spine because it lacked Background, Motivation, Discussion/Limitations, and Conclusion sections.
- The Design section described a five-step data flow but lacked an architecture figure with trust boundaries and component responsibilities.
- Design and Implementation were still mixed because Runtime Lowering described artifact completion status.
- Implementation and Related Work used `\paragraph{}` run-in headings instead of section-level structure.
- Evaluation had the right four-experiment direction, but the section title and surrounding text still read like an evaluation plan rather than a mature full-paper evaluation.

## Changes Made

- Added `背景` with subsections for agent extensions and authority/provenance.
- Added `动机` with the PDF/GitHub running example and protected-decision taxonomy.
- Added a TikZ architecture figure in Design showing trusted issuer, context labeler, untrusted LLM compiler, deterministic checker, and runtime adapters.
- Moved Design wording toward lowering contracts and kept artifact-completion wording in Implementation.
- Converted all `\paragraph{}` run-in headings into `\subsection{}` headings.
- Renamed `评估设计` to `评估`.
- Renamed `证据状态与局限` to `讨论与局限`.
- Added a `结论` section that states the current conservative claim and experiment-dependent claim gates.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. The generated PDF is 19 pages in the current draft format. Remaining warnings are font and underfull table/prose warnings.

Additional checks:

```text
rg -n '^\\(section|subsection|paragraph)' docs/autopaper/intentcap-paper-zh.tex
rg -n '\\paragraph\\{' docs/autopaper/intentcap-paper-zh.tex || true
```

Result: section structure now includes Background, Motivation, Discussion/Limitations, and Conclusion; no `\paragraph{}` headings remain.

## Remaining Concerns

The paper still needs later writing rounds to remove duplicated intro/background motivation, tighten abstract structure, and turn C3 from evaluation plan plus pilot evidence into measured evidence once E1/E3/E2 are complete.
