# CausalVerse AI系统架构 V2（方案）

2026-11-15。依据[技术审计](AI_TECHNICAL_AUDIT.md)与[升级计划](AI_COMPETITION_UPGRADE_PLAN.md)。**本文件描述拟建架构，不代表服务已上线。本阶段不实施。**

## 1. 架构原则与边界

保留Python/NumPy/SciPy模型与Svelte/Plotly七页，旧只读服务、档案和模型一律不覆盖。新增旁路推理运行时与显式身份门，不引入LLM、神经网络框架、数据库或新SCADA平台。推理是按观测请求进行计算，不是修改模型或执行设备动作；计算接口不能存在set_control/inject_fault/execute_action。

```text
现有不可变档案                                  拟新增旁路运行时
raw / processed / manifest ──读取──────→ 观测读取器 + as_of硬截断
                                                      │
NPZ / 校准 / 协议 ──────────只读──────→ 模型注册表 + hash/契约门
                                                      │
                          ┌───────────────────────────┼─────────────────┐
                          ▼                           ▼                 ▼
                    D3 PCA/阈值                 D5.1.2识别       Action/Delta
                    41测量/180s                 4节点/10s        7节点/固定起点
                          └─────────────┬─────────────┴─────────────────┘
                                        ▼
                          上下文编排 / 支持检查 / 候选拒绝
                                        │
D4图/已配对证据 ───引用──────────────→ 结构化证据目录
                                        ▼
                           推理manifest + 解释 + 诊断报告
                                        │
冻结输出 ──仅在计算后读取──→ 独立比较器 ─┘
                                        ▼
                         经确认的七页增量接入 / 旧档案模式并存
```

图中是可用模块分支，不意味着每种输入都允许经过所有模块。D3和D5.1.1保留两条可验证案例链；不同数据集的节点不能因处在同一张界面就连成同次诊断。

## 2. 组件职责与文件映射

|拟新增模块|职责|复用的实际代码/资料|
|---|---|---|
|ai_runtime/registry.py + model_registry.json|固定模型版本、文件/预处理/校准hash、输入契约、已验证数据范围|审计重载逻辑、model_manifest、protocol、selection|
|identity.py / contracts.py|同运行/分支/起点身份门、变量/单位/采样/时域校验|D3 split_plan、D5.1.1 data_log与manifest|
|observation_reader.py|只读原始或既有processed；截断未来；保证不跨运行切窗|原preprocessing、变量映射和observed/permitted_observations|
|detection_runtime.py|冻结标准化与PCA/Threshold评分|Standardizer、PCADetector、ThresholdDetector|
|diagnosis_runtime.py|重建窗口、特征、签名/Logistic及候选策略|SmallVAR、MechanismEvidence、LogisticMechanism、conservative_candidates|
|prediction_runtime.py|全部20成员重载、有限时域点预测|ConditionalPredictor、Ridge，原fit不调用|
|calibration_loader.py / support_runtime.py|只读原半径与支持域；完整历史/命令/分歧检查|原joint校准JSON、support.npz、candidate支持参数、ActionSupport|
|workflow.py / evidence_catalog.py|允许链路判定、固定研究图证据、等待/拒绝/部分报告|D4 process_graph、对齐干预实验、D5.1.2外部复核协议|
|provenance.py / archive_compare.py / report.py|时延/版本/来源、计算后对照、报告|旧冻结输出仅作参考，不是计算输入|
|gateway.py（独立入口）|白名单推理请求与状态响应，复用旧只读适配|原dashboard/server.py保持只读未改；挂接必须另确认|

不将这些拟定文件说成已存在。本计划不要求新增微服务集群；一个本机旁路Python进程即可。标准库HTTP已足够验证原型，是否更换框架不属于P0必要工作。

## 3. 模型重载设计

### D3：检测

读`artifacts/d3/detection/model.npz`与model_manifest：冻结mean/scale/constant；PCA的pca_center/components/eigenvalues；Threshold的threshold_center/threshold_width及三项limits。PCADetector.scores产生T²/SPE/贡献/投影，Threshold.score产生传统分数；报警沿原严格`>`与PCA OR规则。T²与SPE不是再训练两套模型。

数据由41列XMEAS构成，保留原t≥1800、180秒网格，不能拿HTTP返回的四列直接当输入。原分析仪保持、抽样和变量顺序保持；不插值、不补零、不从测试重新估计尺度。

### D5.1.2：机制识别

按method/window唯一定位文件。Logistic恢复mean/scale/coef与原thresholds，Static/VAR签名恢复center/scale/means/variances/limits；VAR另加载四节点VAR_model的lag/alpha/mean/scale/coef/noise。恢复只赋参数，不执行fit/calibrate；用原特征函数和近分数扩展策略。

