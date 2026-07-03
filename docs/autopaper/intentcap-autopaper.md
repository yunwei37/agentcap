# IntentCap 中文自动论文草稿

Last updated: 2026-07-03
Status: 自动研究中的中文长稿；不是冻结的英文两页 workshop abstract

## 题目
IntentCap: Intent-Carrying Capabilities for LLM Agent Extensions

## 摘要草稿
LLM agent 正在从固定工具调用器变成可扩展的执行环境。一个 agent 可以加载 Skills，连接 MCP servers，运行本地脚本，并把任务委托给 subagents。问题不只是这些扩展能否读文件、发请求或调用 API；更关键的是，扩展提供的文本会影响 agent 后续的带权限决策：选择哪个工具、把结果发到哪个 sink、请求多大范围的 approval、或者把哪些上下文和能力交给另一个组件。现有防御通常在“策略已经存在”之后约束操作，例如 tool-call guard、扩展 manifest、OS sandbox 或 eBPF/IFC 监控。它们很少直接表达：在当前用户意图下，哪一段 context 可以影响哪一类未来决策。

IntentCap 的核心观点是把用户意图作为权限根，把 context influence 当成最小权限 capability。系统首先生成结构化 intent certificate，记录当前目标、用户选择的对象、授权的 sink、约束、approval 和过期条件。每个 context cell 都带有 provenance label 和允许的 influence modes。一个 capability lease 只有在操作可由 intent certificate 推导，并且该操作的 control provenance 被允许影响对应 decision class 时才有效。LLM 可以辅助提出 plan、effect graph 和 candidate leases，但 deterministic checker 才能接受或拒绝 lease 与事件；checker 验证 provenance、flow、temporal order、budget 和 delegation 约束，并把允许的 lease 下发到 context constructor、tool gateway、MCP broker、本地执行 sandbox 和 delegation monitor。

本文的目标不是宣称“解决 prompt injection”，而是给出一个更精确的系统安全性质：在已建模的 decision classes 和已接入的 enforcement boundaries 内，accepted high-impact events 不能被未授权 context 作为 control dependency 影响。当前原型已经把这个思想落到多个 benchmark 的 replay 与本地执行路径上：AgentDojo、InjecAgent 和 MCPTox 用于 context-to-decision 攻击，tau2/tau3 用于 policy-following utility 与 authority minimization。下一步需要把 reference replay 推进到 fresh model/user-simulator 运行，并补 expert-oracle lease scoring。

## 论文主线
1. Agent 安全的对象不是只有工具操作，还有“谁能影响未来决策”。
2. 同一段 context 可以被允许作为数据使用，但不应自动拥有控制 authority。
3. 用户当前意图应当是 run-time authority 的根，而不是 Skill package、MCP server 或工具 catalog 的静态身份。
4. IntentCap 用 intent certificate、context authority label、effect IR 和 proof-carrying capability lease，把这件事变成可检查的 authorization 问题。
5. LLM-assisted compiler 只负责提议；deterministic checker 和 runtime adapters 才在 TCB 内。

## 设计要点
- Intent certificate：结构化表示用户目标、选择的对象、允许的 sink、禁止的 sink、fresh approval 和过期条件。
- Context authority：把 `observe`、`quote`、`summarize`、`parameterize`、`plan`、`instruct`、`delegate`、`authorize` 等 influence modes 与 decision classes 绑定。
- Effect IR：把 agent plan 或 benchmark trajectory 转成 `ctx.use`、`tool.call`、`mcp.call`、`fs.read`、`fs.write`、`exec.run`、`net.connect`、`subagent.spawn` 等安全相关事件。
- Capability lease：短期、可衰减的授权对象，约束 operation、object、arguments、intent derivation、control/data provenance、flow、temporal guard、budget 和 delegation。
- Deterministic checker：检查 event 是否匹配 active lease，且 control provenance 是否有权影响当前 decision class。
- Runtime adapters：在 context construction、tool/MCP invocation、本地执行和 subagent delegation 处执行 allow/deny，并保留 audit log。

