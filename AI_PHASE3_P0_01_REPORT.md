# CausalVerse 第三阶段 P0-01：模型注册与数据身份校验

日期：2026-11-15，Asia/Hong_Kong。唯一实施范围为 P0-01。未实施 P0-02 至 P0-05 的算法、网关或页面。

## 交付状态

代码、独立单测和全量数据身份核对已完成；最终两个新增测试文件实际执行 **75 passed in 2.88s**；19 个注册项、200 条 D3 运行及 720 条 D5.1.1 分支核对全部通过，0 失败。本报告提交用户审核，不授权进入 P0-02。

当前实现只返回 READY / WAITING / REJECTED 的准入结果；READY 的 reason 为 `ADMISSION_ONLY_NO_INFERENCE`。没有检测分数、机制分类结果或预测结果，原 8768 网站仍是历史档案平台。

## 新增文件及职责

|路径|实现说明|
|---|---|
|src/causalverse/ai_runtime/__init__.py|静默包入口，无导入时加载、训练、推理或服务启动|
|src/causalverse/ai_runtime/contracts.py|独立 ObservationContext、InferenceRequest、EvaluationContext；列、单位、网格、时间、模型版本和动作合同拒绝码|
|src/causalverse/ai_runtime/registry.py|固定注册项、M0 可信文件源、目录边界、参数/依赖 SHA256、NPZ 键/shape/dtype/有限性/正尺度校验；不构造或拟合算法对象|
|src/causalverse/ai_runtime/model_registry.json|19 项注册记录；实际参数键、shape、dtype、来源代码/协议/训练校准引用、输入合同和原控制限|
|src/causalverse/ai_runtime/identity.py|从 split_plan、data_log、protocol 和原 manifest 解析逻辑数据引用、真实 run、split、branch、parent、snapshot；seed 仅作谱系检查|
|src/causalverse/ai_runtime/observation_reader.py|白名单观测投影、服务器 as_of 截断、raw/processed/D4 缓存核对、固定窗口、完整动作前历史和 command 交叉检查、重新解析源数据的准入门|
|src/causalverse/ai_runtime/provenance.py|确定性类型化序列化/哈希，显式 NaN/Inf 编码，独立 UUID、UTC/实际耗时、成功/等待/拒绝追踪；文件独占创建|
|tests/test_ai_registry.py|全部注册项与 20 成员、880 个候选支持数组、临时损坏副本、路径和禁止训练/仿真检查|
|tests/test_ai_identity.py|合法合同、错列/网格/单位、跨身份、未来截断、伪造上下文、窗口、动作、评价隔离和追踪检查|
|AI_PHASE3_P0_01_REPORT.md|本次报告|
|artifacts/ai_p0_acceptance/p0_01_20261115_210346_db1a9160/|本次唯一验收批次；提取/核对脚本、日志、JUnit XML、临时损坏副本、追踪、全量核对和哈希证据|

验收目录内逐文件完整清单以 `new_files_inventory.json` 为准（生成清单时不对其自身作递归哈希）。临时副本也是新文件，均局限在该批次；没有用正式模型制造失败。没有新增 P0-02 至 P0-05 的业务实现文件。

## 模型注册与参数核验

注册共 19 项、18 个独立参数文件：

|条目|覆盖|
|---|---|
|d3.pca / d3.threshold|共用原 model.npz；mean、scale、constant、Threshold center/width、PCA center/components/eigenvalues/explained 参数和 manifest 原控制限|
|d4.var7|原七节点 VAR，仅 D4 研究合同|
|d512.var4|D5.1.2 自己的四节点 VAR，coef(25,4)、lag6/alpha0.1|
|d512.static.{180,600,1800}|全部三窗口，含原 limits|
|d512.VAR.{180,600,1800}|全部三窗口，含 limits，并绑定四节点 VAR 参数依赖|
|d512.logistic.{180,600,1800}|全部三窗口，含 thresholds、iterations/loss|
|d511.action / d511.delta|各 0..19 全部成员；Delta 的 20 组 Base 参数；bootstrap_seeds(20,20)|
|d511.support|lower/upper/scale|
|d511.candidate_support|Action/Delta × 四背景 × 20 成员的全部 880 个数组，Delta 含 Base|
|d511.calibration_action / d511.calibration_delta|原 joint 与 actionwise 参数，无重新校准|

