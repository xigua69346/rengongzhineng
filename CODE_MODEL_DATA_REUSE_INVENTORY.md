# 现有代码、模型及数据复用清单

日期：2026-11-16。项目根 `D:/广西人工智能大赛`；表内为根目录下真实路径。只读核查，不拷贝/修改模型，不执行fit、calibrate、simulate或付费调用。

## 1. 运行与模型资产

|资产|源码/参数/协议|复用方式与限制|历史验证入口|
|---|---|---|---|
|TEP数值引擎|`src/tep/{simulator,python_backend,controllers,constants}.py`、`PROVENANCE.json`|保留固定上游/许可；复用Python后端，不切换默认后端求展示提速|`docs/research/D2_VALIDATION_RESULTS.md`、`artifacts/d2/artifact_review.json`|
|仿真适配|`src/causalverse/simulation/adapter.py`|复用step、故障、限时控制、snapshot/branch；新增常驻进程包装；不修改旧适配行为|`tests/test_simulation.py` 5项历史测试，`scripts/validate_d2.py` 的25项及总汇|
|注册与身份|`src/causalverse/ai_runtime/{registry,identity,contracts,observation_reader,provenance}.py`、`model_registry.json`|原白名单/哈希只读；新LIVE注册层引用旧参数，不冒用D3/D511身份|`tests/test_ai_registry.py`、`test_ai_identity.py`；P0-01报告|
|检测算法|`src/causalverse/detection/{pca,threshold}.py`、`data/preprocessing.py`|复用scores/score/transform；原控制限、特征次序和OR逻辑不变|`tests/test_detection.py`、`test_preprocessing.py`|
|检测运行时|`src/causalverse/ai_runtime/detection_runtime.py`、`artifacts/d3/detection/model.npz`、`model_manifest.json`|原D3文件推理直接用；实时数组需新输入桥接，不修改旧文件准入|`tests/test_ai_detection_replay.py`、P0-02报告95项|
|机制识别|`src/causalverse/decision/mechanism.py`、`ai_runtime/{diagnosis_runtime,window_contract}.py`|原四变量、9套参数、候选扩展/拒绝复用；未知起点/动作后另验证|`tests/test_mechanism.py`、`test_ai_diagnosis_replay.py`；P0-03报告|
|四节点VAR|`artifacts/d5_1_2/VAR_model.npz`|只用于D5.1.2机制特征；不能替换成七节点VAR|`experiments/d512_mechanisms.py`、D5.1.2协议|
|D4局部模型/图|`src/causalverse/causal/dynamic.py`、`artifacts/d4/{VAR_model,SCM_model}.npz`、`process_graph.json`|模型/工艺边及局限引用；不视为当前运行重新识别的真实因果图|`tests/test_causal.py`、D4报告与`intervention_aligned/`|
|Action/Delta算法|`src/causalverse/decision/intervention_model.py`|真实ConditionalPredictor.predict及Base；不读未来a0；不跨起点直接滚动|`tests/test_intervention_model.py`、`test_intervention_integration.py`|
|冻结集成运行|`src/causalverse/ai_runtime/{prediction_runtime,calibration_loader,support_runtime}.py`|20成员全量、原joint区间、原支持与候选审计；研究路线继续false|`tests/test_ai_prediction_replay.py`；P0-04 178项|
|可靠性算法|`src/causalverse/decision/{action_support,intervention_calibration,uncertainty}.py`|原审计作为失败对照；新控制范围不得直接继承其资格|`tests/test_uncertainty.py`、D5.1.1报告|

`artifacts/d4/SCM_model.npz` 为D4拟合模型，所用线性结构/隐藏变量假设仍受限，不因参数已冻结变成已识别的物理SCM。

### TEP操纵通道核实

以下来自 `src/tep/constants.py` 和实际 `python_backend.py`，外部编号1-based。统一0—100为引擎命令范围，不表示这些通道均已通过自主控制研究。

