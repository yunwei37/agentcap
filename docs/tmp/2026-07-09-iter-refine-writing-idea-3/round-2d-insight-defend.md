# Round 2d - Insight and Novelty Defense

Date: 2026-07-10

## What Was Changed

Target files:

- `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`
- `/home/yunwei37/workspace/agentcap/docs/evaluation.md`
- `/home/yunwei37/workspace/agentcap/scripts/analyze_commit_object_minimality.py`
- `/home/yunwei37/workspace/agentcap/scripts/audit_paper_evidence_numbers.py`

Defense changes:

1. Scoped the minimality claim.
   - Before: the paper could be read as claiming a globally minimal authority-state commit object.
   - After: the paper says the minimality claim is only with respect to the tested owner-projection, lifecycle, and local-boundary removal families.

2. Added R270 commit-object removal matrix.
   - New script: `scripts/analyze_commit_object_minimality.py`.
   - Inputs: saved R239E3WEAKABL, R241E3TYPEDBASE, R225MULTIBOUNDARY, and R240ADAPTERPROOF summaries.
   - Output: `results/eval/R270COMMITMIN/`.
   - Result: 10/10 tested removals have same-event or local-boundary false-accept counterexamples; audit-id removal remains 1 explicit gap.
   - Scope: deterministic saved-summary analysis; no model/API call, trace replay, side-effect execution, clone, sync, or dataset download.

3. Added R271 paper evidence audit.
   - Output: `results/eval/R271PAPERAUDIT/`.
   - Result: 92/92 paper-facing evidence checks passed with 0 failures.

4. Revised system and ActPlane wording.
   - Abstract and contributions now say deterministic OS-monitor-style replay lowering, not kernel/ActPlane mediation.
   - E3 is framed as local adapter contract feasibility, not full production multi-boundary enforcement.

5. Revised related-work and conclusion tone.
   - The related-work table now uses "Default object does not expose" instead of a harsher missing-object framing.
   - Conclusion states that the paper does not invent capability, taint, lease, or monitor primitives; it defines the runtime linearization object for agent authority-changing decisions.

## Verification

Commands run:

```bash
python3 -m pytest tests/test_analyze_commit_object_minimality.py tests/test_audit_paper_evidence_numbers.py -q
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
python3 scripts/audit_paper_evidence_numbers.py --run-id R271PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R271PAPERAUDIT
```

Results:

- Pytest: 2 passed.
- LaTeX: compiled successfully; existing underfull/float warnings remain.
- Paper-number audit: 92/92 checks passed, 0 failures.

## Remaining Concerns

Independent/blinded field-owner adjudication is still required before the paper can make a strong workload-prevalence or expert-minimality claim. The current R270 result is scoped mechanism evidence over tested removals, not global minimality.
