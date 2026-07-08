# Round 3: Contributions and Goals

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Idea-quality checklist Section 3: contribution statements, design goals, and goal/evaluation alignment after R220.

Findings from the reviewer:
- G4 overclaimed implemented coverage because instruction placement and delegation are trace-level while tool/live-callable and local-env boundaries are implemented.
- C2 packed API, implementation, trace-level coverage, and ActPlane-style lowering into one too-broad contribution.
- E3 still risked appearing taxonomy-driven unless R220's characterization role and limits were explained more explicitly.
- E2 title and wording overstated authority-reduction evidence for a 24-label author-adjudicated audit.
- Goal-to-evaluation mapping needed to move G1/G2/G4 toward the experiments that actually support them.

What changed:
- Abstract now states that the current prototype fully executes tool/live-callable and local-env boundaries, while instruction/delegation are trace-level validation.
- C2 now states one deliverable: a checker-centered transition API and prototype with implemented tool/local-env enforcement, trace-level instruction/delegation semantics, and ActPlane-style env lowering target.
- C3 now states the three primary demonstrated results and treats lease auditability as auxiliary evidence.
- G4 now says the transition API can express context placement, tool/MCP, local env, and delegation, but current enforcement evidence is tool/local-env and current instruction/delegation evidence is trace-level.
- Goal map now points G1 to E1/E3, G2 to R220+E3/E1, G3 to E3/E2, and G4 to E4/E3 with the correct boundary note.
- E2 title changed from `Lease Audit and Authority Reduction` to `Lease Auditability`.
- R220 text now defines `requires multiple issuer classes` as analyzer-derived required-field class sets from op/mode/decision/provenance labels, not independent human labels or proof of multiple physical APIs.
- System overview now separates adapter contract from current implementation status.

Remaining concerns:
- E2 still needs independent blinded expert replication before the paper can make a strong expert-oracle least-privilege claim.
- G4 would need live instruction-placement and delegation enforcement experiments before the system claim can become full multi-boundary enforcement.
- R220 remains derived annotation; the next stronger evidence is independent natural protected-decision labeling.
