Date: 2026-07-09

Round: 9 -- language flow and polish

What was checked

- Whether the evaluation reads as a claim-driven argument rather than an experiment diary.
- Topic position and paragraph transitions in the evaluation opening, E1, and limitations.
- Remaining prose that sounded like status tracking rather than paper evidence.

Findings

- The evaluation already has the right three-experiment structure, but the opening mixed claim ordering, replay setup, baseline definitions, metrics, and scope in two long paragraphs.
- The flow improved by putting the claim dependency first, then moving experimental controls and baseline definitions under "评估方法".
- Several sentences used note-like "claim: evidence" structure. They were rewritten into ordinary prose without changing evidence values.

Changes made

- Rewrote the evaluation opening to state the dependency chain: E1 checks expressiveness, E2 tests issuer/lifecycle necessity, E3 tests the multi-boundary transition contract, and the supporting audit checks lease auditability.
- Moved model/replay controls and metric definitions into the "评估方法" subsection.
- Simplified the E1 opening so it first states the failure mode that E1 excludes.
- Rephrased the limitations lead from a status-report sentence into a scoped claim boundary.
- Standardized remaining production-scope wording in limitations.

Verification intent

- No experiment numbers, labels, citations, or evidence claims were changed.
- The edit should make the evaluation read as three claim-facing experiments plus one supporting audit, not a sequence of run records.
- Next checks: paper evidence-number audit, LaTeX compile, log grep, focused pytest, and git diff hygiene.

Remaining concerns

- Round 10 should verify citation annotations and missing-citation risks.
- The evidence boundary still correctly says that fresh online utility/recovery, independent expert replication, and production-grade integration remain future evidence for stronger claims.
