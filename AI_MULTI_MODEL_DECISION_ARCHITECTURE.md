# AI多模型协同与自主决策架构

日期：2026-11-16；设计稿，未实施。绝对项目根为 `D:/广西人工智能大赛`。本设计复用已验收模型及验证规则，为新在线数据和新决策另设合同，不修改P0/S1.1/S2冻结实现。

## 1. 从同一观测前缀组织协作

拟引入 `episode_id → observation_prefix_id → event_id → context_id → plan_id → validation_id → action_id → feedback_id`。每个阶段保存父标识、输入摘要、算法/提示词版本和事件时间；不能只用页面当前run变量串接结果。

运行类型独立：D3/D511历史身份沿用P0-01，LIVE_TEP独立注册，SIM_TWIN分支引用生产前缀但有不同branch_id，EVALUATION_TRUTH仅评估器可见。新的实时运行不得伪装为原D3文件或随意添加进原 `model_registry.json`。新增注册覆盖层引用旧参数哈希，并注明适用性尚待验证。

|对象|关键字段与约束|
|---|---|
|ObservationEnvelope|episode/engine_commit/backend、seq、measurement_time、state_time、wallclock、41列测量、12列命令、单位/顺序/质量、schema_hash、payload_hash；只允许已提交前缀|
|DiagnosticContext|event来源、as_of、真实可见窗口、模型哈希、证据/事实目录、状态；同一context不能被新观测原地更新|
|PlanProposal|proposal_version、context/hash、目标模板ID、候选动作模板ID、evidence_refs、assumptions、rejection_reasons；属于提议，不是事实或执行授权|
|PredictionEvidence|predictor/route版本、输入前缀、动作语义、预测时域、均值/区间、支持和失配、来源类型；预测不能被当观测|
|ExecutionCertificate|plan/hash、validation/hash、episode、执行器、起止/有效期、允许动作、策略/安全规范哈希、一次性nonce；仅后端生成|
|FeedbackRecord|action回执、评价区间、观测事实ID、目标误差、约束、恢复持续时间、下一状态；尚未到时的效果WAITING|

数值事实均由后端生成。方案中的未来动作数值也由后端从已批准动作目录或优化器结果实例化；LLM仅引用方案/模板ID，不能输出控制百分比、PI增益、阈值或任意脚本。

## 2. 模型调度与可复用范围

**感知**：优先在原180秒检测网格、原41列和warmup规则下建立流式重放一致性。新LIVE适配器调用原Standardizer.transform、PCADetector.scores及Threshold.score，恢复冻结参数；P0-02的外层 `DetectionRuntime.detect` 只接受原白名单文件，不能直接对实时数组调用。应新增输入适配与准入层，而不是修改原reader。每秒评分可作为新影子研究，不能直接继承180秒控制限的在线误报保证。

**诊断**：事件自动触发“收集窗口/申请诊断”，不意味着立刻有可信分类。旧模型只在固定3600及三个半开窗口完成后有效；保留7列转4列的 `values[:, [0,1,2,5]].copy()` 顺序。新事件起点诊断先做影子实验，必要时新训练和独立校准，不移动旧模型的时间标签冒充已验证。三方法分歧、多候选和空候选原样保留；不按Top1选择预测器。

**因果**：从 `artifacts/d4/process_graph.json` 逐边挂接原方程、候选Granger、对齐配对总效应和局限。仅有限U10到C21/T9/P7约化总路径有配对证据，不能把整张图都标VERIFIED。候选类包含IDV名称是机制假设目录，不是当前真实故障标签。

**预测**：冻结Action/Delta只承担原协议对照；新LIVE预测器接口单独返回 `UNQUALIFIED/SHADOW/QUALIFIED_SIM_SCOPE`，资格绑定场景与时钟。任何资格缺失、未来输入、成员缺失、域外和过宽均拒绝当前方案。新模型必须保留原失败对照，不能改旧q/width门槛获得通过。

## 3. DeepSeek的实际决策角色

复用 `src/causalverse/evidence_s2/client.py` 的后端Key、超时、限次重试、官方端点白名单和脱敏；复用S1.1事实定位/引用校验。S2原 `d3-explanation-1` 及提示词版本保持原样。它只支持检测解释，不支持LIVE、诊断或动作方案，不能简单扩大输入后声称合同仍完全适用。

拟新增两个严格版本：

