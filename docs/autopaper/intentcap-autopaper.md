# IntentCap 中文自动论文草稿

Last updated: 2026-07-03
Status: 自动研究中的中文长稿；不是冻结的英文两页 workshop abstract

## 题目
IntentCap: Intent-Carrying Capabilities for LLM Agent Extensions

## 摘要草稿
LLM agent 正在从固定工具调用器变成可扩展的执行环境。一个 agent 可以加载 Skills，连接 MCP servers，运行本地脚本，并把任务委托给 subagents。问题不只是这些扩展能否读文件、发请求或调用 API；更关键的是，扩展提供的文本会影响 agent 后续的带权限决策：选择哪个工具、把结果发到哪个 sink、请求多大范围的 approval、或者把哪些上下文和能力交给另一个组件。现有防御通常在“策略已经存在”之后约束操作，例如 tool-call guard、扩展 manifest、OS sandbox 或 eBPF/IFC 监控。它们很少直接表达：在当前用户意图下，哪一段 context 可以影响哪一类未来决策。

IntentCap 的核心观点是把用户意图作为权限根，把 context influence 当成最小权限 capability。系统首先生成结构化 intent certificate，记录当前目标、用户选择的对象、授权的 sink、约束、approval 和过期条件。每个 context cell 都带有 provenance label 和允许的 influence modes。一个 capability lease 只有在操作可由 intent certificate 推导，并且该操作的 control provenance 被允许影响对应 decision class 时才有效。LLM 可以辅助提出 plan、effect graph 和 candidate leases，但 deterministic checker 才能接受或拒绝 lease 与事件；checker 验证 provenance、flow、temporal order、budget 和 delegation 约束，并把允许的 lease 下发到 context constructor、tool gateway、MCP broker、本地执行 sandbox 和 delegation monitor。

