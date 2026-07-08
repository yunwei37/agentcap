# Round 10: Citation Gate

Scope:

- `docs/autopaper/intentcap-paper-zh.tex`
- `docs/autopaper/intentcap-paper-zh.bib`

Checks performed:

- Ran the citation verification script from `check-paper-citations` on the Chinese paper bibliography.
- Confirmed all 22 active `.bib` entries have complete annotation blocks (`VERIFIED`, `REAL`, `PDF`, `ABSTRACT`, `USED_FOR`).
- Confirmed all 22 bibliography entries are cited and every citation key in the paper resolves.
- Re-ran LaTeX after citation edits.

Fixes:

- Changed `tau2bench` title from a nested LaTeX math title to a machine-verifiable BibTeX title while preserving the paper identity.
- Changed `agentbound` URL from the arXiv page to the DOI URL so the checker verifies the published ACM metadata instead of comparing against the arXiv preprint year.
- Added existing citations to the introduction/background where the text first discusses Skills/MCP ecosystems, action-time guards, OS-level enforcement, and IFC/provenance/taint defenses.

Result:

- `verify_bib.py docs/autopaper/intentcap-paper-zh.bib` reports no VERIFIED-entry mismatches.
- Remaining warnings are API lookup limitations for non-arXiv/spec or venue pages (`mcp-spec`, `agentdojo`, `injecagent`, `mcptox`, `eim-bpftime`), not metadata mismatches.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` succeeds with no undefined citations/references and no overfull boxes.