|通道|实际操纵量|现有控制研究范围|
|---|---|---|
|XMV1/2/3|D/E/A进料命令|原PI回路；无自主优化验收|
|XMV4|A+C进料命令|D4作为U4观测节点；无自主调节验收|
|XMV5|压缩机循环阀命令|原PI回路；无自主优化验收|
|XMV6|放空阀命令|原PI回路；无自主优化验收|
|XMV7|分离器液体出口命令|原PI回路；无自主优化验收|
|XMV8|汽提塔液体产品出口命令|原PI回路；无自主优化验收|
|XMV9|汽提蒸汽命令|原PI回路；无自主优化验收|
|XMV10|反应器冷却水命令|D2/D4/D5的+1/+5百分点120秒研究；不是自动执行授权|
|XMV11|冷凝器冷却水命令|原PI回路；无自主优化验收|
|XMV12|搅拌速度命令|后端通过位置影响换热；标准控制器未作为已验证自主调节通道|

原控制器包含3秒快回路及更慢串级/组分回路；XMV10由C21回路及T9串级设定点共同影响。不能将“其余命令采用原控制器建议”写成所有通道都在每秒独立执行PI优化。首个新闭环只研究XMV10并监测其他单元安全，扩展进料/放空/液位/蒸汽通道需要新的耦合约束和实验。

## 2. 本轮实际参数结构检查

直接用 `np.load(..., allow_pickle=False)` 读取键/shape；没有实例化仿真或重新推理：

|参数|本轮核实结构|
|---|---|
|D3 model.npz|10键；mean/scale/constant/threshold_center/threshold_width/pca_center均41维；components(29,41)、eigenvalues(29)、explained_variance(41)|
|D5.1.2 VAR_model|mean/scale/noise(4)，coef(25,4)，lag/alpha标量|
|D4 VAR_model|mean/scale/noise(7)，coef(43,7)，lag/alpha标量；与四节点模型明确不同|
|Action ensemble|61键；bootstrap_seeds(20,20)；成员0—19各model_mean/scale(104)、model_coef(105,18)，全部成员参数有限|
|Delta ensemble|121键；Action所需字段之外，各成员base_mean/scale(33)、base_coef(34,18)，0—19完整且有限|
|support.npz|lower/upper/scale各(7)|
|candidate_support_ensembles.npz|880键，Action/Delta×四候选×20成员参数；完整恢复已由P0-04验收，本轮核对文件/键数及代表shape|

Registry共19条模型条目、18份不同参数文件，D3 PCA/Threshold共用一个原NPZ。三窗口Static/VAR/Logistic分别位于 `artifacts/d5_1_2/{static,VAR,logistic}_{180,600,1800}.npz`，窗口选择原 `selection.json` 三方法均1800，不重选。

Action/Delta校准使用 `artifacts/d5_1_1/calibration_action.json` 与 `calibration_delta.json`，q分别5.787873695670726和5.971070267917241；目标尺度[0.25,0.5,5]。原 `intervals_action_test.npz`、`intervals_delta_test.npz` 只能作计算后对照，不能给模型输入truth。

## 3. 数据复用与隔离

|数据|真实范围|允许用途|禁止用途|
|---|---|---|---|
|D3 raw/processed|`artifacts/d3/dataset/`，200运行、每条14400行1秒41测量/12命令；测试80运行|既有冻结回归、流式重放一致性、旧性能对照|把200身份核对说成200测试；未来/真标签进入决策|
|D4观测与配对|`artifacts/d4/`；七变量10秒、模型及配对动作研究|历史方向/总效应证据、同历史分支方法|把全部边当已验证直接因果；把内部阀位当标准传感器|
|D5.1.1|`protocol.json`、`data_log.json`、raw/observed/manifest；60种子×4背景×3动作=720分支|冻结预测、校准/失败对照；配对身份方法|720分支冒充720独立种子；observed.values未来输入；原测试种子用于新训练后还称独立测试|
|D5.1.2|9组feature缓存、diagnoses、原模型和协议；D3及外部80个a0历史|冻结核对、候选研究；新功能必须从原轨迹重建特征|直接读缓存冒充新推理；外部预测分支错配D3|
|新LIVE数据（未有）|未来唯一episode目录、原始分块和新manifest|新窗口/多轮控制研究；新资格独立验证|覆盖旧raw、沿用旧run_id、藏起失败|