本文的目标不是宣称“解决 prompt injection”，而是给出一个更精确的系统安全性质：在已建模的 decision classes 和已接入的 enforcement boundaries 内，accepted high-impact events 不能被未授权 context 作为 control dependency 影响。当前原型已经把这个思想落到多个 benchmark 的 replay 与本地执行路径上：AgentDojo、InjecAgent 和 MCPTox 用于 context-to-decision 攻击，tau2/tau3 用于 policy-following utility 与 authority minimization。后续数据集选择先做网络检索和官方 metadata 审核，不自动同步新测试集；R026 已把 28 个 web-only 候选整理成可复现排序，但它只是候选选择证据，不是 benchmark 执行结果。R027 把已有 authority-minimization 结果转成共同的 oracle-distance scoring；R028/R029 用本机 llama.cpp/Qwen 跑真实 LLM lease-compiler corpus，并在 R029 加入一轮 checker-feedback refinement；R030 进一步把本地 Qwen 接到 `LiveToolGateway` 做 action-level allow/block/recovery loop；R031 则把本地 Qwen 接进 tau2 mock-domain task environment，用 task text/tool schemas 生成 fresh actions，再由 exact task leases gate 和执行；R032 把同一 runner 推到 airline/retail/telecom 固定小子集，结果是 7/7 model calls 被 exact leases 阻断、0/7 tool-oracle pass；R033 又给这些 blocked calls 加一轮 structured feedback，但 5 个 feedback calls 仍全部 off-lease；R034 在同一小子集上加入 stepwise prompt，给模型 prior gateway decisions 和 executed tool-result previews，最终执行 1 个 exact leased call、阻断 19 个 off-lease calls，tool-oracle pass 提升到 1/7。R032/R033/R034 仍是跨域小规模 pilot，说明 stepwise context 有一点恢复信号，但还远没有达到 benchmark-scale utility/recovery。

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
- tau2 fresh local-model pilot：R031 在完整 tau2 mock domain 上运行本地 Qwen。模型只看到 task text 和 available tool schemas，不看到 `evaluation_criteria.actions`；runtime 用 exact reference-action leases 作为 oracle authorization profile，把 tool+args 完全匹配的 model calls 绑定到 lease 后通过 `LiveToolGateway` 执行。10 个 mock tasks 中 8 个有 assistant reference actions，2 个被记录为 no-reference unsupported；Qwen 产生 7 个 calls，其中 4 个 exact calls 执行并通过 tool oracle，3 个 off-lease calls 被阻断，0 tool errors，tool-oracle pass 为 4/8。R031 是 fresh local-model task-environment pilot，但仍不是跨域 tau2/tau3 user-simulator 或 denial-recovery 结果。
- tau2 cross-domain local-model pilot：R032 使用同一 runner 和同一 local Qwen/llama.cpp 模型，在 airline、retail、telecom 每域最多 3 个任务上运行，不 clone/sync/download 新数据集。7 个 evaluated tasks 有 assistant reference actions，2 个任务因 no assistant reference actions 被记录为 unsupported；共 28 个 reference actions。Qwen 产生 7 个 parse-successful calls，但全部与 exact reference-action leases 不匹配；gateway allow 0、block 7、execute 0、tool errors 0、tool-oracle pass 0/7，env-oracle pass 2/7。R032 支持“跨域 pilot 中 off-lease calls 在调用前被阻断”，同时明确暴露 one-shot prompting 的 utility 缺口。
- tau2 denial-feedback pilot：R033 在 R032 的同一 airline/retail/telecom 小子集上打开 `--feedback-rounds 1`。反馈 prompt 只告诉模型 blocked calls 和 gateway reasons，不暴露 `evaluation_criteria.actions`。7 个 evaluated tasks 全部触发 feedback；Qwen 产生 7 个 initial calls 和 5 个 feedback calls。12 个 calls 全部 off-lease，被 gateway 在调用前阻断；execute 0、tool errors 0、tool-oracle pass 0/7。R033 支持“简单 denied-call feedback 不足以恢复跨域 tau2 utility”，同时继续支持 gateway 对失败恢复尝试的阻断。
- tau2 stepwise local-model pilot：R034 在 R032/R033 的同一 airline/retail/telecom 小子集上打开 `--stepwise-max-steps 3`。每个 step 只要求至多一个 tool call，并把 prior gateway decisions 和 executed tool-result previews 放回 prompt，但仍不暴露 `evaluation_criteria.actions`。7 个 evaluated tasks 共尝试 21 个 steps，Qwen 产生 20 个 calls；其中 1 个 telecom `enable_roaming` call 与 exact lease 匹配并执行成功，19 个 off-lease calls 在调用前阻断；tool errors 0，tool-oracle pass 1/7。R034 是 weak positive stepwise utility pilot，不是跨域 recovery 成功。
- Oracle-distance scoring：R027 对 R019/R020/R022 的已保存 authority-minimization summaries 做统一评分，产生 18 条 baseline rows 和 3 条当前 oracle rows。三个 benchmark 上最接近 oracle 的非 oracle baseline 仍然有明显缺口：InjecAgent `task_tool_allowlist` 距离 1,350 并放行 1 个 unsafe event，MCPTox `authentic_server_allowlist` 距离 2,077,267 并放行 2,058 个 unsafe events，tau2 `task_reference_tools` 距离 1,141，主要缺 control/event-binding granularity。全部非 oracle baselines 合计会放行 13,851 个 unsafe events。R027 是 saved-result scoring，不是大规模独立人工 oracle 标注。
- Checker/LLM split：R025 把 local wrong-sink、AgentDojo R011、MCPTox R007、InjecAgent R010 和 tau2 R024 合成一个 saved-trace checker-ablation corpus。8,680 个 events 中，deterministic checker 允许 4,869 个、拒绝 3,811 个。Object-only policy 会 false-accept 全部 3,811 个被 checker 拒绝的事件；saved-lease-constraints/no-provenance policy 会 false-accept 3,810 个；full-event-args/no-provenance policy 也会 false-accept 全部 3,811 个。R028 进一步用本机 Qwen/llama.cpp 生成真实 candidate lease/deny JSON：7 个样本中 3/3 reference-allowed candidate leases 被 checker 接受，4 个 reference-denied 中 1 个被模型正确 deny，1 个 unsafe candidate lease 被 checker 拒绝，另有 1 个 schema-invalid response 和 1 个 parse failure，dangerous false accept 为 0。R029 把同一 runner 扩展到 28 个 existing-trace samples，并加入一轮 deterministic checker feedback：初始 22 个 candidate leases 中 10 个 unsafe proposals 被 checker 拒绝，另有 2 个 invalid decisions 和 2 个 parse failures；14 个需要 feedback 的样本在 refinement 后全部变成 correct deny。R030 从 lease candidate 前端推进到 action-level gateway loop：18 个 existing-trace samples 上，Qwen 初始提出 18 个 calls；`LiveToolGateway` 执行 8 个合法事件、阻断 10 个不安全 calls，这 10 个是 LLM-only runner 会直接执行的 unsafe initial calls；一轮反馈后 6 个恢复为 abort，4 个仍被 gateway 阻断，最终 0 dangerous execute。R031/R032/R033/R034 再推进到 task environment：R031 在 mock domain 执行 4 个 exact leased calls 并阻断 3 个 off-lease calls；R032 在 airline/retail/telecom 小子集阻断 7 个 off-lease calls；R033 对同一小子集加入一轮 blocked-call feedback，又阻断 5 个 feedback off-lease calls；R034 用 stepwise tool-result context 执行 1 个 exact leased call 并阻断 19 个 off-lease calls。该结果支持 C3 的真实 LLM 前端、checker feedback 和本地 action-level/task-environment enforcement 子结论，但不是 benchmark-scale online agent run。
- Web-only eval 选择：R026 根据官方网页、论文、data card 和 repo metadata 对 28 个候选数据集做 deterministic ranking，没有 clone、sync、download 或执行任何新数据集。四个 existing-local artifacts 是 AgentDojo、MCPTox、tau2/tau3-bench 和 InjecAgent；最高优先级 web-only 候选包括 Skill-Inject、MCPSecBench、MCP-Bench、ToolSandbox、HarmfulSkillBench、WorkBench、TheAgentCompany 和 SWE-bench。其中 HarmfulSkillBench、HarmActionsEval、AgentHarm 和 Agent-SafetyBench 被标记为 safety-protocol-required，不能在没有单独安全协议和范围确认前下载或运行。