|合同|允许输出|验证与降级|
|---|---|---|
|live-diagnosis-analysis-v1|引用已发送事实，比较三方法候选，标明关系等级及证据不足；无自由数值|同owner/context/prefix/hash、事实语义与单位逐项校验；未登记关系拒绝；自由数值和确定根因拒绝|
|sim-plan-proposal-v1|从已批准目录选择目标、候选方案和证据；标注假设/拒绝原因|不能修改约束/权限；方案必须由确定性后端实例化并全量验证；LLM不能排除强制PI对照或安全候选|

DeepSeek参与证据选择、目标语义和候选方案提议；优化器负责数值动作搜索，安全层负责能否执行。最终选择依据要显示实际目标函数、可行性和反对证据，而不只引用LLM一句“建议”。全部方案都失败时返回REJECTED，不要求模型再次生成直至成功。

API超时、Key缺失、格式错误、引用拒绝或预算耗尽时，保留观测、检测及候选；继续既有已批准PI基线/安全状态，不产生新的LLM方案执行。不得回退到未经审核的自然语言指令。LLM处于慢速事件层，不进入1秒安全循环。

## 4. 事实验证与计划验证分开

原S1.1 `claims.catalog(context, snapshot_sha256)`、`resolve` 可用于兼容的证据投影；新数据必须先证明同结构、语义和状态映射正确。禁止为兼容把LIVE的chain写成D3，或在S1.1内部新增“忽略hash”分支。

事实引用校验成功只表示引用与解释结构可验证，不代表诊断正确、方案可行或控制安全。计划验证顺序：

1. 验owner/episode/context/as_of/前缀SHA，排除跨运行和过期提议。
2. 验证所有引用来自本次发送事实子集；拒绝虚构数值、概率、确定根因和未来观测。
3. 从后端受限目录实例化候选；检查通道、单位、动作含义、命令边界、持续时间及互斥。
4. 预测适用性、不确定性和原失败状态分别保留；无合格控制预测路线即拒绝。
5. 孪生隔离验证、安全约束、截止时间和退回策略通过后，才申请新仿真执行证书。
6. 执行前再核前缀/时钟/动作有效期；已变化则作废，不能用旧方案覆盖当前生产。

## 5. 数据与权限接口草案

新接口均为拟议，默认仅回环、同源、唯一端口；不能直接加到8768旧只读Handler而隐式开放控制。

|接口|角色与边界|
|---|---|
|POST /api/live/episodes|人工启动受控仿真会话；固定已批准配置；不接受任意文件路径|
|GET /api/live/episodes/{alias}/events?after=seq|只读采集、阶段和回执事件；支持断线续读；不返回隐藏状态|
|GET /api/live/contexts/{id}|同会话证据、事实和验证状态；无其他context路径访问|
|POST /api/live/analyses|仅已批准事件触发/显式请求；上下文ID，不接受任意prompt或Key|
|POST /internal/plans/validate|服务间受限；方案实例与前缀，不对LLM暴露工具调用|
|POST /internal/actions/commit|唯一执行器消费一次性证书，外部浏览器无直接命令字段|
|POST /api/live/episodes/{alias}/stop|人工紧急停止，优先级最高；绕开LLM和长任务队列|

故障注入是独立演示操作员接口，审计记录进入受限评估区，不能进入在线模型上下文。浏览器可在独立“操作员真值”区查看，默认诊断工作区不展示该内容。

会话Cookie使用新名称，HttpOnly/SameSite及CSRF/Host/Origin检查均保留；Cookie不按端口隔离，不能复用8769的 `s1` 名字制造跨服务会话覆盖。权限不能只靠网页按钮disabled。

## 6. 日志、成本与验收

按事实、提议、数值验证、执行、反馈分别记录输入/输出SHA；追加写入，保留失败与超时。私有身份映射、RNG、执行器内部状态、Key和未验证LLM正文不进入公开证据。S2私有失败诊断记录仍保持私有。

每次LLM调用记录本地/上游请求ID、模型别名、提示词/合同哈希、真实usage、attempts、发起/返回时间和缓存来源；模型别名不等于冻结权重。新持久预算按episode限定逻辑请求和重试预算，播放/采集tick不得自动调用API。

本轮付费调用0；未来S4/S5真实LLM验收需另行批准调用预算。离线回放可验证合同和界面，但不能代替新流程的真实调用证明。

验收必须包含真实冻结算法对照、LIVE身份拒绝、未来扰动隔离、跨context/假ID/数值/概率/根因/授权篡改、提示词注入、过期计划、Key缺失/超时和安全降级。完整闭环是否通过仍以执行回执和后续真实观测判定，不能以LLM返回VALIDATED代替。