参数摘要与完整逐项 SHA256 保存在注册 JSON 和 `corpus_verification.json`。D3 参数 SHA256 为 `8a5cd3c24c5c32d85af005e2b31f9f968c89a96e534e8997d2353bbaa21c74a2`。

模型版本是本阶段新增的内容寻址标识，由参数哈希、输入合同、原代码和依赖哈希计算；没有虚构原实验已有语义版本。训练/验证/测试与校准信息以实际文件及源码引用表达，不补造不存在的逐模型训练证书。类顺序来自原四类协议/实现；原 NPZ 没有类名字段，不能声称从 NPZ 读取到了类名。

## 输入身份、时间与泄漏边界

- D3 只接受完整 41 列 XMEAS 原始 1 秒数据，按 t≥1800 且 t%180=0 重建，与原 processed 逐元素核对后返回 <=as_of 的行；不使用前端四列。
- D4 顺序 T9/C21/P7/L8/F6/U10/U4，10 秒网格，与同运行 D4 观测缓存核对。七节点模型与四节点合同混用明确拒绝。
- D5.1.2 只取 T9/C21/P7/U10，固定 [3600,3600+W)，W=180/600/1800。必须时钟到达窗口结束，不能在最后一个采样时刻提前返回 READY。
- D5.1.1 固定 5340..5390 秒 6×7 历史、5400 起点、动作 0/1/5、120 秒、六原时域。command 来自 observed.command，并与 data_log.command_before 和 raw.command_before[5400,9] 交叉验证。样例 test_631000_m14_a1 为 44.98640640212553，明确不等于 5390 秒 U10。
- 同 snapshot 的三动作还必须有同 split、同真实 parent_run_id、相同完整 0..5399 秒公开观测/控制历史摘要及 command；相同 seed/文件名/snapshot 字符串不能单独通过。
- `data_ref` 仅允许 D3:已注册运行 或 D511:已注册分支。在线请求字段白名单拒绝 future_truth、rng、hidden_valve、fault_id、future_trajectory、path 等。EvaluationContext 不可传入准入门。
- 读取 NPZ 的整文件字节用于 SHA256，允许物化的数组键由读取器固定。原始观测数组读取后先截断，再切网格/窗口；不会索引 raw 的 RNG/隐藏阀位、processed 的 y、D511 的未来 values/delta_values，或读取冻结预测档案充当输入。
- source_hash 表示完整源文件身份，input_hash 包含当前截断观测、身份、合同和源摘要；两者均记录。它不只是数值相等哈希，同值不同实验不会被视为同一请求。整文件校验本身不构成未来观测数值进入输入。

未来截断实际单测：as_of=1980 仅返回 (1800,1980) 两行；重复读取输入 hash 相同而 context UUID 不同；推进到2160后 hash 改变。临时改变读取后的未来观测值不改变原时刻输入。标量 NaN/±Inf 使用显式标记，数值数组使用 dtype、shape、C 序字节的十六进制编码，并归一化 NaN payload 位、记录非有限值计数；严格 JSON 不写 JSON NaN。相同逻辑数组的 C/F 内存布局 hash 一致，不同 dtype/shape 则区分。身份哈希排除 context UUID，追踪时间/耗时不混入输入哈希。

全量实际核对见 `corpus_verification.json`：200 条 D3 运行各重建70×41检测观测、1440×7 D4缓存，并检查全部三个 D5.1.2 四变量窗口；720 条 D511 分支均检查6×7历史、command 与三动作完整公开前史/parent/snapshot/split配对。耗时70.57秒，失败0，禁止调用记录为空。这里只核对输入/参数/谱系，不计算分类特征或模型结果。

## 实际测试和保护证据

