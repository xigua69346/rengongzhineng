# 现有项目能力与最终目标差距审计

日期：2026-11-16。只读审计；没有运行训练、校准、仿真、模型推理测试或付费API。本轮读取源码、模型数组结构、既有协议/验收日志及保护清单；历史成绩不写成本轮新测试。

## 1. 审计依据与版本口径

已审阅根目录 `AI_COMPETITION_UPGRADE_PLAN.md`、`AI_SYSTEM_ARCHITECTURE_V2.md`、`AI_IMPLEMENTATION_ROADMAP.md`、`AI_COMPETITION_HIGHLIGHTS.md`、P0-01至04及S1/S1.1报告。旧计划中的“拟实现”以之后阶段验收为准。

S2结论以 `artifacts/ai_s2/real_20261116_162851/AI_PHASE3_S2_REPORT.md` 为准；根目录 `AI_PHASE3_S2_REPORT.md` 是等待Key准备版。收尾报告实际位于 `artifacts/ai_s2/closeout_20261116_173046/S2_CLOSEOUT_REPORT.md`，不是根目录同名文件。另核读D2/D3/D4/D5.1.1/D5.1.2及D6.1.1研究报告、原始协议和对应源码。

## 2. 能力矩阵

|目标|现有可核实能力|缺口/完成状态|主要源码与证据|
|---|---|---|---|
|连续生产仿真|1秒步进、闭环PI、20类故障注入入口；D2正常24h|缺少常驻生产任务、时钟/背压/恢复和监督服务；未完成在线业务|`simulation/adapter.py`、`tep/simulator.py`；`artifacts/d2/results.json`|
|数据采集|41测量+12命令；原始NPZ/CSV与manifest|文件生成已实现；可信实时事件流未实现|`simulation/adapter.py`、`data/generator.py`|
|异常检测|PCA/Threshold冻结推理；80运行×70时刻数值重放|只接受D3注册档案；新运行、新采样频率未验证|`ai_runtime/detection_runtime.py`；P0-02报告及95项历史测试|
|机制识别|9套参数、720组D3特征、1440条D3/外部评分，排序/候选一致|固定3600起点；未知起点自动诊断未实现|`diagnosis_runtime.py`、`window_contract.py`；P0-03报告|
|因果分析|7节点结构模型、工艺先验、候选Granger及有限配对总效应|没有完整工厂因果识别，也没有逐实时运行在线因果重估|`causal/dynamic.py`、`artifacts/d4/process_graph.json`、`intervention_aligned/`|
|动作预测|两套20成员；480条件均值/区间最大差0|固定5400起点、单次120秒动作；不能支持任意滚动优化|`prediction_runtime.py`；P0-04报告及178项历史测试|
|可信度|原joint半径、支持与候选分歧重算/审计|全部480区间宽度失败；原优化授权全部false|`calibration_loader.py`、`support_runtime.py`、原support/gates档案|
|证据服务|身份、截断、不可变应用快照、事实目录、引用验证|单机会话/进程索引；不支持持续实时运行恢复和跨系统统一身份|`evidence_s1/service.py`、`claims.py`；S1/S1.1报告|
|LLM|真实DeepSeek证据选择与严格回填|仅D3检测解释；不读取机制/预测，不生成可执行方案|`evidence_s2/{client,runtime,explanation}.py`；真实S2报告|
|控制执行|限时绝对命令覆盖；其余PI回路继续工作|没有自主策略、安全证书、执行API、抢占停止或反馈编排|`simulation/adapter.py`、`tests/test_simulation.py`|
|MPC|有名为economic_mpc的上游示例插件|源码明确“不使用实际MPC优化”；真正MPC未实现|`src/tep/controller_plugins.py` 的 `EconomicMPCController`|
|主平台|七页、回放、曲线、研究因果图、可信度与历史对比|主要读冻结档案，无自主运行主工作台|`dashboard/server.py`、`frontend/src/App.svelte`；D6.1.1报告|

以上简写路径在 `src/causalverse/` 下，`tep/` 在 `src/tep/` 下，项目绝对根为 `D:/广西人工智能大赛`。

## 3. 8768与8769的数据流差异

8768部署入口是 `src/causalverse/dashboard/server.py`；源码默认端口其实是8766，原8768需启动参数指定。本轮未启动、重启或验收该在线服务，不能用端口号替代实现证据。

旧接口 `/api/trajectory` 返回整条未来轨迹及manifest；`/api/detection` 返回历史NPZ并含y真值；`/api/diagnosis` 查diagnoses.json；`/api/uncertainty` 按独立D511条件查prediction/truth/上下界。浏览器按cursor隐藏未来只是展示限制，**不是可信后端时间隔离**。这些响应不能整体转发给LLM或在线决策器。

8769的 `EvidenceService.create` 真正调用检测、三种识别及适用的预测运行时，并投影白名单证据。D3没有注册D511配对则预测UNAVAILABLE；D511不适用D3的41列检测器。随机案例别名不能靠显示顺序、故障编号或seed猜测配对。S2解释只接受同会话D3检测事实，不支持把D511预测或D4图直接塞进提示词。

旧图是D4固定研究结构；七页当前run标题和拖动状态不表示对该运行重新发现因果图。S2收尾已修正文案并展示5类真实历史卡片；这不等于8768已接入在线推理。

## 4. 模型与实验的实质限制

