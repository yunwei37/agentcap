# Round 9 - Language Flow and Polish

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

What was checked:

- Topic position and stress position.
- Old-to-new information flow.
- Paragraph transitions and claim-first ordering.
- Register consistency, especially whether evaluation prose reads like a paper or an internal run ledger.
- Common pitfalls from `iter-refine-writing/references/common-pitfalls.md`, with numbers treated as read-only.

Reviewer findings:

- Must-fix: E3 proof-completeness and system-surface paragraphs were still too ledger-like because they foregrounded run IDs and artifact layers before the claim.
- Must-fix: the current-evidence recovery diagnostic table cell packed too many shard-level details into a main table cell.
- Must-fix: the E2 workflow residual paragraph combined baseline role, values, novelty boundary, and scope in one paragraph.
- Must-fix: E3 boundary result paragraphs were organized by rows/probes rather than by boundary claims.
- Must-fix: the formal owner-class paragraph defined all four context classes in one overloaded sentence.
- Should-fix: abstract, intro insight paragraph, contribution bridge, problem characterization, four-class explanation, equivalence boundary, implementation opening, recovery diagnostic, limitations, and conclusion needed better flow and less self-attacking scope language.
- Consider: remove a run-in bold pseudo-heading from the pre-effect commit quote block and reduce repeated caveat placement.

What changed:

- Abstract now adds a claim-first evaluation bridge before the three result sentences.
- Introduction insight paragraph now explains the four context classes as separate proof questions rather than four note-like sentences.
- Contribution bridge now uses separate sentences for C1, C2, and C3.
- Problem characterization now leads with the design-support observation; provenance/no-sync details remain in evaluation/evidence text.
- The four-context explanation now separates why env is needed from why env cannot be merged into tool or instruction.
- Formal owner-class definition now introduces `agent`, `inst`, `tool`, and `env` as proof owners across separate paragraphs.
- Equivalence boundary now separates required interface objects, audit id role, and typed-provenance convergence.
- Implementation opening now describes block points and modules in claim-driven language instead of project-path language.
- E2 workflow residual paragraph is split into claim, evidence, and scope.
- E3 prompt/delegation, MCP broker, integrated workflow, paired data/control, env-lowering, bubblewrap, proof-completeness, and aggregate paragraphs now start with the boundary claim before the numbers.
- Current evidence recovery cell is compressed; detailed recovery/compiler shard numbers were moved into the recovery diagnostic prose.
- Limitations are grouped into data/labeling, deployment, and utility/recovery boundaries.
- Conclusion is split into a system-object sentence and an evidence/takeaway sentence.
- The quote-block pseudo-heading was rewritten as an ordinary sentence.

Remaining concerns:

- The paper remains long and table-heavy; Round 10 should focus on citation/annotation correctness rather than new prose changes.
- Some compact English labels remain in tables for space.
- This round did not add new experiments or change quantitative claims.
