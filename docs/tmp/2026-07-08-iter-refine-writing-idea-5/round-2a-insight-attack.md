# Round 2a: Insight Attack

Date: 2026-07-08

## What Was Checked

Checked the paper's insight and novelty framing in `docs/autopaper/intentcap-paper-zh.tex`, focusing on whether reviewers could dismiss the idea as provenance/IFC plus capabilities, AuthGraph/PACT/AIRGuard plus state, a Skill/MCP policy framework, EIM/bpftime for agents, or ActPlane policy synthesis.

## Findings

Strongest skeptical reviewer attack:

- The current paper can look like "provenance/IFC + capabilities + stateful policy DSL" because it lists components but does not make the non-obvious insight sharp enough.
- The novelty should not be framed as "a DSL cannot encode this predicate." It should be framed as a different runtime authorization object and adapter contract.
- "Four classes" can sound like an artificial taxonomy unless the paper states the merge criterion and the four different proof questions.
- A stateful lease can sound like an ordinary capability lease unless the paper gives a same-action/same-provenance but different-authority-state example.
- The system contribution can sound like a checker without system depth unless it stresses the protected-transition API across prompt placement, Skill instruction placement, tool/MCP, runtime/env side effects, and delegation handoff.

## Remaining Concerns

- Round 2b should sharpen the thesis around protected-decision transitions, not broaden claims beyond the current evidence.
- Round 2c should re-attack whether the updated paper still reads as policy-DSL packaging.
