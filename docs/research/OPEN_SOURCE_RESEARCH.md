# CausalVerse 开源调研与技术可行性报告

核查日期：2026-11-14（Asia/Hong_Kong）。范围：用户指定的 4 个 TEP 仿真项目、4 个因果项目，以及故障检测、行动优化和可视化补充候选。实际访问 GitHub API、README、许可证、构建文件、关键源码及官方文档，未开展大规模业务开发。

## 1. 推荐结论

阶段版优先采用 **jkitchin/tennessee-eastman-profbraatz 的 Python 数值后端 + DoWhy 0.14 + PCA + 自研动态机制根因/风险干预优化 + Dash/Plotly/Cytoscape**。这是有条件的工程选型：Python 源码已能在本机运行，但原包标准安装被 Meson 的 C 编译器要求阻断，且仍缺跨后端数值等价证明。不要把“纯 Python”解释成“原包无条件安装成功”。

**tep-rust** 是更有价值的数值保真候选与后续替代方向：许可链更清晰、原 Fortran 差分验证体系更丰富，但 Python wheel 未正式发布，本机无 cargo，Python binding 主要暴露批量 run，实时步进和控制接口需补桥接。当前 13 天工期不宜先安装完整工具链并重写接口。

**PyRCA 用来做对照，不强制放入线上链路。Tigramite/Causal-TS 先作可选离线研究。** 因果发现不是完成因果推理的前置硬依赖；首版用显式工艺先验、时间展开 SCM 和真实随机分配仿真动作完成识别/估计/验证。

## 2. 审核方法与证据等级

- A：本机实际运行；B：检查到实现源码/依赖/测试；C：上游 README 或论文声称；D：检索线索，授权或可访问性不足。
- 下表的日期为 GitHub `pushed_at`，不是最后发布日期、项目成熟度评分或最近实质算法修改；该字段可能包含文档推送。快照见 `.research/source_manifest.json`，关键源码索引见 `.research/source_review_index.json`。
- 优先 TEP checkout 固定为 `9a6c8e5fcef4a2850778704e7793c87b0a187005`。其他项目为当天默认分支观察，正式复用前需锁完整 commit/发行包哈希，不以 main 作为可重复依赖。
- 未拿 README 中的演示性能、检测准确率或作者验证数值当本项目实验结果。标准安装失败与源码导入通过分别记录。

## 3. 项目与许可、维护情况

