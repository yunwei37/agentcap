# Round 11: Final Consistency Audit

Scope: `docs/autopaper/intentcap-paper-zh.tex`.

Checks:

- Grepped the Chinese paper for core result numbers, four-input terminology, E1-E4 labels, and `tau2/tau3` naming drift.
- Cross-checked E1 numbers against saved R202/R203E1U/R024 records in `docs/evaluation.md` and result artifacts.
- Cross-checked E4 numbers against:
  - `results/eval/R211ENVBACKEND/env_backend_summary.json`
  - `results/eval/R212ENVLLM/env_llm_backend_summary.json`
  - `results/eval/R216E1MATCH8/matched_online_summary.json`
- Rebuilt the Chinese paper with XeLaTeX.

Findings and fixes:

- The main paper used `tau2/tau3` in the abstract, intro result summary, and conclusion, while the methodology used `tau2-style artifacts` and the bibliography cites tau2-bench. Replaced those three paper-facing instances with `tau2-style` to avoid an undefined benchmark name.
- E1 numbers are consistent: 3,746 protected events with 0 dangerous accepts, 3,813/3,813 benign reference actions, and 2,554/2,556 applicable tool-oracle tasks.
- E4 numbers are consistent: R211 executes 4 authorized IntentCap effects, blocks 6 violations, and executes 0 unsafe effects; object-only executes 8 effects including 4 unsafe effects. R212 has 8 model calls including 4 unsafe calls; IntentCap executes only the 4 authorized calls and blocks all 4 unsafe calls, while object-only executes 7 calls including 3 unsafe effects.
- Limitations remain consistent: the paper claims instrumented protected-decision safety and local pre-side-effect feasibility, not full end-to-end utility, approval-burden reduction, independent expert replication, or production ActPlane integration.

Verification:

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- No undefined citations/references or overfull boxes were reported in the final grep check.