## 当前证据链
- Local motivating trace：checker 允许用户选择的 PDF-to-spreadsheet 和用户选择 repo 的 GitHub issue，拒绝 PDF hidden text 控制的 wrong-repo issue。
- AgentDojo：R004 从 workspace injection tasks 中导出 10 个 benchmark-provided protected-decision events，全部因 untrusted injection-goal control 被拒绝。R011/R014 进一步把 54 个 adapter-only goal-inferred events 与 10 个 official ground-truth events 分开，避免把推断事件过报成 benchmark trajectory。
- MCPTox：R007/R015 从 1,834 个 `Success` labeled model responses 中导出 2,148 个 protected events，并把 benchmark cases、authentic tools、poisoned-tool records 和 replay events 分清楚。IntentCap 拒绝全部 2,148 个 poisoned-description-controlled events。R020 显示 exact-tool ACL 虽然也只暴露 1.0 tool/event，却会放行全部 2,148 个事件，因为它没有 provenance check。
- InjecAgent：R010 mixed replay 在 1,054 个 base cases 中允许 1,054 个 trusted user-tool events，拒绝 1,598 个 injected attacker-tool events。R016 把同一 trace 接到 `LiveToolGateway`，执行全部 benign callables，并在调用前压制全部 attacker callables。R017/R018 对官方 released cached model outputs 做 replay，覆盖 122 个 result sets、128,044 个 cached cases，执行 trusted setup calls，并阻断 37,991 个 cached attacker decisions；但这不是 fresh inference。
- Authority minimization：R019 显示 IntentCap one-shot lease 暴露 1.0 tool/case 并拒绝 1,598/1,598 injected events；toolkit/server policy 平均暴露 9.59 tools/case 并会放行 77 个 injected events；catalog-wide policy 暴露 330 tools/case 并放行全部 injected events。
- tau2/tau3 substrate：R021 解析当前 artifact，得到 5 个 domains、2,556 个 tasks、14,842 个 reference actions、67 个 ordinary assistant tools、48 个 discoverable assistant tools 和 32 个 user tools。
- tau2/tau3 minimization：R022 覆盖全部 3,813 个 assistant reference actions。Exact event leases 用 3,813 个 event slots；domain regular assistant ACL 暴露 34,209 个 tool slots，global all-tool ACL 暴露 388,512 个 tool slots。
- tau2/tau3 live toolkit execution：R023 把 3,813 个 assistant reference actions 接到真实 tau2 domain toolkit callables；3,813 个事件全部 checker-approved 并调用注册 callable，3,795 个成功，18 个 direct-replay `ValueError`，0 个 checker block，0 个 unsupported tools。
- tau2/tau3 evaluator-backed replay：R024 构造 tau2 message trajectories，assistant actions 通过 exact IntentCap event leases 和 `LiveToolGateway`，user reference actions 作为 simulator-side actions 不计入 assistant authority，并把 per-task leases/provenance labels 写入 `intentcap_traces.json`。R024 使用官方 `ACTION`、`DB`、`ENV_ASSERTION` evaluator classes，结果为 2,554/2,556 tool-oracle pass tasks、43/43 action-basis pass tasks、2,545/2,547 env-oracle pass tasks，0 checker blocks，0 unsupported tasks。两个失败是 `mock` 环境断言 mismatch，不是 checker deny。168 个带 `COMMUNICATE` 或 `NL_ASSERTION` basis 的任务仍未评估，因为没有运行 fresh model/user-simulator 对话。`banking_knowledge` 因本地缺少 retrieval 依赖使用 no-retrieval fallback environment，所以 R024 不能被写成该 domain 的完整 official environment-constructor run。

## 当前可支持的说法
- IntentCap 可以在 toy trace、AgentDojo、MCPTox、InjecAgent 和 tau2/tau3 reference replay 中表达并执行 context-provenance-aware allow/deny。
- 对 MCPTox，context authority 不是“更小 tool set”的同义词：exact-tool ACL 与 IntentCap 暴露同样的 tool count，但缺少 provenance check 时会放行 poisoned-description-controlled calls。
- 对 tau2/tau3，exact event leases 比 domain/global static ACL 显著缩小 authority surface，并且可以下发到真实 toolkit callable 和官方 action/env evaluator reference replay。

## 还不能支持的说法
- 不能说 IntentCap 已经完成 fresh online model benchmark。
- 不能说 IntentCap 已经测量了 denial recovery 或 model 看到拒绝后的重规划能力。
- 不能说 R024 是完整 tau2/tau3 simulator utility，因为 `COMMUNICATE` 和 `NL_ASSERTION` 没有评估。
- 不能说 R024 对 `banking_knowledge` 使用了完整 official retrieval environment constructor；当前是 no-retrieval fallback。
- 不能说 lease 是全局最小；当前是相对于 reference effects 或保存 traces 的 exact/event-scoped lease。
- 不能说 OS enforcement 不需要；IntentCap 决定 policy provenance，sandbox/OS monitor 仍是可选或必要后端。

## 评估计划
- E1：AgentDojo influence-denial。比较 vanilla、static tool filter、Task Shield/CaMeL 可复现实验和 IntentCap，指标包括 attack success、wrong-sink rate、utility、false denial。
- E2：InjecAgent cached/fresh model replay。继续从 cached outputs 推进到 fresh inference，观察 blocked attacker decisions 与 benign setup utility。
- E3：MCPTox MCP poisoning。重点比较 exact-tool ACL、server allowlist 和 IntentCap provenance lease，证明 tool description 不能作为 authorize/tool-select/sink-select 的 control source。
- E4：tau2/tau3 utility。把 R024 reference replay 推进到小规模 fresh model/user-simulator run，测量 task success、denial recovery、approval burden 和 latency。
- E5：expert-oracle lease scoring。为 10-30 个跨 benchmark tasks 手写 expert leases，对比 IntentCap exact/task/domain/global policies 的 risk-weighted distance。
- E6：compiler/checker ablation。构造 LLM-proposed candidate leases，比较 LLM-only acceptance 与 deterministic checker rejection。

## 下一步门槛
下一步最有价值的是三选一：第一，接一个 fresh online model/API benchmark subset，让 `LiveToolGateway` 真正在模型循环中阻断并观察恢复；第二，把 R024 改造成 tau2/tau3 fresh user-simulator utility run；第三，为 R019/R020/R022/R024 加 expert-oracle lease scoring。没有其中至少一个结果前，中文论文不应把当前证据写成 end-to-end online benchmark。