评估器可持有故障计划、RNG、隐藏阀位等私有真值；在线模型和LLM只读允许的测量/命令及其事实。仿真内部孪生持有完整快照时必须标特权模式。原始full source SHA、实际观测payload SHA、inference identity SHA保持分工，不用一个全文件哈希冒充时间截断证明。

## 4. 证据、LLM和展示复用

|资产|实际文件|复用/缺口|
|---|---|---|
|证据快照|`src/causalverse/evidence_s1/service.py`|原调用真实模型、owner/hash核验与公开投影；新LIVE组装器另建，不改原白名单|
|事实与验证|`evidence_s1/claims.py`、`claim_schema_v11.json`、`knowledge.json`|复用引用和语义校验；新方案属于未发生计划，不混成FACT；旧规则完全保留|
|LLM客户端|`evidence_s2/client.py`|后端Key/官方域/JSON/超时/有限重试；无SDK安装需求|
|真实解释|`evidence_s2/{explanation,runtime,gateway}.py`、`explanation_contract.json`|原D3解释原样；新的LIVE机制/方案合同另版本，不在原S2里偷加动作执行|
|8769展示|`evidence_s2/console/`|五类卡片、折叠证据、dirty和历史来源交互可参考；不是主平台/实时控制已融合|
|七页|`frontend/src/{App,Chart,DetectionSummary,CausalGraph,PredictionPanels,ProcessHMI,TrustMetrics,HistoryCompare}.svelte`、`graphGeometry.js`|保留研究页面及已验收拖动/缩放/复位；新工作台首期独立，主站挂接另报文件范围|
|只读档案API|`src/causalverse/dashboard/server.py`|研究展示继续用；其包含future/truth的响应不能成为AI输入接口|

S2真实成功证据：`artifacts/ai_s2/real_20261116_162851/real_model_output.json`、`real_verified_analysis.json`、真实API审计及browser截图；原调用耗时/usage不是新系统实测成绩。无Key、拒绝和成功档案均保留。

## 5. 保护、版本与不可复用项

P0、S1/S1.1、S2全部历史清单继续保留，原8992与S1572记录不重新生成。P0-02用户创建的 `acceptance_summary - 副本.json` 已被历史授权保留，不自行删除。模型/数据/历史报告和证据一律只读。

原S2标签 `s2-real-deepseek-20261116` 指向提交9e828050399eff3506c5806638eca2e67d7c4765；收尾标签指向e05a2a48f23667c543b381e8ac150eee1d407c20。当前独立Git工作区干净；本轮无提交/推送。公开仓库只备份允许范围，大型原始轨迹与私有映射留本机，不能宣称GitHub已有完整13.5GB灾备。

以下不能作为现成能力复用：真正MPC优化器、未知起点已验证分类器、在线状态估计、任意起点可信Action/Delta、持久安全执行器、连续反馈策略、完整工厂孪生、正式现场通信和真实设备安全认证。旧文档提到DoWhy、PCMCI、RL或其他库，不等于本项目已实际使用或验证这些算法。

## 6. 复用验收

冻结路线按原测试/容差复核；新增桥接须先对同一原始D3流与P0-02逐点比较、同窗口对P0-03比较，再验证LIVE身份、未来隔离与新分布。参数恢复/推理时拦截fit、minimize、calibrate/control-limit估计；新的MPC优化实验与“冻结推理禁止训练”的测试进程分开，不能因为MPC需要优化而解除旧训练拦截。

本轮未重新运行既有84/178等测试；其结果来自已封存日志。新S3—S7测试须唯一目录、失败不覆盖，并在实施批准后执行。任何现有源码修改都需先给文件、原因、前后语义及风险；首期S3建议只新增18文件，不修改现有业务源码。
