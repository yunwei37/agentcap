# Round 9: Citation Gate

Scope:
- Target files:
  - `docs/autopaper/intentcap-paper-zh.tex`
  - `docs/autopaper/intentcap-paper-zh.bib`
- Focus: citation authenticity, citation-key integrity, claim/citation alignment, and missing benchmark citations.

Checks performed:
- Confirmed all citation keys in the paper resolve to bibliography entries.
- Confirmed every bibliography entry has the required annotation fields: `VERIFIED`, `REAL`, `PDF`, `ABSTRACT`, and `USED_FOR`.
- Confirmed no entry remains marked `REAL: unverified`.
- Rebuilt the paper with `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`.
- Checked the final LaTeX log for undefined citations or fatal errors.

Changes made:
- Replaced placeholder related-work metadata with verified BibTeX metadata for 18 existing entries.
- Added citation annotations directly in `docs/autopaper/intentcap-paper-zh.bib`, as required by the citation-checking workflow.
- Added benchmark citations for AgentDojo, InjecAgent, MCPTox, and tau2-bench.
- Added citations where the paper first describes Skills/MCP extension surfaces and benchmark-derived trace adapters.
- Replaced `tau2/tau3` wording with `tau2-bench-style` to avoid citing an unstable or uncited benchmark name.

Gate result:
- Verified bibliography entries: 22
- Hallucinated citations found: 0
- Inaccurate or unstable citation uses fixed: 1 (`tau2/tau3` -> `tau2-bench-style`)
- Missing citations added: 4 bibliography entries, plus corresponding in-text citations
- Entries without local PDF: 1 (`mcp-spec`, official web specification)

Remaining caveats:
- The bibliography uses `plain.bst`, which omits some URL/DOI fields from the rendered bibliography even though the fields remain in the `.bib` file.
- The LaTeX build still emits fontscript and underfull-box warnings; these are formatting warnings, not citation failures.
