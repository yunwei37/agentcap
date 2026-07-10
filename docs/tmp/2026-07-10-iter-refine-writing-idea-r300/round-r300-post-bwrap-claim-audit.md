# R300 Post-Bubblewrap Claim Audit

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex` abstract, contribution list, implementation overview, E3 setup, E3 discussion, and limitations.
- `iter-refine-writing-idea/references/idea-quality-checklist.md`, especially the tests for problem/insight/evaluation alignment.
- `iter-refine-writing/references/common-pitfalls.md`, especially overclaiming, tool-vs-insight framing, and defensive scope wording.

Findings:
- Must-fix: R298 added a real local bubblewrap namespace sandbox probe, but the abstract and contribution list still described the env backend only as deterministic replay lowering. This made the top-level system evidence lag behind the implementation and E3 table.
- Must-fix: E3 described four primary system properties even though R298 adds a fifth property: local OS-substrate containment boundary plus the semantic gap where OS sandboxing cannot decide holder/provenance/prompt authority.
- Should-fix: The system-surface ledger paragraph could be misread as including R298 in the 8-row / 58-attempt R294 aggregate. R298 is separate local sandbox-substrate evidence and should be named separately.
- Consider: Keep the limitation wording neutral. It should say R298 is not production ActPlane/eBPF and not production MCP/prompt/subagent runtime, but should not sound like an apology or self-attack.

What was changed:
- Abstract: changed env/local-effect projection from only a deterministic replay target to deterministic replay target plus local bubblewrap namespace sandbox, while explicitly excluding production ActPlane/eBPF monitor.
- Contribution C2: added local bubblewrap namespace sandbox to the surfaces implementing the same pre-effect contract.
- Implementation summary: changed "production sandbox" missing evidence to "production ActPlane/eBPF integration" so the text no longer contradicts the local bwrap probe.
- E3 setup: changed the primary system properties from four to five, adding local OS-substrate containment boundary.
- E3 aggregate paragraph: clarified that R298 is outside the R294 8-row ledger and supplies separate OS-substrate execution evidence.

Remaining concerns:
- This was a targeted post-R298 alignment pass, not the full five-round `iter-refine-writing-idea` cycle.
- The next full idea refinement should stress-test whether "authority-state commit object" is still the cleanest name and whether the four proof-owner classes are framed as an implementation instantiation rather than a global taxonomy.