本轮实际检查：PCA components `(29,41)`；Action 61数组、每成员模型均值/尺度104维、系数 `(105,18)`；Delta 121数组，另有33维Base及 `(34,18)`系数；两路线成员0至19齐全且参数有限。support为7维边界/尺度，候选支持为880数组。四节点VAR系数 `(25,4)`，D4七节点VAR系数 `(43,7)`，不能混用。

检测统计来自 `docs/research/D3_EXPERIMENT_RESULTS.md`：IDV4的PCA逐点Recall仅0.0283，IDV11为0.3642；曾检出20/20运行不代表持续检测可靠。180秒检测网格不能宣称秒级报警。

识别窗口固定 `[3600,3600+W)`，W为180/600/1800，验证选择均为1800。D3长窗Static/VAR/Logistic Top1分别0.975/0.95/0.9125，拒绝率0.5625/0.1/0.375。不能因接入LLM而宣称Logistic性能提升，也不能把低拒绝率直接当更准确。

P0-04的保守支持审计Action仅2/240、Delta12/240通过；这与原报告中的基础支持检查不是同一统计口径。joint全宽Action约2.894°C/5.788°C/57.879kPa，Delta约2.986°C/5.971°C/59.711kPa，全部超过原1/2/20门槛。20个独立测试种子的20/20联合覆盖，其精确95%区间下界约0.8316；不是总体90%覆盖已证实。IDV14稳定投影改善谱半径却使预测误差变差，负结果仍有效。

D4总路径37/40响应方向正确只限所测配对实验；主动探针校准不足导致唯一判断100%拒绝。不能从这些结果推出在线确定物理根因、全工厂因果识别或优化收益。

## 5. DeepSeek与证据能力的真实边界

真实S2验收列出4次调用，3拒绝、1VALIDATED；成功6041 tokens、3695.5601ms、5项发现。完整封存审计集合另有一条此前已存在记录，共5条；收尾已披露此统计范围差异，不改写旧报告。S3—S7必须按实际请求审计统计，不能硬编码“历史只有4次”。

DeepSeek输出rule与事实引用；所有数值和中文由后端回填，不是自由叙述或根因裁决。S1.1有关系分级合同，但当前没有已登记的正向关系事实供此最小解释使用。新决策合同不能通过添加自由文本字段绕过原拒绝规则。

## 6. 保护与Git核查

项目根目录没有.git；独立仓库位于 `artifacts/ai_s2/closeout_20261116_173046/version_repo`。本轮 `git status --short` 为空；HEAD为 `e05a2a48f23667c543b381e8ac150eee1d407c20`。本地两标签存在：`s2-real-deepseek-20261116`、`s2-closeout-20261116`。远程成功发布来自已封存 `git_publication.json`，本轮未重新联网核验远程，也未提交/推送。

原12194项预期按已封存767条收尾清单覆盖授权展示版本后，去重为12957项；本轮写前全部匹配，changed/missing/unreadable/verification_errors均为空。没有从当前文件重造历史预期。

锚点：原8992清单 `protection_final.json` SHA256为 `d55a4089a89e0472ed9b87e7e13248e07488bb1ff80982b8bda75847cfbf6923`；收尾清单SHA256为 `8ebeea2d784b21e1220dbe195df9dd354185762a3fdd61e0d6ffd2291ace6742`。

首次严格枚举将156项清单外文件列出并触发检查断言；随后只读归类确认：152项属于原核验脚本明确排除的两个运行追加目录，4项是与封存HEAD blob逐字节一致的P0清单副本。没有删除或补写任何文件，也没有把152项称为已封存验收项。该152项路径/内容集合摘要为 `6b407c44a3dfcdbc9e7eac0515894634aa65ba14ca1047866f3b0b094382c4b2`；后续复核须确认没有在本轮改变。范围之外的环境缓存不在12957项结论内。

八份文档形成后的只读复核结果如下；本表是本轮实际检查，不是引用旧日志：

|字段|写后结果|
|---|---|
|expected_count / checked_count|12957 / 12957|
|changed_hashes / missing_files|[] / []|
|unreadable_files / verification_errors|[] / []|
|unknown_files|[]；已明确区分本轮允许的8份新文档、152份运行追加文件及4份封存Git副本|
|运行追加集合|仍152项，集合SHA与写前完全相同|
|修改旧文件 / 新增业务代码|0 / 0|

本轮没有重跑会写历史目录的核验脚本，而用临时内存中的只读比较；旧基线、封存清单及证据未覆盖。八份新文档已计算SHA256，文档链接/UTF-8和代码围栏检查通过；这些静态文档检查不能充作S3—S7功能验收。

## 7. 差距优先级

1. 先补可信实时运行与身份：新LIVE合同、事件时间、原始观测白名单、唯一写入所有者。
2. 自动事件触发不等于冻结诊断可平移：必须验证未知起点窗口；不能从注入计划读取真起点。
3. 将可用于控制的新预测/孪生资格作为S5硬前置，避免先接执行再补可信度。
4. 建立方案合同、安全准入、可抢占停止、回执与多轮反馈；这些目前未实现。
5. 以未见种子完整闭环和PI配对基线评价，证据台与页面整合服务于此目标。

当前不能承诺哪类故障一定可恢复。首选候选为反应器冷却回路单故障；IDV4弱检出、IDV11随机性和IDV14粘滞都必须纳入验证，失败不能靠换一个演示案例从验收总数中消失。
