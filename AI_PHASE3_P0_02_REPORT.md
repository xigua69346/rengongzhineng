# CausalVerse 第三阶段 P0-02：冻结 PCA / Threshold 真实异常检测验收报告

日期：2026-11-15（Asia/Hong_Kong）。唯一授权范围：P0-02。

## 结果与停止位置

本阶段已调用原 `Standardizer.transform`、`PCADetector.scores`、`ThresholdDetector.score/contributions`，用冻结参数独立完成异常检测，再单独读取历史检测档案作对照。

实际新增测试 **95 passed in 98.24s**，JUnit 为95测试、0失败、0错误、0跳过。原始80个D3测试运行全部纳入，每运行70个时刻，共5600个检测时刻。全部数值最大绝对误差为0，22400项布尔报警完全相等。屏蔽历史检测输出后，再对全部80个运行独立重算，数值/报警与未屏蔽时完全相同；对照全部返回 `UNAVAILABLE`。

交付复查保护文件6496项，差异0：M0清单6418项、P0-01清单76项，以及M0报告和P0-01清单自身各1项。没有修改原有文件。P0-01的200个D3运行身份核对成绩与本阶段80个测试运行数值验收严格分开。

**P0-02完成并提交审核，到此停止。没有实施P0-03、P0-04、P0-05。** 原网站8768仍使用历史档案；本次能力是本地Python旁路运行时，没有接入七页或启动新服务。

## 新增文件完整清单与实现

|新增路径|实现及用途|
|---|---|
|src/causalverse/ai_runtime/detection_runtime.py|冻结参数恢复、原算法调用、检测结果落盘、三类哈希、D3专用计算后档案对照|
|tests/test_ai_detection_replay.py|80运行全量/屏蔽档案双重重算、禁止训练与控制限估计、时钟边界、未来文件扰动、无标签输入、严格报警与拒绝追踪，共95测试|
|AI_PHASE3_P0_02_REPORT.md|本验收报告|
|artifacts/ai_p0_acceptance/p0_02_20261115_214832_5873e745/|本次独占验收批次，含全部新计算结果、逐运行比较、拦截记录、临时副本、日志和文件哈希|

验收目录内每个实际文件的完整路径、大小和SHA256见同目录 `new_files_inventory.json`。该清单不对自身递归计算哈希，交付回复另提供其SHA256。目录没有覆盖P0-01或任何历史批次。

重要证据文件：

- `acceptance_summary.json`：80运行完整索引、误差、报警、raw/processed核对、算法调用和耗时。
- `replay/<run>/<inference_id>/result.npz`：本次实际重算的数组，不是历史输出复制；每运行含普通和屏蔽档案两次计算。
- 同目录 `result.json`：来源/模型/输入/合同哈希、推理身份、时刻范围、状态、耗时和NPZ SHA256。
- `replay/<run>/admission/<id>.json`：复用P0-01的准入阶段记录，明确区别于后续实际检测结果。
- `comparisons/<run>.json`：每个运行全部指标、原始容差、形状、误差、参考SHA256和匹配状态。
- `masked_comparisons/<run>.json`、`guards/<run>.json`：屏蔽输出后的UNAVAILABLE原因及原算法调用/禁止调用记录。
- `tests_attempt1.xml`、`pytest_attempt1.log`：实际95项测试执行结果；没有失败轮次被删除。
- `tmp_attempt1/test_future_file_changes_leave0/future_proof.json`：临时未来轨迹变化的三类哈希及评分不变证明。
- `tmp_attempt1/test_no_label_or_hidden_array_0/keys.json`：实际NPZ键访问记录，禁用字段访问为空。
- `tmp_attempt1/test_mismatch_is_reported_with0/intentional_mismatch.json`：临时参考数组故意扰动的MISMATCH证据；不是正式80运行验收失败。
- `precheck_initial.json`、`protected_expected.json`、`hash_diff_delivery.json`：开发前核对摘要、保护预期值及交付完整复查。
- `summarize_acceptance.py`、`audit_protection.py`、`summary.log`：仅本批次使用的独立聚合和保护检查代码/日志，没有执行旧审计写入入口。

原有P0-01的7个运行时文件、2个测试、报告及全部验收文件均保持不变。没有创建通用archive_compare/gateway或分类、预测模块；本文件内的D3专用比较函数仅满足本阶段“先算后比”的验收要求。

## 真实输入、参数恢复与输出

复用P0-01 `Registry`、`IdentityStore`、`ObservationReader`、`InferenceRequest`、`trace_admission`、`canonical/stable_hash`。没有重新实现注册、身份解析或观测读取。

输入只允许已注册D3逻辑引用。读取原始完整14400行、1秒采样、41列XMEAS，按原规则 `t>=1800 and t%180==0` 建立网格；服务端先用 `t<=as_of` 截断，再进入模型。每次读取均由原读取器与对应processed公开观测逐元素核对。全时域为1800..14220秒，共70行；没有插值、均值聚合、四列替代、补零或真实故障标签特征。

