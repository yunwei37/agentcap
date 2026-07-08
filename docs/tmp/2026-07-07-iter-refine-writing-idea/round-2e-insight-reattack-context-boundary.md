# Round 2e: Re-Attack on Four-Context Boundary

Date: 2026-07-07

## Reviewer Verdict

The new four-context framing is stronger, but a skeptical reviewer can still reduce the design to a transactional ABAC/IFC/provenance policy unless the paper treats the four contexts as system boundaries rather than taxonomy. The attack changed from "this is just taint/provenance" to "this is a stateful policy engine." The defense must therefore make the protected object agent-specific: future decision authority at prompt construction, instruction ingestion, tool exposure, local execution lowering, approval requests, and delegation.

## Findings Applied

- The abstract and introduction now state that authority is the checked intersection of `agent context`, `instruction context`, `tool context`, and `env context`.
- The `Authority Inputs` subsection now defines the four contexts as a table with issuer/trust source, examples, allowed influence, forbidden influence, and enforcement adapter.
- The formal model now includes `No Context-Class Promotion`: env/tool/instruction context cannot be used as a higher-authority class unless a trusted issuer explicitly endorses it.
- Runtime lowering now defines explicit adapter contracts: agent adapter, instruction adapter, tool adapter, env adapter with sandbox/ActPlane-style backend, and delegation adapter.
- E1 and E2 now require workloads that cover instruction, tool, env, agent, and delegation boundaries.
- E3 now includes `collapsed-context` and `misclassified-context` baselines, plus no-promotion in the lifecycle ablation set.
- The current evidence table now marks which context classes each pilot result covers.
- Related work now states the narrower claim: IntentCap is an agent-specific transaction boundary, compiler/checker organization, and multi-boundary runtime realization, not a claim that no transactional policy could express equivalent rules.

## Verification

Ran:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
rg -n "undefined|Citation|Error|Fatal|Overfull" intentcap-paper-zh.log || true
```

Result: compile succeeded; no undefined references, citation warnings, fatal errors, or overfull boxes were reported after the final pass.

## Remaining Risk

The paper still needs experiment evidence that directly exercises the four-context boundary. The highest-value missing pieces are:

- Fresh/broader online utility/security comparison, not only saved trajectory replay.
- A benchmark-derived or model-loop residual case where collapsed/misclassified context baselines fail.
- A local command/script or ActPlane-style env enforcement case.
- Broader Skill/manual instruction cases beyond the partial current evidence.