窗口是10秒网格[3600,3600+W)，输入为T9/C21/P7/U10。D4七节点模型不能替换四节点VAR；不因类标签可从文件名猜测而把它加入特征。缓存键包含窗口、算法和预处理版本。

### D5.1.1：有限时域预测

action_ensemble.npz中每成员的model_mean/model_scale/model_coef；delta另恢复base_mean/base_scale/base_coef。实际键包含成员前缀，参考scripts/audit_ai_readonly.py的重载实现。加载20成员并全部计算，预测输出shape=(6,3)，不删除不稳定或误差较大的成员。

历史严格为6×7：5340..5390秒，当前已发生命令与data_log的command_before及动作前原命令记录核对。预测起点5400秒，动作增量0/1/5个百分点、时长120秒；输出检查点为起点后10/30/60/120/300/600秒。真实类别不在predict签名里，也不通过类名选择本路线的权重文件。

读取本模型原joint半径q，使用[.25,.5,5]尺度给均值±q×尺度，不调用calibrate。单动作半径仅用于原对照展示，不能因分类或选择动作后拿其替换联合半径。当前“计算成功”和“满足可信门槛”是两件事，均须返回。

## 4. 数据身份、请求与结果契约

### 4.1 分离三个对象

**ObservationContext**（运行时可用观测）：data_ref、dataset_id、run_id、split、branch_id、parent_snapshot_id及证据来源、as_of_seconds、窗口[起点,终点)、变量表/单位、采样、观测hash、engine_commit/backend。seed可作谱系，不作分类特征。parent身份不能仅靠同seed推定；需同一实际snapshot/历史及日志核验。

**InferenceRequest**：context_id、task、method、model_version、允许的动作定义/时域、request_id。输入字段白名单，拒收idv/rng/hidden_valve/actual_future等模型不允许字段；选择实验背景只允许作为离线档案索引，不可投喂模型。

**EvaluationContext**（独立离线评价）：故障真值、实际动作结果、冻结输出、未来目标观测。其ID可链接到推理，但对象不传给模型执行器；预测器绝不能读取测试不动作未来结果代替Delta的学习基线。

### 4.2 结果必须包含

- inference_id、request_id、context_id、输入hash、模型/预处理/校准/策略hash、契约版本、输出hash。
- execution_mode：archive / recomputed_frozen / exploratory，明确当前结果不是新性能基准。
- status、计算结果、候选集合/分数/拒绝原因、适用性与证据等级；optimization_allowed固定false。
- 训练/校准/验证谱系引用，source_files与证据段落；时间记录采用UTC并在UI转香港时间，耗时用单调时钟。
- elapsed：加载、特征、模型计算、比较、总耗时；cache_hit和原始推理ID。缓存返回不冒称又跑了一次模型。
- reference_comparison：matched / mismatch / unavailable、容差、最大差、布尔结果是否一致。没有参考输出仍可运行，不能因此返回假match。
- output_scope：样本时刻/固定预测起点/六检查点，不暗示连续全轨迹区间保证。

拟定拒绝码：INPUT_SCHEMA_ERROR、FUTURE_INPUT、WINDOW_INCOMPLETE、DATASET_SCOPE_UNVERIFIED、ORIGIN_UNSUPPORTED、ACTION_UNSUPPORTED、CONTEXT_MISMATCH、COMMAND_SATURATION、MODEL_HASH_MISMATCH、NONFINITE_INPUT、CANDIDATES_AMBIGUOUS、EMPTY_CANDIDATE_SET、ENSEMBLE_DISAGREEMENT、INTERVAL_TOO_WIDE、AUDIT_ONLY_SUPPORT。复用原reasons时保留原文，不覆盖历史状态。

## 5. 两条可落地案例链与一条待研究链

### A：D3同运行重新推理

选D3 test_f14_00等合法运行 → 截断as_of后数据 → PCA/Threshold推理 → 同运行固定3600秒起的窗口完整后执行分类 → 加载D4图来源 → 报告候选与异常证据。

预测阶段在该链默认标**不具备D5.1.1已验证数据身份**，不自动切到631000。可以跳转独立预测案例，但必须新建context、清楚显示“另一实验”，不能同一报告假装完成预测。D3同样有七观测量不代表已验证干预预测迁移。

### B：D5.1.1同历史分类与动作预测（P1）

在已有不动作分支创建规范上下文，核对5400秒前历史、command_before、分支及parent。3600–5400秒1800秒四变量分类可复用D5.1.2 external研究范围；原始外部特征从轨迹重建的工程一致性应新增核对，而不是只读取冻结特征。

在as_of≥5400时将同一合法6×7历史输入Action/Delta，三动作均计算。**分类候选不作为预测输入**：两路线是跨四背景学习的共同模型，没有当前IDV参数。候选只用于组织解释和提示不确定，不对20成员删选、加权或缩区间。所有不稳定/分歧证据保留。