使用既有 `.research/venv-tep/Scripts/python.exe`、`-B`、`-p no:cacheprovider`，仅运行两个新增测试模块；没有安装依赖、写旧 pytest 缓存或运行整个历史 tests。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
& .\.research\venv-tep\Scripts\python.exe -B -m pytest tests/test_ai_registry.py tests/test_ai_identity.py -p no:cacheprovider --basetemp artifacts/ai_p0_acceptance/p0_01_20261115_210346_db1a9160/tmp_attempt3 --junitxml artifacts/ai_p0_acceptance/p0_01_20261115_210346_db1a9160/tests_attempt3.xml -q
```

首轮64 passed in 3.76s；扩充测试后第二轮75 passed in 4.15s；数组哈希优化后最终第三轮 **75 passed in 2.88s**。三轮日志和 XML 全部保留，没有失败测试被删除或通过放宽标准改成通过。故障注入测试的预期拒绝属于正常通过，不是隐藏失败。

首次全量核对因逐浮点序列化在调用拦截下耗时过高而主动中止，退出码1，未计为通过；保留 `corpus.log` 和 `corpus_attempt1_interrupted.json`。优化确定性数组编码后完整重跑成功，证据为 `corpus_attempt2.log` 和 `corpus_verification.json`。这不是原始模型/算法变更，没有放宽比较标准。

M0 开发前完整核对：6418 项，0 差异，实际扫描约9.11秒。开发后复查为6418匹配；最终交付复查再次确认 **6418 匹配、0 变化、0 缺失、扫描期间变化0**，耗时9.40秒，并验证 M0 内嵌完整清单的摘要有效，详见 `hash_diff_final.json` 和 `hash_diff_delivery.json`。M0 报告本身另有 SHA256 锚定，值为 `632cd6e13f9e55d046830466250bb889a5c2d52d4b0e156651d2492f75e21b2a`。

原模型、校准、业务源码、实验数据、报告、前端、server、package/pyproject、build/dist、D6.1.1 记录均没有变化。未启动/重启原服务、未访问数据库、未训练、未校准、未仿真。新增测试通过运行时调用拦截和 NPZ 键访问拦截核对这些边界。旧38测试及七页浏览器成绩不计入本次验收；本次没有重跑浏览器。

638 项历史重建范围中 30 项缺第二阶段逐文件哈希的原证据缺口仍然存在；本次 6418 项保护结果不补造该历史证明。

## 未完成事项、风险和下一阶段建议

1. 本阶段只有本地 Python 准入 API，没有 HTTP 服务、实时数据入口或实际算法推理。服务器集成时必须由服务端决定 as_of，不能把客户端时间无条件当可信时钟。
2. D5.1.2 的 D511 外部样本来源已注册为协议证据，但读取器当前明确拒绝该跨数据集输入；其原轨迹特征重建留给 P0-03 的独立工程核对，不宣称本次完成。
3. 哈希证明文件身份，不证明数据分布适用性、未知故障泛化、因果识别或可靠优化。逻辑 snapshot 不是完整内部状态密码学快照；本次配对证明限于记录谱系和公开历史，没有读取隐藏状态补强在线结论。
4. 当前每次准入重校验文件，优先保证身份；没有模型或输入缓存，cache_hit 恒 false。不承诺实时延迟或清洁机器部署成功；现有环境的 SciPy 依赖声明缺口未修改。
5. 追踪基础可由 `trace_admission(lambda: reader.admit(request, context), ...)` 使用，也能包裹读取阶段失败；预上下文失败的 context/hash 为 null，保留明确 reason。未来每个服务请求必须在该边界内执行，避免调用者绕过失败记录。没有把准入追踪冒充模型结果追踪。
6. P0-02 建议仅在用户确认本报告后开始：复用 D3 注册项/读取器，恢复原标准化器、PCA/Threshold 参数，调用原评分函数；独立做80测试运行原评分/贡献/报警重放，阻断 fit/控制限重估，并证明移除冻结输出副本仍可计算。不要修改旧站点或提前推进分类/预测。

**本次到 P0-01 停止，等待用户审核。**