项目实际类名为 `Standardizer`，不是sklearn StandardScaler。只赋冻结属性：

- Standardizer：mean、scale、constant。
- PCA：center、components(29,41)、eigenvalues(29)、explained_variance、ratio。
- Threshold：center、width。
- 限值直接读取并校验原manifest：Threshold=1.3336688956481197，T²=52.959722682884994，SPE=12.664235365628597。

`d3.pca` 与 `d3.threshold` 均从注册表加载并核验自己的版本/依赖，且要求共用原D3参数文件。参数SHA256仍为 `8a5cd3c24c5c32d85af005e2b31f9f968c89a96e534e8997d2353bbaa21c74a2`。没有调用fit、fit_transform、calibrate或control_limit，没有重估中心、尺度、主成分数或限值。

每次返回列式数组，数组同一行对应一个 `observation_time`：T2、SPE、threshold_score、29维projection、41维T2/SPE/Threshold贡献以及pred_T2、pred_SPE、pred_PCA、pred_Threshold。共享metadata为每行绑定model_id/model_version/model_hash、源文件及输入哈希、inference_id、实际耗时、适用性、状态、reason和原限值引用。

报警仍为 `score > original_limit`，`pred_PCA = pred_T2 | pred_SPE`。等于控制限不报警；独立边界测试验证相等、仅T²越界、仅SPE越界三种情况。贡献度只解释统计量，不代表因果根因。

实际计算标记 `execution_mode=recomputed_frozen`、`status=INFERRED`。档案对照另标记 `archive_reference_only`，不修改已计算数组、不回填结果。缺参考为UNAVAILABLE；参考哈希错误为REJECTED；超过容差为MISMATCH。预热前WAITING、非法身份REJECTED、数值执行异常FAILED均留本批次记录，不返回伪造成功。

## 80运行数值和报警结果

比较原固定参考的每个元素；PCA的rtol=atol=1e-12；Threshold score及贡献rtol=1e-12、atol=0，额外记录真实绝对误差。报警逐元素完全相等。没有放宽容差。

|项目|全80运行元素数|最大绝对误差|最大相对误差（非零参考）|结果|
|---|---:|---:|---:|---|
|T²|5600|0|0|全部一致|
|SPE|5600|0|0|全部一致|
|PCA projection|162400|0|0|全部一致|
|T² 41变量贡献|229600|0|0|全部一致|
|SPE 41变量贡献|229600|0|0|全部一致|
|Threshold score|5600|0|0|全部一致|
|Threshold 41变量贡献|229600|0|0|全部一致|
|T²报警|5600|逐项完全相等|—|全部一致|
|SPE报警|5600|逐项完全相等|—|全部一致|
|PCA OR报警|5600|逐项完全相等|—|全部一致|
|Threshold报警|5600|逐项完全相等|—|全部一致|

全部80运行时刻数组与原参考完全相同；原raw→processed映射80/80精确通过，每运行70×41=2870个测量元素。接受结果没有读取processed.y或检测档案.y。保留全部80运行结果，没有选择最佳种子或删除失败样本。

这证明冻结模型工程重放正确，不是新的独立性能实验。既有IDV4/11漏报、统计异常与物理故障不同、贡献不等于根因等边界仍然保留。

可直接审阅的重算样例：`test_f14_00`，inference_id=`08f69c411f9c4f728a0a0c8fc92af16e`，完整数组位于 `replay/test_f14_00/08f69c411f9c4f728a0a0c8fc92af16e/result.npz`。以下只为阅读显示取12位有效数字，验收比较使用完整float64：

|观测时刻/秒|T²|SPE|Threshold score|PCA报警|Threshold报警|
|---|---:|---:|---:|---|---|
|1800|30.1444299424|7.34271513405|0.975637608510|false|false|
|3600|27.9428741687|2.46451688935|0.989947043771|false|false|
|5400|155.806680113|187.496233941|5.48428908521|true|true|
|14220|180.286297965|165.624899211|5.64056267940|true|true|

## 两项独立计算证明

95项测试中的80个逐运行测试，在普通重算和屏蔽重算期间都安装以下拦截：Standardizer.fit、PCADetector.fit、ThresholdDetector.fit、statistics.control_limit；函数调用profile另拦截fit/fit_transform/calibrate/control_limit/set_control/inject_fault、simulation和TEP源码。所有禁止调用记录为空，原算法实际调用数为：transform160次、PCA scores160次、Threshold score160次、Threshold contributions320次（score内部还调用一次contributions）。

每个运行先完成普通计算与对照，再在该测试实例的可信文件映射中屏蔽 `artifacts/d3/detection/test_*.npz`。第二次detect期间对历史输出的读取尝试必须为0，之后单独compare才触发一次“文件不可用”。全部80次屏蔽计算仍INFERRED，全部数组/报警与普通重算逐元素完全相同，对照80/80 UNAVAILABLE；没有查找其他参考补齐，也没有移动/修改正式检测文件。