|完整项目/真实地址|语言与实际功能|许可证核查|最近推送 UTC|复用判断/集成难度|
|---|---|---|---|---|
|[Tennessee Eastman Process Simulator](https://github.com/jkitchin/tennessee-eastman-profbraatz)|Python/Fortran；仿真、控制、检测插件、流式读取、Dash|实际 LICENSE 为 Illinois/NCSA 风格；元数据 BSD、meson MIT 冲突|2025-12-12|主候选：数值后端与接口、检测/仪表盘；中，打包需修复|
|[TEP-Rust](https://github.com/jkitchin/tep-rust)|Rust/PyO3/WASM/JS；原 Fortran 移植、场景与流程图|MIT **AND NCSA**，不能只记录 GitHub MIT 标签|2026-10-20|保真验证与 WASM 沙盘参考；中高|
|[TEP Studio](https://github.com/khalidlabs/tep-studio)|Python/C；modified TEP、Gym、snapshot、rollout、Dash|包装 BSD-3-Clause；LICENSE 明确不授予底层 C 模型额外权利|2026-08-30|功能贴近需求，但底层授权未闭合；暂不集成，高|
|[pyTEP](https://github.com/ccreinartz11/pytep)|Python/MATLAB；MATLAB Engine/Simulink 控制包装|BSD-3-Clause 包装；模型/数据另核查|2022-01-09|商业依赖和 Python 3.7 锁定；排除，高|
|[DoWhy](https://github.com/py-why/dowhy)|Python；识别、估计、反驳、GCM what-if/异常解释|MIT|2026-11-13|主因果框架；中|
|[Tigramite](https://github.com/jakobrunge/tigramite)|Python；PCMCI/+、LPCMCI、CausalEffects|GPL v3，具体源码头与 license.txt 已查|2026-01-14|离线时序图发现/稳健性对照；中|
|[PyRCA](https://github.com/salesforce/PyRCA)|Python；HT、EpsilonDiagnosis、Bayesian、RCD、random walk|BSD-3-Clause|2026-06-02|HT/Epsilon 对照与图编辑工具；中，隔离依赖|
|[Causal-TS](https://github.com/bloomberg/causal-ts)|Python；非平稳/稳态时序发现、effects/DoWhy 集成|GPL-3.0-or-later；pyproject 已查|2026-11-14|用户文档地址对应此仓库；功能多但依赖重，阶段版不必加入，中高|
|[TEP Fault Detection: MSPC vs ML](https://github.com/ScottDuncanAI/TEP-Claude-Code)|Python；PCA/MSPC 与监督检测对照脚本|MIT；版权行只写 2025，没有署名，保留原文|2026-03-04|参考评价流程，不照搬数据划分；中|
|[CARLA — Counterfactual And Recourse Library](https://github.com/carla-recourse/CARLA)|Python；行动集合、因果 recourse、成本与对照|MIT|2023-10-02|只参考算法/对照，旧 TF/Torch 依赖使整体集成不划算，高|
|[Dash](https://github.com/plotly/dash)|Python/JS；回调、图表与交互网页|MIT|2026-11-13|前端宿主，复用已有 TEP Dash 页面接口；低中|
|[Dash Cytoscape](https://github.com/plotly/dash-cytoscape)|Python/JS；可交互网络和样式|MIT|2025-08-09|因果图可视化；低|
|[CIPCaD-Bench / CPCaD-Bench 仓库](https://github.com/giovanniMen/CPCaD-Bench)|数据/图；工业因果发现基准|根目录无 LICENSE；代码构建不适用，不能假定开放授权|2022-11-02|论文与真值设计参考；不导入数据/代码|

授权记录与保留原文见 [第三方声明](../../THIRD_PARTY_NOTICES.md)。这张表区分“调研候选”和“已集成依赖”，不是软件 BOM 已完成的声明。

## 4. 安装、Windows 与代码质量尽调

|项目|依赖和 Windows 条件|源码、测试与文档证据|主要风险|
|---|---|---|---|
|TEP Python|Python≥3.8、NumPy；Fortran 可选；本机 CPython 3.12 源码导入通过|`pyproject.toml`、`meson.build`、`src/tep/{simulator,python_backend,constants,controllers,detector_plugins,dashboard_dash}.py`；tests/ 和 examples/；24 项仿真器测试通过|Meson 首行声明 C 导致无编译器安装失败；版本/许可元数据不一致；安全阈值单位注释错误|
|TEP-Rust|Rust 工具链、maturin/PyO3、NumPy；Windows 构建需匹配 MSVC 目标工具；Fortran 只用于 oracle 验证，不是交付运行依赖|`Cargo.toml`、`tepsim-py/pyproject.toml`、`sim.rs`、`wheels.yml`、`apps/studio/js/flowsheet.js`；book/notebooks/验证分层|无正式 PyPI wheel；本机未构建；Rust 有 step/Clone，Python Simulation 只公开批量 run，不得混淆语言接口|
|TEP Studio|Python≥3.10、CFFI、C 编译器、SciPy、Gymnasium；Windows 要 Visual Studio Build Tools；UI 可选 Dash|`core.py` 真实 advance/snapshot，`optimization.py` rollout/有限差分，`_cffi_build.py` 路径、tests 与 validation 目录|底层模型授权；编译；不同 modified TEP 版本不能混作同一数值基准|
|pyTEP|setup.py 明确 Python==3.7.*，激活 MATLAB/Simulink + Engine；README 有 Windows Anaconda 流程|README.rst、setup.py、requirements、`matlab_bridge.py` 实际 import matlab.engine；tests 在包内|2019–2020 MATLAB 兼容要求；包装 BSD 不覆盖商业软件授权|
|DoWhy|主分支 Python≥3.11,<3.14，NumPy≥2、现代 SciPy/sklearn 等；本机安装的是 PyPI **0.14**，不是当前主分支|README.rst、pyproject、`gcm/whatif.py`、`gcm/anomaly.py`、未观测混杂敏感性 refuter；测试目录完整|发布版与 main 依赖不同；自动模型搜索的 joblib 中文临时路径问题；反驳通过不证明识别假设为真|
|Tigramite|Python≥3.10、NumPy/SciPy/Numba；基础 ParCorr 不需深度学习；可选 sklearn/torch/ortools|README 假设矩阵、setup.py、license、`pcmci.py` 的 PCMCI/+ 实现；tests/tutorials|闭环、隐藏变量、非平稳和多采样率违反假设；GPL 分发义务|
|PyRCA|setup.py 名称 **sfr-pyrca**；sklearn≥0.24,<1.2、NumPy/pandas、JPype1；图发现某些路径涉及 Java/Tetrad，HT 不等于必须启动 JVM|`ht.py` 线性父节点回归残差，`epsilon_diagnosis.py` 相关变化/bootstrap；tests/examples/docs|旧 sklearn 与现代 NumPy ABI/版本冲突；服务监控算法不自动适应物理根因|
|Causal-TS|包名 **causalts**；Python≥3.10，torch、lightning、Numba、causal-learn 等；DoWhy 为可选 extra|README、pyproject（0.28.1）、GPL、`effects/query.py` 区分观察/干预，tests/examples|比单用 Tigramite 重；短赛程不必重复两套发现；GPL|
|TEP MSPC/ML|现代 pandas/sklearn、LightGBM/XGBoost/pyarrow；Windows wheel 是否可解未安装验证|README、LICENSE、requirements、`tep_binary_classification.py` 读取 52 列并训练检测器|脚本自称 quick reference；按行随机划分可能泄漏同运行/临近时刻；不复用其报告性能|
|CARLA|setup.py 锁 NumPy1.19.4、sklearn0.23.2、TF1.14、Torch1.7 等；现代 Windows 主环境不适配|README、LICENSE、setup.py、`causal_recourse/model.py` 的行动枚举与采样流程；test/|旧依赖；修改分类特征不等于过程控制干预|
|Dash/Cytoscape|浏览器+Python；Dash 包依赖从 requirements/读取，Cytoscape 带 JS bundle；无需为浏览预先自编前端|README/LICENSE/setup.py、Dash 服务源码、Cytoscape usage.py、TEP dashboard 源码|当前候选上游 Dash API 可能与旧 TEP dashboard 不同，要锁兼容版本；本次未启动 UI|

完整仓库不是都下载到本地。指定候选均通过远程源码审核；只有首选 TEP 进行 checkout 和本机运行。缺失文件/元数据不能当已确认功能。GPL 在分发组合程序时可能产生相应源代码与许可证义务；独立进程/JSON 交换只是架构选择，不能作为通用免责。应按实际分发方式和完整 GPL 文本评估，阶段版可不带这两个可选框架。

## 5. 仿真功能实际区别

|能力|TEP Python|TEP-Rust|TEP Studio|pyTEP|
|---|---|---|---|---|
|正常+故障|20 IDV，已测 IDV4|20 IDV，支持组合/幅值/时间表（源码/文档）|modified TEP 的扰动契约，需按 schema 对齐|模型决定，MATLAB 包装|
|调冷却水/进料|`set_mv(1..12,value)`；闭环会覆盖，要显式覆盖控制器|Rust 有场景 Action::Setpoint；不能假设 Python 任意阀门逐步控制已暴露|`advance(action, control_interval)` 12 维、snapshot/restore 明确实现|经 MATLAB 模型设置|
|在线读取|`step`, `stream_step`, `get_measurements`，已测|Rust step 可用；Python 目前批量 run|AdvanceResult 每控制周期返回状态和测量|经 Engine 交互|
|新实验数据|已能生成并保存；正式训练待数据协议冻结|run/to_numpy、dataset CLI；未在本机生成|TrajectoryDataset/OptimizationAdapter|可生成但商业软件依赖|
|Windows优先级|当前最易源码启动，有打包缺陷|长期候选，需要工具链与桥接|C 编译与授权同时阻塞|本项目不选|

## 6. 因果框架如何组合

DoWhy 的 CausalModel 路线负责显式定义图、识别 estimand、估计和反驳；GCM 路线负责机制拟合、干预采样和在可逆机制假设下做反事实。`interventional_samples` 和 `counterfactual_samples` 在源码中分开实现；不是对同一批预测改个名字。

Tigramite 的 PCMCI/+ 处理自相关和滞后发现，LPCMCI 可表达潜在混杂情形下的部分图，但输出不一定是可直接执行的完整 DAG。Causal-TS 已有非平稳处理和 DoWhy 集成，并非只有网页展示。两者都需要站稳假设后再用，不能让 UI 自动定向所有边。PyRCA HT 可以用给定图排名异常机制，EpsilonDiagnosis 是相关变化诊断基线；二者都不提供完整化工干预决策证明。

首版建议：先用工艺先验图建立局部动态 SCM，再以独立仿真干预检验关键方向和效应。后续用 Tigramite 的受约束发现提出候选边，作为敏感性模型集合的一部分。DoWhy 的 random_common_cause、placebo、data_subset、未观测混杂敏感性检验各有适用前提；时序子集需分块重采样，不能把 iid refuter 默认值当完整工业验证。

## 7. 故障检测/根因/优化与界面复用

- 故障检测优先复用 TEP 的阈值/PCA 插件接口和 sklearn 数值实现，但训练窗口、阈值校准、指标和按运行划分自己控制。PCA 贡献不称因果根因。
- 工业根因先用动态机制残差和工艺路径，PyRCA HT/Epsilon 作对照。候选机制、可观测性和 IDV 入口映射必须自研；标准数据未直接测冷却入口温度，Top-1 物理根因未必可识别。
- 反事实内核复用 DoWhy GCM，动态展开/证据反演/控制策略替换/完整历史分支自研。
- 多方案优化先用有限动作枚举；SciPy 的 [differential_evolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html) 可扩展低维有界非凸搜索，但可能消耗很多仿真，不能声称全局最优或原创。
- 界面已有可复用代码：TEP Python dashboard 的实时曲线/控制/CSV；TEP-Rust 的 Worker+SVG flowsheet；PyRCA Dash 图编辑工具。TEP Studio 有成体系 UI，但许可链尚未闭合。没有核实到现成系统提供本项目全部稳健方案比较、因果证据和报告链。
- 本赛程选 Dash，减少 Python/TypeScript 双栈；自定义工业流程主画布、因果证据侧栏和多方案轨迹。React 适合后续产品化，但不是当前第一优先级。

补充检索的 Merlion、TimeSeAD、深度故障检测课程项目只列入线索，不在本次复用短名单；未做完整许可证和关键源码尽调，不能直接导入其代码。检索命中 [vivekuw/sem_3_capstone](https://github.com/vivekuw/sem_3_capstone) 但 GitHub API 未返回可审核元数据，不据搜索摘要声称可用。

## 8. 本机验证记录

本节最终结果见旁边的 [RUN_VALIDATION.md](RUN_VALIDATION.md)，原始 JSON、版本锁与脚本位于 `.research/`。验证包括标准安装（失败）、源码运行、同种子一致性、IDV4 生成、冷却命令分支、在线读取、上游仿真测试、DoWhy 合成 SCM API，以及正常长轨迹。API 冒烟结果不等于已完成 TEP 因果效应实验或稳健优化对照。

## 9. 下一步决策

可直接复用：经审核的 TEP 数值后端/控制与检测接口，DoWhy 原语，sklearn PCA，Dash/Plotly/Cytoscape；使用时保留原项目来源和版权。

必须自主实现：故障机制与可控性映射、动态 SCM 的工艺约束、根因歧义集合、完整历史分支、执行器模型、CVaR/约束筛选与拒绝决策、独立实验和报告证据链。候选创新、公式和消融见 [创新方案](INNOVATION_ANALYSIS.md)。

进入业务开发的门槛：解决原包安装/适配问题，正常长轨迹和变量映射通过，关键冷却动作在控制器模式下确实生效，明确许可分发清单。开发计划见 [13 天安排](DEVELOPMENT_PLAN.md)。
