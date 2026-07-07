# Round 3: Logic Flow

## Reviewer Focus

Checked the paper as a skeptical systems reviewer: whether the central claim follows from the problem statement, whether design promises match implementation, and whether evaluation baselines are described at a defensible level of fidelity.

## Main Logic Risks Found

1. The threat model said enforcement adapters are in the TCB, while the implementation section later says the prototype does not include a full production MCP broker or OS sandbox. Without clarification, this could read as overclaiming the implementation.
2. Runtime Lowering listed context/tool/MCP/sandbox/delegation adapters as if they all exist at the same maturity level. The implementation only instantiates a subset.
3. E3 named close related systems as baselines. If the paper does not reproduce those systems exactly, the evaluation must say it implements semantic checker variants over the same event schema.

## Fixes Applied

1. Clarified that the TCB statement is per connected boundary: uninstrumented side effects are outside the safety properties.
2. Clarified that Runtime Lowering describes design contracts, while the Implementation section reports the subset instantiated in the prototype.
3. Clarified that the Python prototype verifies the lease language, deterministic checker, and lowering to trace replay/live callable/benchmark-derived workflows, not every production adapter.
4. Clarified that E3 related-work baselines must be written as semantic variants when exact system reproduction is unavailable.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The next consistency pass should check whether every claim in Abstract/Introduction/Discussion uses the same evidence boundary language now introduced in Threat Model, Design, and Implementation.
