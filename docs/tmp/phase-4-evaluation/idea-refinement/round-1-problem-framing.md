# Round 1: Problem Framing

Date: 2026-07-07

## What Was Checked

Problem framing in `docs/autopaper/intentcap-paper-zh.tex`, especially introduction paragraphs around lines 32--38, against `iter-refine-writing-idea/references/idea-quality-checklist.md` Section 1.

## Findings

Subagent reviewer (problem framing) reported:

> Lines 34-38 say untrusted context can lead to an action that is operation-allowed but source-unauthorized, but they do not explicitly explain why provenance is structurally lost in the agent pipeline.

> The critique of tool guards, static allowlists, human approval, and OS sandboxing is too fast and can read as a straw man because some existing systems already address provenance, IFC, or intent/action policies.

> The introduction covers Skills, MCP, local programs, subagents, OAuth scope, skipped checks, and delegation without early limiting the protected decision classes, creating scope creep risk.

> The PDF example can be trivially countered by exact repo argument validation; the stronger distinction is decision-source authorization for approval scope, delegation, policy, and capability requests.

## What Was Changed

- Before line 34: the paper stated that text can become a control signal and called this `context privilege`, but it did not show the pipeline where control provenance is lost.
- After line 34: the paper now describes the structural path: agent runtime co-locates trusted and untrusted context, the model emits plans/arguments/approval/delegation decisions, and downstream guards see the final operation but not which context controlled security-relevant fields.

- Before line 36: the example emphasized wrong GitHub repository selection, which an exact argument validator could block.
- After line 36: the example keeps repo argument validation as useful but insufficient, and shifts the hard case to PDF influence over approval scope, Skill loading, delegation target, capability request, and unrelated data inclusion.

- Before line 38: existing defenses were described broadly as not answering the earlier decision-source question.
- After line 38: the text now states a bounded set of protected decisions and frames existing defenses as necessary but not assigning influence authority to context sources.

## Verification

Ran:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Existing font/box warnings remain; no fatal LaTeX errors.

## Remaining Concerns

The problem framing is sharper, but the thesis still needs an adversarial novelty pass: a reviewer can still argue this is provenance/IFC plus capability packaging unless the insight sentence makes the new decomposition explicit.
