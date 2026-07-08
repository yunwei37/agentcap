# Round 2b: Insight Defense

Date: 2026-07-08

## What Was Changed

- Introduction, line 42 before edit: described the core idea as an atomic lease object but did not define the minimum interface.
  After edit: rewrote the insight as a testable proposition: the authorization unit is a protected-decision transition. Added the minimum transaction interface: issuer-typed required fields, control-provenance proof, `mint`, `check_and_consume`, `attenuate`, `expire`, atomic checker state update, and adapter calls before side effects or authority transfer. Also stated which residual appears when each part is missing.

- System design, after the architecture figure before edit: distinguished IntentCap from tool allowlists but did not foreground the system-level adapter contract.
  After edit: added that IntentCap is a central transaction API plus adapter contracts. Tool/MCP, env, instruction placement, and delegation adapters must call the checker before side effects, prompt authority placement, or authority transfer. ActPlane is positioned as an env backend, not the core authorization model.

- Formal model, after `Req(d)` before edit: four context planes could still be read as ABAC attribute namespaces.
  After edit: added issuer-typed authority fields and a no-substitution typing rule. A field proof is valid only if the proof issuer matches the field owner. Trusted tool metadata can prove schema fields but cannot prove a user-authorized sink.

- Context authority, line 250 before edit: said this is not merely a taint-label policy dimension but did not give a concrete contrast.
  After edit: added a PDF example showing IFC can allow PDF text to flow into issue body, while IntentCap also requires the repo field's agent-plane issuer, a PDF-free approval-scope control proof, and an unconsumed one-shot lease.

- Evaluation E3, before edit: listed ablations and the composite baseline but did not require workload characterization.
  After edit: added E3's first step as workload characterization across AgentDojo, MCPTox, InjecAgent, and tau2-style traces, and required the strongest split-state composite baseline. The text now says that if the baseline adds the unified lease API and passes, it has adopted the paper's abstraction.

- Related work, before edit: differences from closest systems were prose-only.
  After edit: added `Table~\\ref{tab:closest-abstractions}` comparing work families by intent root, protected-decision object, atomic lifecycle, four-plane no-promotion, and adapter lowering.

## Verification

Compiled from `docs/autopaper` with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex
```

Then checked the log for undefined citations, undefined references, and overfull boxes. No matching warnings remained after narrowing the related-work matrix.

## Remaining Concerns

- The writing now defends the novelty more cleanly, but the E3 strongest-composite-baseline experiment and workload characterization still need to be implemented before claiming full novelty evidence.
- The closest-abstraction matrix is a useful guide, but citation-specific claims should be audited again in the later citation/consistency rounds.
