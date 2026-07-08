# Round 12: Final Verification

Scope: repository-level verification after the Chinese paper refinement and citation/consistency passes.

Commands:

- `pytest -q`
  - Result: collection failed because the package is not installed and the default environment does not put `src` or the repository root on `PYTHONPATH`.
  - Failure mode: `ModuleNotFoundError: No module named 'intentcap'` and `No module named 'scripts'`.
- `PYTHONPATH=.:src pytest -q`
  - Result: `235 passed in 2.95s`.

Paper build status:

- The final paper build from round 11 used:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- The final grep check found no undefined citations/references and no overfull boxes.

Interpretation:

- The repository tests pass under the same import setup used by the evaluation scripts (`PYTHONPATH=.:src`).
- The unqualified `pytest` command is not the right invocation for this repository unless packaging or `pythonpath` configuration is added later.
