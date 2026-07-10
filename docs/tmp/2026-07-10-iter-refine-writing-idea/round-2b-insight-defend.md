# Round 2b: Insight Defense

Date: 2026-07-10

What was changed:
- `docs/autopaper/intentcap-paper-zh.tex`
- `docs/tmp/2026-07-10-iter-refine-writing-idea/round-2a-insight-attack.md`

Defense applied:
1. Strengthened the core insight in the introduction.
   - Before: the paper said the main difference was a runtime-visible pre-effect authorization record, but it could still read as a renamed policy predicate.
   - After: the paper states why agent runtimes are special: proof issuer, observation issuer, and lifecycle owner are split across prompt construction, tool registry, runtime observer, approval UI, and delegation adapter. The contribution is the state placement and linearization interface.

2. Added a formal merge-unsoundness proposition.
   - Before: safe merge was expressed as an implication \(Accept_h \Rightarrow Accept\), but not as a named result.
   - After: Proposition 1 states that if a collapsed owner class lets a non-owner issuer supply a required field, there exists a same-action event accepted by the collapsed checker and rejected by the full checker.

3. Added a formal split-lifecycle proposition.
   - Before: lifecycle linearization was described by equivalence conditions and examples.
   - After: Proposition 2 states that splitting allow predicates, budget consumption, expiry progress, or parent-child attenuation without an equivalent final checker state admits stale reuse, double consume, or over-delegation traces.

4. Reframed the strongest baseline.
   - Before: the typed-provenance state guard row might look like another weak ablation.
   - After: the paper calls it the strongest prior-derived policy-style baseline: it already has owner fields, approval, holder, temporal, and budget predicates. Its remaining miss is the parent-child lease-set commit, so repairing it converges to the IntentCap interface.

5. Repositioned ActPlane-style enforcement.
   - Before: the text could read as saying OS-level enforcement cannot help.
   - After: the paper says an OS/local backend that receives only OS events lacks upstream projections, but if upstream supplies issuer proofs and shared checker state, it implements the IntentCap env/local lowering contract.

Remaining concerns:
- Round 2c should re-attack whether the propositions and typed-baseline convergence are enough to avoid the “just ABAC/IFC/reference monitor” rejection.
- Production-scale kernel/ActPlane integration remains future evidence, not a current claim.
