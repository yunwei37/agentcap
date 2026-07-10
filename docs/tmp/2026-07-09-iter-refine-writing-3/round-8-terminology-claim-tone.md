Date: 2026-07-09

Round: 8 -- terminology and claim tone

What was checked

- Invented or project-local terms that make the paper read like an internal progress report rather than a systems paper.
- Self-attacking or over-defensive wording around evaluation scope.
- English compound terms that were useful while drafting but should be clearer in the Chinese paper.

Findings

- The paper already defines the four authority-input classes as proof boundaries rather than component taxonomy: agent, instruction, tool, and runtime-observation/env.
- The main remaining issue was not the four-context model. It was evaluation wording such as "project-author adjudicated", "current corpus", "saved local workflow suite", "claim-facing counterexamples", and repeated "production ..." markers.
- Scope-bearing limitations should stay. The paper must keep saying that current results do not prove benchmark-scale utility, production ActPlane integration, or independent expert-oracle minimality.

Changes made

- Replaced "project-author adjudicated" with "author-adjudicated" and tied those labels explicitly to the lease-audit corpus.
- Replaced "current corpus" with "lease-audit corpus" or "该 corpus" where the corpus had just been named.
- Replaced "saved local workflow suite" with "本地 workflow suite 的保存 traces".
- Replaced "claim-facing counterexamples" with "支撑机制结论的 counterexamples".
- Rephrased "production ..." occurrences in Chinese prose as "生产级 ..." or removed "production" where the sentence only needed to say the row is not an ActPlane integration.
- Replaced "当前结果" with "这些结果" in the limitations/conclusion so the paper reads less like a status report.

Verification intent

- No quantitative values were changed.
- The edits preserve evidence boundaries: no new claim of benchmark-scale utility, production MCP/ActPlane integration, or independent expert minimality was introduced.
- Next checks: paper evidence-number audit, LaTeX compile, log grep, focused pytest, and git diff hygiene.

Remaining concerns

- The paper still intentionally keeps several scope boundaries: fresh online utility/recovery, independent field-owner adjudication, expert-oracle lease scoring, and production-grade prompt/MCP/ActPlane integration remain missing evidence for stronger claims.
- Later rounds should continue with paragraph flow and citation verification rather than changing experiment numbers.