原D3 PCA用于此数据集的新增数值计算可标“适用性尚未在此协议验证”，不能附D3性能当作此链的检测质量。P0/P1不因此给出整链已验证的准确率。若要认证这一整链，先冻结P2协议。三臂未来真值只有在对应目标时间达到且评价模式允许时显示；原冻结预测可用于即时重放核对，但未来观测与故障真值不进入模型。

### C：自动告警触发链（P2）

真正未知起点下，告警时间不等于故障开始时间。记录trigger_time可先做工程事件，但旧分类器只验证[3600,3600+W)，不能直接将trigger_time代入该窗口。因此先返回window_policy_unvalidated，记录漏报/未触发，等待新协议；不能悄悄用真实故障onset纠正起点。

## 6. 状态机与智能诊断工作流

数据输入 → 输入校验 → 检测 → 诊断窗口 → 候选识别 → 证据引用 → 条件预测 → 可靠性检查 → 报告。

每段状态独立：WAITING、READY、COMPUTING、INFERRED、AMBIGUOUS、REJECTED、UNVERIFIED、FAILED。不要求全部绿色才允许报告；拒绝、未触发、窗口未齐和范围不符均是结果。没有报警不等于没有故障，特别是D3 IDV4/11；固定时钟评估允许独立执行合法分类，而“检测触发”模式不允许用后台真值补救漏触发。

候选多个：保留集合/排名与逐候选得分解释。空集：只表示已知签名不支持，不自动命名新故障。预测可在独立合同合法时计算，但不同任务的可信状态不能互相替代；候选单一不能使预测变可信，区间覆盖高也不能取消分类歧义。

报告区分：当前观测、冻结模型计算、离线研究证据、实际未来评价、历史总体指标。不能把测试集中20/20某项运行覆盖写成当前样本的100%故障概率。

## 7. 解释与七页最小增量方案

|现有页面|仅增量接入|保留的行为|
|---|---|---|
|总览|模型未加载/已加载/推理/缓存/档案状态，阶段context身份和断点|五段导航与回放时钟，不把不兼容阶段强制串联|
|监控|观测时间/采样/输入质量，当前检测推理ID|HMI动画、命令语义、既有配色|
|异常|新计算与冻结评分对照、贡献来源、正常/故障检测性能口径|当前时间门控、三节点时间线，SPE不等于原因|
|诊断|真实分数/候选/拒绝、特征/残差贡献、逐类与external评价|现有方法/窗口、非概率提示，失败保留|
|动态图|逐边basis/lag/kind/evidence与总路径实验引用|已验收统一坐标、拖动/缩放/复位；不重新发现图|
|可信度|同parent三动作、支持域/分歧/宽度原因、真实推理耗时|独立卡片/上下界、原区间、六检查点与独立实验身份|
|历史|推理manifest下载、同一上下文重放/差异|双运行对比、当前区间统计与原manifest|

UI挂接属于第三阶段待单独确认变更。默认新增frontend/src/ai下的组件，既有品牌不在本阶段变更；本项目定位在文档中采用用户指定CausalVerse名称，不擅自覆盖已确认页面品牌。

## 8. 运行、日志与可复现性

本机单进程旁路gateway复用既有Python类和本地只读文件；不再复制算法公式实现第二套检测器。模型按hash缓存只读对象，输出缓存按全契约键，切换运行/窗口/as_of时取消或丢弃旧响应。并发请求不得修改共享模型属性或跨运行追加历史。

新推理日志、结果、比较、报告只写`artifacts/ai_inference/<id>/`；旧raw/模型/报告不覆盖。可通过追加JSON/NPZ清单满足追溯，不需要数据库。文件路径从注册表解析，不接受任意绝对路径。未来若开放外网、多用户或现场设备，属于新部署范围，不能把本机只读原型当生产服务。

模型版本以参数hash为准，不能依赖当前包版本0.3.0或页面版本替代模型版本。重复回放应固定模型版本、输入hash、成员集和必要的随机种子；P0 Action/Delta本身确定性，D5.1残差模拟的随机过程状态必须另记，不能和TEP RNG混为一谈。

## 9. 准入与不可越过的门

实施前用户确认范围 → 不变性基线 → 参数重载/身份拒绝测试 → 全量冻结输出对照 → 端到端合同错误注入 → 经确认的七页小范围挂接 → 浏览器回归。

P0最多证明“冻结模型真实参与且正确重放”；P1最多证明“既有合同下可追溯集成”。未知起点、任意动作、现场泛化或可靠控制仍需P2新数据/协议。新路径即使得到数字，也必须携带适用性和拒绝状态，不以UI颜色替代验证。