## 当前可支持的说法
- IntentCap 可以在 toy trace、AgentDojo、MCPTox、InjecAgent 和 tau2/tau3 reference replay 中表达并执行 context-provenance-aware allow/deny。
- 对 MCPTox，context authority 不是“更小 tool set”的同义词：exact-tool ACL 与 IntentCap 暴露同样的 tool count，但缺少 provenance check 时会放行 poisoned-description-controlled calls。
- 对 tau2/tau3，exact event leases 比 domain/global static ACL 显著缩小 authority surface，并且可以下发到真实 toolkit callable 和官方 action/env evaluator reference replay。
- 对 oracle scoring，R027 支持一个 saved-result 说法：在当前三类 authority-minimization summaries 上，IntentCap oracle profiles 比最接近的静态/半静态 baseline 更接近 intent/provenance/event-binding 要求，并且非 oracle baseline 仍会放行大量 unsafe events。
- 对 checker/LLM split，R025 支持 deterministic provenance checking 能拒绝 object-only、saved-lease-constraints/no-provenance 或 full-event-args/no-provenance policy 会错误接受的候选授权；R028/R029 支持一个真实 local LLM 前端说法：Qwen 生成的 candidate leases 必须被 checker 验证，checker 可以接受有效候选、拒绝不安全候选，并用结构化 denial feedback 把部分无效/不安全候选修正为 deny；R030 支持一个更运行时的本地说法：当 Qwen 直接提出 action events 时，gateway 可以执行合法事件、阻断不安全事件，并通过反馈让部分不安全 calls 转成 safe abort；R031/R032/R033/R034 支持一个 task-environment pilot 说法：当 Qwen 从 tau2 task text 生成 tool calls 时，exact task leases 可以执行匹配调用并阻断 off-lease 参数或 hallucinated tools；R034 进一步说明 stepwise tool-result context 能恢复一个 exact call，但当前跨域 utility 仍然很弱。
- 对后续 workload 选择，R026 支持一个流程性说法：新数据集应该先经官方 metadata 排序和安全门槛分类，再请求明确下载/导入批准；当前不能把 R026 写成新的实验性能结果。

