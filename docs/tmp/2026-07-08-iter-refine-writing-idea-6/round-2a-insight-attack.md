# Round 2a - Insight Attack

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Focus: whether the paper's novelty can be attacked as stateful ABAC, policy DSL predicates, provenance namespaces, stateful capabilities, or a reference monitor.

Findings:
- Must-fix: The strongest attack is that \sys is only stateful ABAC with owner namespaces and transactional checking. The paper already concedes that a policy DSL implementing the same transition is equivalent, but it did not state the positive contribution clearly enough.
- Must-fix: Four context classes can still read like attribute namespaces. The paper should frame them as four non-substitutable proof questions, not an ontology.
- Must-fix: `check_and_consume` read like a checker function signature. It needs to be described as a runtime commit-record interface whose accept result atomically updates checker state.
- Must-fix: The related-work table should compare default authorization object / commit unit rather than capability coverage.
- Should-fix: The running example should make clear why ordinary provenance can still look clean: PDF text influences delegation handoff, while final repo/body/tool provenance remains apparently valid.
- Should-fix: E3 should explicitly bind counterexamples to artifact families and state that only issuer/lifecycle changes vary.
- Should-fix: Evaluation overview should connect E1/E3/E4 to non-obvious insight.
- Should-fix: ActPlane positioning should say that backend receives certified env lease contracts and cannot produce field proofs.

Remaining concerns:
- Top-conference evidence still needs stronger closed-loop utility/recovery and independent labels.
- Abstract density remains a writing concern for a later prose pass.
