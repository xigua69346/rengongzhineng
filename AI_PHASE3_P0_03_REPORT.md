# CausalVerse 第三阶段 P0-03：冻结机制真实识别与候选拒绝

日期：2026-11-15（Asia/Hong_Kong）。本阶段只实施P0-03；P0-02已由用户验收通过。

## 验收结果

实际调用冻结Static、四节点VAR和Logistic原始算法，完成全部9套模型、三个固定窗口的独立计算。首轮新增测试 **39 passed in 86.14s**。D3特征720组、外部原始轨迹特征720组，D3/外部共1440条评分、排名、候选和拒绝结果全部与原档案一致。特征与评分最大绝对误差均为 **0**，没有放宽rtol=atol=1e-12。

屏蔽历史特征和diagnoses输出后，另外1440条评分仍独立计算成功，与未屏蔽计算逐元素完全相等，18个比较批次全部UNAVAILABLE。fit、fit_transform、minimize、calibrate、控制及仿真调用记录为空。

最终复查 **7281个已登记既有文件全部匹配，0缺失、0变化、读取期间变化0**。另对用户确认创建、要求保留的1个既有等值副本单独核验通过，共实际检查7282项；没有修改历史清单或把副本计为本阶段新增。原有业务源码修改数量为0。未实施P0-04或P0-05，没有修改前端、server或8768服务。

**P0-03实现及关键验收项已完成，本报告提交审核。到此停止，等待用户确认。**

## 新增文件与实现说明

|新增文件|作用|
|---|---|
|src/causalverse/ai_runtime/window_contract.py|复用P0-01观测/身份/校验，固定3600秒及三窗口；仅对原协议列出的外部test a0建立受限原始轨迹适配|
|src/causalverse/ai_runtime/diagnosis_runtime.py|全部9模型参数恢复、原特征/评分/候选函数调用、原始及扩展候选/拒绝输出、计算后D5.1.2档案对照及本阶段独立结果落盘|
|tests/test_ai_diagnosis_replay.py|18个完整批次、全部1440条评分的双重计算、专项拒绝/窗口/输入/七四节点隔离、禁止调用及无标签数组输入检查，共39项|
|AI_PHASE3_P0_03_REPORT.md|本报告|
|artifacts/ai_p0_acceptance/p0_03_20261115_220640_f306aab2/|本阶段唯一证据目录，含实际结果、临时负例、日志、清单及保护记录|

目录内所有新增文件的逐项路径、大小和SHA256见 `new_files_inventory.json`，自身不作递归哈希。该目录未覆盖以前批次。只新增上述两个运行时模块、一个测试模块、报告及该独立证据目录。

主要证据入口：

- `acceptance_summary.json`：18批次逐项统计、完整范围、算法调用次数、环境和失败列表。
- `all_scores.json`：主验收1440条完整评分、排名、原始候选、扩展候选、拒绝/原因和数据身份；不包含真实故障标签。
- `feature_index.json`：18份主计算NPZ的路径、SHA256及特征矩阵shape；D3共720行、外部共720行。每份result.npz含features、scores、ranking、raw_candidates、expanded_candidates和refused。
- `external_raw_reconstruction.json`：全部80个外部a0工况的原始轨迹引用/SHA256、真实engine_run_id、来源split、parent和snapshot，来自本次独立重建。
- `replay/<split>_<kind>_<W>/<inference_id>/result.json`：每条输入身份、时刻、四列顺序、评分、候选、拒绝、版本、参数/输入/来源哈希、实际耗时。
- `comparisons/`、`masked_comparisons/`、`guards/`：18批次逐运行比较、屏蔽后的UNAVAILABLE原因、调用拦截及原算法实际调用记录。
- `tests_attempt1.xml`、`pytest_attempt1.log`：首轮完整39项实际日志。
- `tests_rejection_evidence.xml`、`pytest_rejection_evidence.log`、`tmp_rejection_evidence/`：补充保存网格/变量/单位/未来/七四节点错误的实际拒绝文本，受影响6项重测通过。
- `tmp_attempt1/`：窗口未齐/非法起点/非法分支的持久化结果和空集、多集、近分数、矛盾孤立候选五类原始负例记录；全部保留。
- `precheck_initial.json`、`protected_expected.json`、`hash_diff_preimplementation.json`、`hash_diff_delivery.json`：初始工具核对摘要、累积保护预期及两次独立复查。
- `confirmed_scope_supplement.json`、`hash_diff_confirmed_delivery.json`、`finalize_delivery.py`：用户确认的既有副本、保留说明及确认后7282项最终复查；不替换7281项原保护记录。
- `audit_protection.py`、`summarize_acceptance.py`、`summary.log`：仅本批次使用的保护核对和证据聚合脚本，没有执行旧写入型审计/实验入口。