## 还不能支持的说法
- 不能说 IntentCap 已经完成 benchmark-scale fresh online model benchmark；R031 是 mock-domain local Qwen task-environment pilot，R032/R033/R034 是 airline/retail/telecom 固定小子集 pilots。
- 不能说 IntentCap 已经测量了 robust end-to-end task-level recovery 成功；R029 只测了 lease-candidate 层的一轮 checker-feedback refinement，R030 只测了 action-level local gateway feedback，R033 在 tau2 task loop 中加入简单 denied-call feedback 但没有恢复任何执行，R034 的 stepwise prompt 只恢复 1/7 个任务。
- 不能说 R024 是完整 tau2/tau3 simulator utility，因为 `COMMUNICATE` 和 `NL_ASSERTION` 没有评估。
- 不能说 R024 对 `banking_knowledge` 使用了完整 official retrieval environment constructor；当前是 no-retrieval fallback。
- 不能说 R027 是大规模独立人工 expert-oracle study；它是对 R019/R020/R022 已保存结果的 oracle-profile distance scoring。
- 不能说 R028/R029/R030/R031/R032/R033/R034 是完整 LLM lease compiler evaluation；R028/R029/R030 是 existing-trace samples 上的本地 Qwen/llama.cpp lease/action corpus，R031/R032/R033/R034 是 exact reference-action leases 下的 tau2 task pilots。
- 不能说 R026 产生了新的 benchmark utility/security 数字；它只是 web-only metadata ranking。
- 不能说 lease 是全局最小；当前是相对于 reference effects 或保存 traces 的 exact/event-scoped lease。
- 不能说 OS enforcement 不需要；IntentCap 决定 policy provenance，sandbox/OS monitor 仍是可选或必要后端。
- 不能在没有确认前自动同步新的 eval dataset；后续应先从官方网页、论文、data card、repo metadata 做候选筛选，再明确下载边界。

## 评估计划
- E1：AgentDojo influence-denial。比较 vanilla、static tool filter、Task Shield/CaMeL 可复现实验和 IntentCap，指标包括 attack success、wrong-sink rate、utility、false denial。
- E2：InjecAgent cached/fresh model replay。继续从 cached outputs 推进到 fresh inference，观察 blocked attacker decisions 与 benign setup utility。
- E3：MCPTox MCP poisoning。重点比较 exact-tool ACL、server allowlist 和 IntentCap provenance lease，证明 tool description 不能作为 authorize/tool-select/sink-select 的 control source。
- E4：tau2/tau3 utility。R031 已把 R024 reference replay 推进到 mock-domain fresh local-Qwen task-environment pilot；R032 已扩展到 airline/retail/telecom 固定小子集，但得到 0/7 tool-oracle pass 的负向结果；R033 加入一轮 denied-call feedback 仍然 0/7；R034 加入 stepwise tool-result context 后执行 1 个 exact leased call，tool-oracle pass 1/7。下一步要加入 user-simulator loop 或更强 stepwise planner，测量 task success、recovery、approval burden 和 latency。
- E5：expert-oracle lease scoring。R027 已完成 saved-result oracle-profile scoring；下一步要为 10-30 个跨 benchmark tasks 手写并独立 review expert leases，对比 IntentCap exact/task/domain/global policies 的 risk-weighted distance。
- E6：compiler/checker ablation。R025 已完成 saved-trace object-only/no-provenance ablation；R028 已完成小规模 real local Qwen candidate lease corpus；R029 已扩大到 28 个 existing-trace samples，并加入一轮 checker-feedback refinement；R030 已把 Qwen action proposals 接到 `LiveToolGateway` 做本地 allow/block/recovery loop；R031/R032/R033/R034 已把 Qwen proposals 接入 tau2 task environments。下一步需要独立标注更大 corpus，并把 loop 扩展到跨域 benchmark task environment 的 stronger recovery。
- E7：explicitly approved web-only candidate。优先候选来自 R026：Skill-Inject/MCPSecBench 用于 Skill/MCP security，MCP-Bench/ToolSandbox/WorkBench 用于 utility/recovery；harmful/safety 类数据必须先写 safety protocol。

## 下一步门槛
下一步最有价值的是五选一：第一，把 tau2 runner 改造成 fresh user-simulator utility run；第二，强化 R034 stepwise planner，让它利用 executed tool-result context 做多步任务恢复；第三，把 R027 扩展成 10-30 个跨 benchmark tasks 的独立 expert-oracle lease study；第四，把 R029/R030/R031/R032/R033/R034 扩展成有独立 validity labels 的更大 LLM-proposed lease/action corpus；第五，在明确批准后导入一个 R026 top candidate。选择新 workload 时以 R026 的候选排序为入口，优先看 Skill-Inject、MCPSecBench、MCP-Bench、ToolSandbox 和 WorkBench；HarmfulSkillBench/AgentHarm 类数据必须先写 safety protocol。不默认 clone/sync。没有其中至少一个结果前，中文论文不应把当前证据写成 end-to-end cross-domain online benchmark 或完整 compiler evaluation。
