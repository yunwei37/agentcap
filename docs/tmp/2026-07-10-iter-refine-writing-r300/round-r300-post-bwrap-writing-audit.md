# R300 Post-Bubblewrap Writing Audit

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex` passages touched by R298.
- `iter-refine-writing/references/common-pitfalls.md` patterns: overclaiming, self-attacking sentences, and design/implementation separation.

Findings:
- Must-fix: The newly added bwrap evidence needed to be visible in the abstract/contribution path, not only in the E3 detail table.
- Must-fix: R298 needed to be written as a system-boundary probe, not as a production OS monitor claim.
- Should-fix: The E3 prose needed to distinguish three layers: checker semantic authority, deterministic env-policy lowering, and actual namespace sandbox containment.

What was changed:
- Added "local bubblewrap namespace sandbox" to the abstract and contribution prose.
- Kept "not production ActPlane/eBPF" boundary in abstract, implementation, E3, and limitations.
- Clarified that bwrap contains OS-visible path/resource violations but leaves non-OS semantic authority violations to the IntentCap checker.

Remaining concerns:
- The paper still has long English-heavy technical compounds inside Chinese prose. A future full writing cycle should reduce term repetition and shorten table-heavy paragraphs.
- Current LaTeX compile succeeds, but overfull/underfull table warnings remain and should be handled in a formatting pass.