## 复用与输入合同

继续使用原环境、原模型和原算法，没有复制训练公式或重复开发P0-01/P0-02。复用Registry和可信文件读取、IdentityStore、ObservationReader、ObservationContext/InferenceRequest与原校验函数、provenance确定性哈希/准入记录，以及detection_runtime的数值输入hash函数。没有调用检测算法构造自动诊断触发链。

D3直接调用原ObservationReader的D512路径：先将同一真实运行的原始1秒41列/12控制列映射为七节点10秒观测，并与D4缓存同一时刻的values逐元素核对，再依原顺序 `values[:, [0,1,2,5]].copy()` 后切窗口。列顺序固定T9、C21、P7、U10；七节点原顺序仍为T9、C21、P7、L8、F6、U10、U4。原读取器和本阶段窗口校验共同拒绝错网格/列/单位/缺样本，不进行插值。

起点只能是3600秒；W=180/600/1800，窗口分别[3600,3780)、[3600,4200)、[3600,5400)，18/60/180行。服务器时钟必须达到窗口结束才准入，未到时WAITING。不能以最后采样早10秒为由提前计算，也不能把PCA报警时刻、故障编号或真实标签作为起点。

原selection.json的static/VAR/logistic均为1800秒、no_test_tuning=true。本阶段只读取保留，同时验收全部三个窗口，没有按本次结果重新选择。

## 外部原始轨迹重建

原P0-01注册表的D512 supported_scope和旧读取器仍保持不变，没有偷偷扩大为任意D511数据。新增WindowReader针对本次明确授权、原D5.1.2 protocol.external_runs中的80项作受限扩展：必须与原data_log记录完整对应，来源split=test、delta=0，并通过原IdentityStore的manifest/seed/trajectory SHA256检查；a1、训练分支和任意路径均拒绝。

每个外部工况从raw trajectory的公开t_seconds、XMEAS、XMV重新读取。先截断<=as_of、取10秒网格，复用七节点映射，再选[0,1,2,5]、copy、切行；不读取D511 observed.values、delta_values或冻结特征来构造输入。四变量布局与原permitted_observations列式结果一致，全部外部720组特征与原特征档案的最大差为0。

来源保持dataset=D511、真实source_split=test、branch/parent/snapshot；`split=external`只表示本D512评价角色，不把它改称D3运行或额外独立种子。80工况仍是20种子×4背景，仅a0；不是80独立种子或真实现场数据。本次结果为新的工程重建验收，未继承旧审计的external_feature_reconstruction=False成绩。

## 参数恢复、评分和候选拒绝

全部通过原注册项SHA256/依赖/键/shape/dtype/有限性检查后恢复：

|方法|恢复及实际调用|
|---|---|
|Static三个窗口|center、scale、means、variances、limits；原static_features均值/log std → MechanismEvidence.distances → 原softmax(-distance)|
|VAR三个窗口|签名center/scale/means/variances/limits；只恢复D5.1.2 d512.var4的mean/scale/noise/coef/lag/alpha；SmallVAR.residuals → 原residual_features → MechanismEvidence.distances|
|Logistic三个窗口|mean、scale、coef、thresholds、iterations、loss；原simple_features → LogisticMechanism.scores|

