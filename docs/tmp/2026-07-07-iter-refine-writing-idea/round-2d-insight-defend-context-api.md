# Round 2d: Insight Defense with Context Inputs and Lease API

Date: 2026-07-07

## Trigger

Round 2c's re-attack argued that the paper could still be dismissed as a conventional stateful authorization policy with transactional updates. The user also pointed out a missing modeling axis: Skills/manuals, tools, local commands, and the agent itself carry different kinds of context, and the actual capability should be synthesized from those contexts jointly.

## Change

The paper now makes authority inputs explicit. Capability synthesis is defined over four context classes:

- `agent context`: user intent, selected objects/sinks, approvals, role, parent lease, and workflow state.
- `instruction context`: system/developer/user instructions, Skill/manual workflow text, `SKILL.md`, reference files, and MCP prompts.
- `tool context`: MCP/tool schema, descriptions, annotations, server identity, credential scope, local command descriptors, side-effect declarations, and sandbox contracts.
- `env context`: selected files, cwd/filesystem state, concrete arguments, tool results, script outputs, subagent summaries, runtime evidence, resource availability, and lease consumption state.

The formal section now writes lease synthesis as:

```tex
\kappa \in Solve_\Gamma(C_{agent}, C_{inst}, C_{tool}, C_{env}) .
```

The checker interface is also made explicit:

```tex
mint(\kappa)
check_and_consume(e,\kappa)
attenuate(\kappa_parent,K_c)
expire(\kappa)
```

The intended novelty claim is no longer just "provenance + intent + capabilities". It is that IntentCap binds four context classes, trusted mint provenance, decision-specific influence authority, consumption/expiration, and delegation attenuation into one authority-changing lease transition.

## Paper Edits

- Added `Authority Inputs` subsection to `docs/autopaper/intentcap-paper-zh.tex`.
- Replaced the previous three-way `agent/extension/runtime` input model with the four-way `agent/instruction/tool/env` model.
- Added formal `Solve_\Gamma(C_{agent}, C_{inst}, C_{tool}, C_{env})` notation.
- Added the checker's explicit authority-changing API.
- Added a split-state failure trace and E3 split-state stateful policy baseline.
- Updated related-work positioning so semantic-equivalent baselines must bind the same four context inputs into the same transition API.

## Verification

Ran:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
rg -n "undefined|Citation|Error|Fatal|Overfull" docs/autopaper/intentcap-paper-zh.log || true
```

Result: compile succeeded; no undefined references, citation warnings, fatal errors, or overfull boxes were reported after the final pass.

## Remaining Risk

The next re-attack should test whether reviewers can still reduce the contribution to "a transactional ABAC/IFC policy." If so, the paper needs an even sharper argument that the transaction boundary is agent-specific: protected future decisions, instruction/tool/env context separation, and lease consumption before side effects.
