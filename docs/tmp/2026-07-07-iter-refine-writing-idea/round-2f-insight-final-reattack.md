# Round 2f: Final Re-Attack on Four-Context Boundary

Date: 2026-07-07

## Reviewer Verdict

The four-context framing is now more than taxonomy. The paper presents `agent context`, `instruction context`, `tool context`, and `env context` as authority input boundaries, formalizes no context-class promotion, names collapsed/misclassified-context baselines, and positions IntentCap as an agent-specific transaction boundary. The strongest remaining attack has moved from novelty framing to evidence: the system needs implementation and experiments that exercise all four boundaries, especially local command/env and ActPlane-style lowering.

## Changes Made

- Split the system contribution so implemented components are distinct from ActPlane-style/full sandbox lowering targets.
- Clarified `agent context` versus `env context`: agent context carries user intent, approval, workflow, and delegation root; env context carries observed facts/results/resources and cannot forge lease state.
- Strengthened no-promotion text: one context class cannot supply another class's missing authority field.
- Made `check_and_consume` the required pre-side-effect gate for tool calls, MCP calls, local commands, approval requests, lease minting, policy updates, and delegation.
- Added a four-context residual attack table covering env-as-instruction, tool-metadata-as-intent, Skill approval widening, and subagent delegation expansion.
- Added an implementation adapter surface table that distinguishes implemented, trace-level, and design-target adapters, including ActPlane-style env backend status.

## Verification

Ran:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
rg -n "undefined|Citation|Error|Fatal|Overfull" intentcap-paper-zh.log || true
```

Result: compile succeeded; no undefined references, citation warnings, fatal errors, or overfull boxes were reported.

## Round 2 Status

Round 2 can move to contribution-goal alignment. The idea-layer framing is now defensible enough to proceed: the protected object is future agent decision authority; the authorization unit is the four-context intersection; the lease is a consumable authority transition object. The next risk is evidence/implementation alignment, not the central idea.