另外用临时参考数组使一项T²偏移1，确认对照返回MISMATCH并记录运行、时刻1800、actual/reference、model_hash，已计算数组保持不变。该负例为测试映射，原档案未变。

## 三类哈希与未来边界

1. `source_file_hash`：raw trajectory、manifest、processed、split_plan各自完整SHA256；参数哈希及原限值引用另列。它证明文件身份，不作为数值特征。
2. `observation_payload_hash`：仅实际截断的XMEAS数组、dtype/shape、列顺序和观测时刻数组。新检测结果的input_hash是该值的别名。没有包含未来行、as_of、seed、run标签、源文件完整字节或UUID。
3. `inference_identity_hash`：真实dataset/run/split/branch/parent身份、逻辑引用、as_of、当前数值payload哈希、完整源文件哈希、模型版本/哈希、合同和本模块代码哈希。UUID、请求ID、时间戳和耗时不混入此确定性身份。

P0-01原context.input_hash仍按原定义不变，并以 `p0_01_context_input_hash` 单独记录，避免把它误称为纯数值哈希。

实际未来扰动测试在本批次临时目录建立仅含公开t/XMEAS/XMV的轨迹映射，显式更新该测试实例的可信哈希；只改变1980秒之后的观测与控制。变更前后raw完整SHA256和inference_identity_hash均不同，但as_of=1980的observation_payload_hash、全部评分/投影/贡献/报警完全相同。没有修改正式文件，也没有绕过正式注册表的完整性拒绝；正式源字节若意外变化仍应拒绝。

as_of=1799等待；1800返回1行；1979仍1行；1980返回2行；2160返回3行。1800和1979的可用观测相同，因此payload hash相同，而as_of不同使identity hash不同。NPZ键访问拦截确认没有索引y、rng_state、valve_position、future_truth、truth或delta_values。

## 实际执行、耗时与文件保护

环境为原 `.research/venv-tep/Scripts/python.exe`，Python3.12.14、NumPy2.4.6；没有安装或升级依赖。只执行新增 `test_ai_detection_replay.py`，没有运行全历史测试、仿真测试或旧写入型审计脚本。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$env:CAUSALVERSE_P002_EVIDENCE=(Resolve-Path artifacts/ai_p0_acceptance/p0_02_20261115_214832_5873e745).Path
& .\.research\venv-tep\Scripts\python.exe -B -m pytest tests/test_ai_detection_replay.py -p no:cacheprovider --basetemp artifacts/ai_p0_acceptance/p0_02_20261115_214832_5873e745/tmp_attempt1 --junitxml artifacts/ai_p0_acceptance/p0_02_20261115_214832_5873e745/tests_attempt1.xml -q
```

首轮实际结果95 passed in 98.24s，无失败。若复现须另建唯一批次目录，不能直接重用上述证据路径。

80次普通全运行计算，在测试调用拦截环境下，`elapsed_ms`（读取/校验/准入/加载/计算，不含后续NPZ落盘和档案比较）最小239.85ms、中位533.87ms、最大652.32ms；`score_elapsed_ms`最小0.167ms、中位0.380ms、最大0.615ms。读取器和准入多次验证原文件，未做缓存或优化；这些是本机实测，不承诺实时性能。

写前：M0 6418项、P0-01清单76项逐项SHA256核对，差异0，耗时8.89秒。交付复查：6496个既有文件全部匹配，缺失0、变化0、读取期间变化0，M0内嵌清单摘要有效，耗时12.56秒。期望值保存在本批次protected_expected.json，没有更新历史基线。

P0-01清单自身原先明确不作自引用哈希，本阶段把其当前已核验内容另作锚定，不能把该新锚声称为旧阶段已有的外部证书。M0报告另按P0-01注册锚核验。原638重建范围中30项缺历史逐文件哈希的问题仍未消失，本阶段不补造旧证据。

原模型、原数据、原校准、原Python、P0-01全部文件、前端七页、server、package/pyproject、build/dist和旧验收记录均未改。未启动TEP、未访问数据库、未启动/重启8768或其他网站、未进行前端构建、未重新做浏览器验收。

## 未解决事项与后续建议

- 未发现本阶段未解决的数值差异或验收失败。工程证明限于原D3固定协议下80测试运行的回顾性冻结重放，不能推断未知工况、现场泛化或故障识别质量。
- 当前没有HTTP入口/页面接入；服务器集成时仍须由可信服务器确定as_of。失败发生在准入前时，context/input hash可以为null，reason仍保存。
- 追踪包括P0-01准入阶段和本阶段检测结果两份记录；泛化缓存、工作流、跨模型档案对照及展示属于后续授权范围，没有提前实现。
- 后续若明确授权P0-03，可复用冻结注册和身份门，严格使用D5.1.2自己的四节点VAR和固定窗口，另验收720个D3特征窗口及外部样本重建；不能混用D4七节点模型或凭P0-02通过直接宣称诊断已实现。

**等待用户审核P0-02，不自动进入下一阶段。**
