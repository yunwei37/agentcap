# Round 5: Reviewer Stress Test

Date: 2026-07-09

## Reject argument (149 words)

Core idea is IFC + capability-based security (50 years old). No engagement with Capsicum/HiStar/Flume lineage. Intent extraction hand-waved into TCB. LLM compiler untested under adversarial prompts. 38 boundary events too thin. Ablation circular. Policy language, not a system.

## Meta-assessment

Reject was **moderately easy** to construct — signals real vulnerabilities:
1. **Classical-security lineage gap** — genuine, needs a paragraph separating from Capsicum/HiStar/CHERI
2. **38-event evaluation** — genuinely thin, easiest attack
3. **Intent extraction hand-wave** — real engineering gap assumed solved

But reviewer **had to reach** on:
- "Ablation is circular" — slightly unfair, 94% is meaningful
- "Policy language, not a system" — architecture shows concrete components

## Assessment

For a workshop extended abstract, the framing is **good enough** if:
1. Discussion section addresses classical-security lineage explicitly
2. 38-event weakness acknowledged as preliminary
3. Intent extraction bounded as future work

The core idea (controlling which input influences which decision field) was recognized as "genuinely useful reframing."

## Remaining open items (not fixable by framing alone)

- Evidence scale: 38 boundary events needs 10-50x for full paper
- Live agent experiments needed for full paper
- Intent extraction mechanism needs real evaluation
