# Round 9: Language, Flow, and Terminology Pass

Scope: `docs/autopaper/intentcap-paper-zh.tex`.

Reviewer focus:

- The abstract and intro had dense lease terminology that read like notes rather than a paper claim.
- The four authority inputs used mixed names (`authority-input class`, `plane`, `context source`, `input surface`), making the "four, not three" argument harder to follow.
- Runtime lowering was written as run-in adapter bullets instead of a claim-led mechanism boundary.
- The evaluation opening was artifact-first; it needed to state the four claim questions before listing workloads and metrics.

Changes made:

- Rewrote the abstract lease sentence to state that a lease binds current user intent, structured proof from agent/instruction/tool/env inputs, provenance, budget, expiry, and delegation constraints.
- Standardized the main term to four authorization input classes: agent, instruction, tool, and env. Removed stale `plane` phrasing except inside names such as ActPlane.
- Added clearer formal structure around `Solve_Gamma(C_agent, C_inst, C_tool, C_env)`, `Req(d)=<A_d,I_d,T_d,E_d>`, issuer-owned fields, and the no-substitution/no-promotion rules.
- Replaced the runtime lowering bullet list with a table mapping each adapter to submitted fields and checker boundary.
- Reframed E1-E4 as claim-facing experiments: protected-decision safety, lease auditability, mechanism necessity, and pre-side-effect enforcement.
- Removed note-like Chinese semicolons in the touched sections and split several long paragraphs into shorter paper-style sentences.

Verification:

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- `git diff --check`
- The LaTeX build reports no undefined citations/references and no overfull boxes after this pass.