VAR另要求语义ID=d512.var4、coef(25,4)、lag=6、alpha=0.1。d4.var7在新增入口和旧Registry两层均明确拒绝，不能只凭shape推断兼容。

特征维度为Static8、VAR12、Logistic36，类别顺序固定[0,4,11,14]。Static/VAR原始候选按distance<=limits；Logistic原始候选按1-score<=thresholds。之后直接调用原conservative_candidates：前两名分差<0.05扩Top2，矛盾孤立候选补入第一名。没有改变阈值或强制唯一判断。

每条输出包含四类评分、排名、原始候选、扩展候选、refused及精确原reason：empty_candidate_outside_known_signature / multiple_candidates / singleton。空/多候选拒绝唯一判断；单候选状态仍为“模型内单一候选，非确定因果结论”。scores_are_calibrated_probabilities=false，optimization_allowed=false；0.8分不解释为80%故障概率。

原diagnoses没有保存扩展前原始候选字段，因此不虚构一份历史原始候选档案；本次保存实际阈值判断掩码和排名顺序下的原始候选，历史对照核验其已有评分、排名、扩展候选、拒绝标记和原因。

## 完整数值及拒绝对照

|范围|Static|VAR|Logistic|合计|
|---|---:|---:|---:|---:|
|D3特征/评分记录，三个窗口|240|240|240|720|
|外部原始特征/评分记录，三个窗口|240|240|240|720|
|主验收全部记录|480|480|480|1440|

1440行特征矩阵共有26880个特征值，评分共有5760个值。18个批次全部MATCHED：特征和评分最大绝对误差0；排名、扩展候选列表、refused、reason全部逐项一致。严格rtol=atol=1e-12，不删除异常运行。若有差异，比较器会保留具体run/method/window/变量顺序、完整实际/参考特征评分、排名、候选和拒绝原因；本次真实差异列表为空。

下表为各80条件中拒绝唯一判断的实际数量，与历史记录一致，不把拒绝改为成功诊断：

|评价范围/窗口秒|Static|VAR|Logistic|
|---|---:|---:|---:|
|D3 / 180|52|42|42|
|D3 / 600|39|31|37|
|D3 / 1800|45|8|30|
|外部 / 180|53|45|46|
|外部 / 600|42|36|44|
|外部 / 1800|42|11|37|

原冻结1800秒D3 Macro-F1仍为Static0.9749373434、VAR0.9484126984、Logistic0.9120050283。此处引用原metrics.json，不是本次新增性能试验；工程接入没有使Logistic优于Static/VAR，也没有升级概率校准、根因识别或七节点图发现能力。

## 独立计算、负例与实际测试

18个批次均在普通和屏蔽计算期间安装fit/minimize/calibrate拦截及函数profile；还禁止控制和TEP/simulation调用。原函数实际调用：LogisticMechanism.scores12次、MechanismEvidence.distances24次、SmallVAR.residuals960次。计数覆盖主验收和屏蔽重算；全部禁止调用列表为空。

每批计算完成后才允许比较器读取features与diagnoses。随后在该测试实例的可信读取映射中同时屏蔽两类文件，第二次推理对它们的读取尝试必须为0；再调用比较器才返回UNAVAILABLE。全部额外1440条评分的features/scores/rank/raw sets/expanded sets/refused与未屏蔽时逐元素完全相等，未使用其他文件补齐。没有移动、删除或修改正式档案。

