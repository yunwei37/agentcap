# Round 1 - Problem Framing

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- `iter-refine-writing-idea` checklist Section 1: concrete pain, root cause, non-straw-man gap, and scope.

Findings:
- Must fix: the introduction did not make the failure consequence concrete enough before introducing IntentCap vocabulary.
- Must fix: the root cause still sounded like solution terminology; it needed a system-independent explanation of mixed planning channels and post-hoc guards.
- Must fix: the four context classes were well-defined in design but not motivated early enough from collapsed-context failure modes.
- Must fix: scope boundaries were spread across the paper and should be stated near the protected-decision definition.
- Should fix: existing guards should be acknowledged more precisely to avoid straw-man framing.
- Should fix: the framing should include over-privilege, approval fatigue, auditability, and workflow breakage, not only prompt-injection security.
- Should fix: the contribution list should not read like an internal proposal status.

What changed:
- Abstract line 25: replaced the project-status result sentence with a concrete current-evidence sentence covering 3,746 protected events, local env model-loop side effects, and the 18-task local-Qwen comparison.
- Introduction lines 32-34: replaced the solution-like root-cause paragraph with a concrete failure trace and a system-independent root cause: mixed planning channel plus post-hoc guards.
- Introduction line 36: added collapsed-context failures for Skill/manual text, MCP/tool metadata, script output, and tool results, tying the four context classes to problem framing.
- Introduction line 38: moved the protected-decision scope boundary near the first definition of protected decisions.
- Introduction line 40: rewrote related-defense framing to acknowledge tool guards, approvals, sandboxes, monitors, provenance, taint, and IFC, then isolate the residual gap as missing stateful future-decision authority.
- Contribution line 53: changed the evidence contribution from "final version must replace this" to a bounded evaluation/evidence contribution with explicit claim separation.
- Motivation lines 75-91: added Table `tab:motivation-context-boundary` showing allowed/forbidden influence and collapsed-context consequences.

Verification:
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`
- `rg -n "undefined|Citation|Error|Fatal|Overfull|LaTeX Warning" intentcap-paper-zh.log || true`
- Result: build succeeded; final warning grep returned no hard warnings.

Remaining concerns:
- The abstract is still long and mixes English technical terms with Chinese prose; this belongs to writing refinement after the idea-level rounds.
- The paper remains evidence-bound rather than full-result final; this is intentional until recovery/approval and adversarial workloads close the remaining E1 gate.
