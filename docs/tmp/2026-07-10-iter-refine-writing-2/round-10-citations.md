# Round 10 - Citation Gate

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

What was checked:

- `.bib` annotation completeness for `VERIFIED`, `REAL`, `PDF`, `ABSTRACT`, and `USED_FOR`.
- Missing or suspicious annotation markers: `REAL: unverified`, `unverified`, `TODO`, `FIXME`, and `MISSING`.
- Undefined citation keys in the paper.
- Unused bibliography entries.
- LaTeX compilation after Round 9 prose changes.

Commands:

```bash
python3 - <<'PY'
from pathlib import Path
import re
tex=Path('docs/autopaper/intentcap-paper-zh.tex').read_text()
bib=Path('docs/autopaper/intentcap-paper-zh.bib').read_text()
cites=[]
for m in re.finditer(r'\\cite\{([^}]+)\}', tex):
    cites += [x.strip() for x in m.group(1).split(',')]
bibkeys=re.findall(r'^@\w+\s*\{([^,]+),', bib, re.M)
print('cite_occurrences', len(cites))
print('unique_cites', len(set(cites)))
print('bib_entries', len(bibkeys))
print('undefined_cites', sorted(set(cites)-set(bibkeys)))
print('unused_bib_entries', sorted(set(bibkeys)-set(cites)))
PY

rg -n 'REAL: unverified|unverified|TODO|FIXME|MISSING' \
  docs/autopaper/intentcap-paper-zh.bib \
  docs/autopaper/intentcap-paper-zh.tex

latexmk -g -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Results:

- `cite_occurrences`: 48.
- `unique_cites`: 22.
- `bib_entries`: 22.
- `undefined_cites`: none.
- `unused_bib_entries`: none.
- `.bib` annotation fields are present for 22/22 entries.
- No `REAL: unverified`, `unverified`, `TODO`, `FIXME`, or `MISSING` tokens were found in the paper or `.bib`.
- LaTeX compiled successfully after Round 9, producing 54 pages. The remaining output consists of existing font/underfull/overfull/float warnings, not compilation errors.

Changes made:

- No citation or bibliography source changes were required.
- No quantitative claims were changed.

Remaining concerns:

- Citation verification relies on the existing annotated `.bib` and downloaded reference corpus. A later full related-work refresh should be driven by a new literature/novelty pass, not by this writing-round citation gate.
