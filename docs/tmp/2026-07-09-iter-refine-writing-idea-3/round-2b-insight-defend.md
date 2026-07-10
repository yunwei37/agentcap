# Round 2b - Insight and Novelty Defense

Date: 2026-07-10

## What Was Changed

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

The defense edits strengthen the paper's core novelty claim without changing evaluation numbers.

1. Intro insight paragraph:
   - Before: the paper described a generic pre-effect authorization record / commit object.
   - After: the paper defines an `authority-state commit object` containing issuer-owned field proofs, checker-owned active-lease version, same-transition consume/delegate mutation, and audit binding. It also states the concrete failure modes when a field is missing: class substitution, stale reuse, double consume, and over-delegation.

2. Design motivation before threat model:
   - Added `Pre-Design Characterization`.
   - It uses existing audited artifacts only: 8,696 events, 8,691 requiring multiple issuer classes, 198 requiring env/runtime proof, 3,593 denied events with class-substitution attempts, and 48 sampled protected-decision labels.
   - Purpose: make the insight evidence-driven before the design appears.

3. Formal model:
   - Strengthened the safe-merge criterion by naming owner-projection equivalence.
   - Added lifecycle-linearization equivalence: a split monitor must accept the same trace and produce the same final checker-owned lease state as atomic `check_and_consume`.
   - Explicitly names stale lease version, post-side-effect budget consume, missing parent/child comparison, and unbound audit ids as falsifiers.

4. ActPlane / OS positioning:
   - Intro and implementation now state that OS monitor / ActPlane-style backend receives only the env/local-effect projection: file/process/network/object predicates, holder, budget, and provenance/influence labels.
   - Agent-owned sink/approval proof, instruction endorsement, tool schema owner proof, lease minting, and delegation graph mutation remain checker responsibilities.

5. Safety properties:
   - Added concrete implementation-level falsifiers: missing adapter, wrong control provenance, stale lease version, wrong owner projection, and non-atomic parent/child lease comparison.

6. Related work:
   - Replaced the yes/no-style comparison table with a default runtime authorization object table.
   - Removed the duplicate runtime-object audit table.
   - The prose now says programmable policy systems can be equivalent if they expose the same authority-state commit record.

## Verification Plan

Run:

```bash
cd /home/yunwei37/workspace/agentcap/docs/autopaper
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Run paper-number audit:

```bash
python3 scripts/audit_paper_evidence_numbers.py --run-id TIDEA2BAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir /tmp/intentcap-idea2b-audit
```

## Remaining Concerns

Round 2c should re-attack whether:

1. The authority-state commit object still sounds like generic reference-monitor state.
2. The four classes are now justified as proof-boundary quotients rather than ABAC labels.
3. The pre-design characterization is enough evidence, given that it is derived from existing artifacts and author-adjudicated labels rather than independent blinded labels.
4. The ActPlane positioning is now clearly above/beside OS enforcement rather than a claim of production ActPlane integration.