专项测试保留窗口结束前1秒WAITING、0/3601/5400非法起点、错网格、错列序、缺变量、错单位、未来时刻、七四节点VAR混用、非法外部分支/路径，以及空集、多集、近分数、矛盾孤立候选、正常单候选五类案例。另拦截NPZ键访问，确认没有请求y、truth、rng_state、valve_position、delta_values或各split_y。真实故障标签没有传入特征函数或模型评分函数。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$env:CAUSALVERSE_P003_EVIDENCE=(Resolve-Path artifacts/ai_p0_acceptance/p0_03_20261115_220640_f306aab2).Path
& .\.research\venv-tep\Scripts\python.exe -B -m pytest tests/test_ai_diagnosis_replay.py -p no:cacheprovider --basetemp artifacts/ai_p0_acceptance/p0_03_20261115_220640_f306aab2/tmp_attempt1 --junitxml artifacts/ai_p0_acceptance/p0_03_20261115_220640_f306aab2/tests_attempt1.xml -q
```

实际首轮39 passed in86.14s，0失败/错误/跳过。补充负例拒绝文本落盘后，只重跑受影响6项：6 passed、33 deselected in1.16s；不是把两轮相加声称45个不同测试。未重跑全部历史tests或旧仿真测试。复现必须使用新的唯一证据目录，不能覆盖本批次。

环境使用原Python3.12.14、NumPy2.4.6、SciPy1.15.3，完整版本见summary；没有安装/升级依赖、训练/校准、重选窗口、启动仿真或写数据库。

## 累积文件保护

累积范围为M0原6418项 + M0报告1项 + P0-01全部新增77项（含清单自身）+ P0-02全部新增785项（含清单自身）= **7281**。6496只是上一阶段对更早文件的检查范围，不拿它冒充本阶段累积总数。

首次写前逐文件核对7281项，差异0，耗时11.50秒，见precheck_initial.json。保护期望值由原M0机器清单、两个阶段真实新增清单和P0-02已有protected_expected中的清单锚交叉合并，不重设原期望哈希。P0-02清单自身另核验上次交付回复的SHA256：ca9354947b6b8452b716627da8ecf427d8894bad29294dc03bb80f6e345da25e。

独立记录落盘时再次复查9.70秒；最终交付复查9.61秒，均7281匹配、0差异、0缺失、读取期间变化0，M0内嵌清单摘要有效。所有原模型、实验数据、校准、协议、历史报告/清单、P0-01/P0-02源码和证据、前端/server/build/dist均保持字节不变。

生成交付清单时，另发现P0-02目录中未登记的 `acceptance_summary - 副本.json`，因此暂停写入并询问用户。文件系统记录创建时间22:00:31，早于本批次22:06:40；其120326字节及SHA256与原 `acceptance_summary.json` 完全一致。用户明确回复“这是我创建的副本，保留并记录后完成交付”。现按该回复保留，不删除、不改写、不补入任何历史清单；在本批次单独记录为用户创建的既有范围补充文件，不算本阶段新增。

副本SHA256为 `8538844e3f8d7567939c71444fdff61a4da092d576bd6d9f3536e6e0abef0b48`，校验预期取自原已冻结摘要的哈希。确认后再次完整检查7281项登记文件及该副本，共7282项，0差异、0缺失、扫描期间变化0，耗时9.76秒，见hash_diff_confirmed_delivery.json。该范围差异已处理，最终新增文件清单将它明确列为保留的用户既有文件。

原638重建范围中30项缺第二阶段历史逐文件哈希的证据缺口不因本次匹配而被补造；本报告只证明当前累积保护范围未变。原站点仍为档案平台，本次没有重启网站、浏览器验收或页面挂接。

## 未解决事项和下一阶段建议

本阶段没有未通过的关键数值/候选/拒绝/外部重建/保护验收项。能力仍限于原固定时钟、四变量、四已知机制的回顾性冻结模型推理，没有验证未知故障起点、任意窗口、现场泛化、确定物理根因或自动闭环。

外部支持是本阶段针对原协议a0名单的显式适配，并未修改P0-01注册表，未来若要扩展其他数据范围必须另行授权。当前为本地Python入口，as_of必须由可信调用者决定；没有HTTP网关、缓存或前端，失败/等待保存在独立结果记录中。

如用户后续明确批准P0-04，再实施Action/Delta各20成员与Base恢复、原command/历史身份、六时域及原joint校准/支持审计；不能将本次分类Top1用来删成员、加权或缩窄预测区间。本次没有开始这些工作。

**完成P0-03后停止，等待审核。**
