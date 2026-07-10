# Round 2c - Insight Re-Attack

Date: 2026-07-09

## What Was Checked

Read-only adversarial re-attack after commit `8754353`, focusing on whether the revised paper can still be rejected as a renamed reference monitor, policy DSL, IFC/provenance system, or typed-capability engineering checklist.

## Findings

The reviewer found the revised version stronger than the previous pass: the pre-effect commit interface, four owner-equivalence classes, typed-provenance convergence baseline, and E1/E4 guardrail framing now appear in the paper.

The remaining strongest rejection argument was:

> This is essentially a linearizable reference monitor plus typed capabilities plus provenance/IFC labels; the four context classes are an engineering taxonomy, and the strong E3 baseline is only one delegation rule away from convergence.

Must-fix items:

1. State the insight as a new authorization granularity: a multi-issuer, lifecycle-mutating protected decision, not merely a checker or API.

2. Clarify that \(C=C_{agent}\uplus C_{inst}\uplus C_{tool}\uplus C_{env}\) is a disjoint union over canonical proof projections, not raw artifacts or components. A Skill, MCP server, command, or agent run can produce multiple proof cells.

3. Present R241 typed-provenance state guard as an equivalence-boundary result. If it adds parent-child lease comparison and same-transition child-state update, it implements the IntentCap commit interface on that residual class.

4. Tighten the attenuation rule from \(K_c\sqsubseteq K_\sigma\) to a parent-specific relation such as \(K_c\sqsubseteq K_{parent(a)}\).

Should-fix items:

1. Further weaken abstract wording around `0 unsafe accepts/executions` so those numbers do not read as the main security proof.

2. Later writing rounds should reduce repeated context-class tables.

3. Related-work matrices should emphasize default exposed runtime object instead of yes/no comparisons.

## Remaining Concerns

After fixing the must-fix items, the remaining risks are mostly evidence scope and writing compactness: independent labeling, benchmark-scale online recovery, production ActPlane/kernel enforcement, and table redundancy.
