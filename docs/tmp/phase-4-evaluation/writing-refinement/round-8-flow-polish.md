# Round 8: Flow Polish

Scope:
- Target file: `docs/autopaper/intentcap-paper-zh.tex`
- Focus: local transitions and ending emphasis.

Changes made:
- Added a transition after the protected-decision motivation to state that the decision classes define the shared boundary for the threat model, lease language, and evaluation oracle.
- Reordered the conclusion so the final sentence lands on the paper's core claim: making context-to-decision influence checkable, consumable, and auditable authorization state.

Why this matters:
- The paper now connects its motivating examples to the formal and evaluation boundaries more directly.
- The ending no longer closes primarily on missing experiments; it acknowledges E1--E4 as evidence requirements, then closes on the thesis.

Verification:
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded before this log was added.

Remaining work:
- Round 9 citation gate remains.
