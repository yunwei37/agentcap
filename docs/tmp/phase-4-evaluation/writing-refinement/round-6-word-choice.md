# Round 6: Word Choice

## Reviewer Focus

Replaced project-management phrasing with paper-native wording while preserving the conservative evidence boundaries.

## Fixes Applied

1. Replaced `gate`/`claim gates` with `判定标准` or phrasing that says claim strength is determined by the four experiments.
2. Replaced `open items` with `剩余评估要求`.
3. Replaced `Run IDs, pilot probes` with `具体运行编号、探索性 probes`.
4. Replaced `utility collapse` and `benign completion collapse` with `utility/benign completion 大幅下降`.
5. Replaced `agent replacement` with `完整端到端 agent 安全结果`.
6. Replaced `prototype gap` with `prototype limitation`.
7. Replaced `final claim strength` and `写作风险` with more paper-native Chinese phrasing: `最终主张强度` and `解释风险`.
8. Replaced `Full-paper claims` with `完整论文的主张`.
9. Replaced `open engineering gap` with `未解决的工程限制`.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The prose still mixes English technical terms with Chinese exposition. Round 7 should focus on terminology and claim tone: which English terms should remain as technical terms, and which should be localized or normalized.
