# TEP 数据来源、变量和实验数据规范

核查日期：2026-11-14。标准编号统一按 XMEAS/XMV 的 **1-based 编号**，Python 数组列为编号减一。来源以实际数值方程/变量定义为准，README 有错误时不照抄。

## 1. 数据来源与许可

|来源|实际内容与用途|代码/数据许可分别处理|
|---|---|---|
|[Braatz 参考数据镜像](https://github.com/jkitchin/tennessee-eastman-profbraatz/tree/master/data)|正常 d00 与故障 d01–d21，历史文件用于检测基线；3 分钟采样，名义训练 480、测试 960|根目录 LICENSE/readme.txt 对同目录代码和数据给出 Illinois 授权背景；数据目录没有独立标准许可证。保留来源、完整原文，勿直接标成 CC0|
|[Harvard Dataverse / Rieth 2017](https://doi.org/10.7910/DVN/6C3JR1)|四个 RData 文件，500 次运行，正常及 20 故障，训练 500 点/25h、测试 960 点/48h|已通过官方 API 核查公共领域奉献和使用条款；API 的 license 字段为空，不能机械写成“明确 CC0 SPDX”。条款允许复制修改分发且不得暗示背书|
|[TEP Python 后端](https://github.com/jkitchin/tennessee-eastman-profbraatz)|生成可控制种子、时刻、动作的实验轨迹；首版可行性验证对象|实际 LICENSE 为 Illinois/NCSA 风格，而 pyproject 宣称 BSD、meson 又宣称 MIT，需保留全部原始声明并标注冲突|
|[TEP-Rust](https://github.com/jkitchin/tep-rust)|20 标准扰动、53 通道、情景与调度；可作交叉后端候选|MIT AND NCSA；验证数据和自己生成的数据分别记来源|
|[pyTEP/扩展 TEP](https://github.com/ccreinartz11/pytep)、[DTU DOI](https://doi.org/10.11583/DTU.13385936)|扩展模型和数据线索，依赖 MATLAB 路径|包装代码 BSD-3-Clause；未对 DTU 文件许可及所有模型文件授权完成核查，首版不下载复用|
|[CIPCaD-Bench](https://github.com/giovanniMen/CPCaD-Bench)|含 TEP 因果发现评价数据和图线索|根目录未见 LICENSE，README 要求引用不等于明确复用授权，暂不导入数据或代码|

Harvard 官方元数据已保存为 `.research/harvard_dataset.json`：文件大小依次 47,327,663；24,678,017；836,882,037；494,063,194 字节，合计约 1.40 GB（十进制）。本阶段仅下载元数据，未下载四个大数据文件；其内部数组仍需实际读取核验。原始 API：[dataset metadata](https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/6C3JR1)。

## 2. 为什么有 41、52、53、55 及更多变量

- 41：XMEAS(1..41)，其中 1..22 是过程连续测量，23..41 是采样组成分析。
- 52：41 个测量 + XMV(1..11)，历史文件省略常量搅拌控制 XMV(12)。
- 53：完整 41+12，仿真输出可包含搅拌控制；不能将第 53 列当新增传感器。
- 55：Harvard 的 52 过程列 + faultNumber、simulationRun、sample 三个元数据列，官方 API 明确说明。
- 扩展 TEP 的额外测量/monitor 与标准 XMEAS 分开命名，不能把不同引擎同列号直接拼接。

历史 ASCII 文件存在行列转置风险，尤其 d00.dat。加载必须确认 shape，并根据明确的 52 通道模式校验，不能仅凭扩展名认定行是样本。实际文件形状检查见运行证据。

## 3. 全部 41 个测量变量

核查源码：[constants.py](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/master/src/tep/constants.py) 中 MEASUREMENT_NAMES/UNITS，并对照 [teprob.f](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/master/teprob.f) 和 Python 方程。kscmh 指千标准立方米/小时；压力为表压语义（kPa gauge），不能与模型内部绝压混用。

|XMEAS|测量名称|单位|
|---:|---|---|
|1|A 进料，流股 1|kscmh|
|2|D 进料，流股 2|kg/h|
|3|E 进料，流股 3|kg/h|
|4|A+C 进料，流股 4|kscmh|
|5|循环流量，流股 8|kscmh|
|6|反应釜进料，流股 6|kscmh|
|7|反应釜压力|kPa gauge|
|8|反应釜液位|%|
|9|反应釜温度|°C|
|10|放空流量，流股 9|kscmh|
|11|产品分离器温度|°C|
|12|产品分离器液位|%|
|13|产品分离器压力|kPa gauge|
|14|分离器底流，流股 10|m³/h|
|15|汽提塔液位|%|
|16|汽提塔压力|kPa gauge|
|17|汽提塔底部产品流量，流股 11|m³/h|
|18|汽提塔温度|°C|
|19|汽提蒸汽流量|kg/h|
|20|压缩机功率|kW|
|21|反应釜冷却水出口温度|°C|
|22|分离器冷却水出口温度|°C|
|23|反应进料 A 组成|mol%|
|24|反应进料 B 组成|mol%|
|25|反应进料 C 组成|mol%|
|26|反应进料 D 组成|mol%|
|27|反应进料 E 组成|mol%|
|28|反应进料 F 组成|mol%|
|29|放空气 A 组成|mol%|
|30|放空气 B 组成|mol%|
|31|放空气 C 组成|mol%|
|32|放空气 D 组成|mol%|
|33|放空气 E 组成|mol%|
|34|放空气 F 组成|mol%|
|35|放空气 G 组成|mol%|
|36|放空气 H 组成|mol%|
|37|产品 D 组成|mol%|
|38|产品 E 组成|mol%|
|39|产品 F 组成|mol%|
|40|产品 G 组成|mol%|
|41|产品 H 组成|mol%|

## 4. 全部 12 个控制变量

XMV 数值为归一化控制命令 **0–100%**，不是名称中的物理流量单位。流量响应受阀门动力学和压力等影响；XMV(12) 也是归一化搅拌控制，不得直接标为 rpm。方程根据归一化值转换为内部转速。

|XMV|控制对象|输入单位|
|---:|---|---|
|1|D 进料阀，流股 2|%|
|2|E 进料阀，流股 3|%|
|3|A 进料阀，流股 1|%|
|4|A+C 进料阀，流股 4|%|
|5|压缩机循环阀|%|
|6|放空阀|%|
|7|分离器液体排出阀|%|
|8|汽提塔产品排出阀|%|
|9|汽提蒸汽阀|%|
|10|反应釜冷却水阀|%|
|11|冷凝器冷却水阀|%|
|12|搅拌速度归一化命令|%|

首版核心观测 XMEAS(7/8/9/21)，辅以进料 1..6、产品 17/40/41、控制 XMV(1..4/10/11)。**XMEAS(21) 不是冷却水入口温度，IDV(4) 也不是冷却水流量故障。** 标准观测缺少入口温度和直接冷却水流量，诊断要承认部分可观测性。

## 5. 故障映射及真值边界

|IDV|标准定义|形态|
|---:|---|---|
|1|流股 4 A/C 比变化，B 组成固定|阶跃|
|2|流股 4 B 组成变化，A/C 比固定|阶跃|
|3|D 进料温度|阶跃|
|4|反应釜冷却水入口温度|阶跃|
|5|冷凝器冷却水入口温度|阶跃|
|6|A 进料损失|阶跃|
|7|C 供料总管压力损失|阶跃|
|8|A/B/C 进料组成|随机|
|9|D 进料温度|随机|
|10|C 进料温度|随机|
|11|反应釜冷却水入口温度|随机|
|12|冷凝器冷却水入口温度|随机|
|13|反应动力学|慢漂移|
|14|反应釜冷却水阀|粘滞|
|15|冷凝器冷却水阀|粘滞|
|16–20|历史发布描述为 Unknown|不猜测标签；可另做源码机制注释|
|21|历史文件的附加工况|20-IDV API 无对应 IDV(21)，本阶段排除；须先核查生成协议|

Rust 文档对 16..20 给出更细机制解释，但这些是该实现的机制注释，不能擅自改写历史数据的真实标签。历史 d21 文件存在也不意味着引擎可接受 21。故障类别标签、故障激活时刻和根因变量真值是不同字段。

Harvard 的 faultNumber 表示本次运行设定的故障类型，故障前的样本应标为正常状态。官方记录训练 1h、测试 8h 后引入故障；按时间比较定义标签，并明确边界样本的采集约定，不照搬第三方“sample≥160”的假定。

## 6. 新工况生成、重现和独立评估

1. 固定 engine_commit、backend、dt=1s（首轮与实现一致）、控制器与预热流程，显式 `backend='python'`，防止机器装有 Fortran 时自动切换。
2. 每次独立创建 TEPSimulator(random_seed=seed)，initialize 后进入统一预热，检验有限性、正常稳态漂移与是否停机。自定义初态需连同噪声与控制器状态记录，不能仅改传感器初值。
3. 通过 disturbances={4: (onset_hours,1)} 或 set_disturbance 注入故障；set_mv(10,value) 只在明确的手动/覆盖策略下使用。闭环 PI 会覆盖直接命令，需设计选择性控制器覆盖并记录实际命令。
4. 输出原始 1s/合适频率轨迹；检测对齐 180s 公共基线，同时保留组成分析仪更新时刻。组成测量具有不同采样/保持和延迟，不能把重复保持值当独立样本。
5. 训练/验证/测试按完整运行和不重叠种子划分；相同历史生成的行动分支必须归入同一 split，不得跨集。滑窗不能跨 split 或运行边界，标准化/PCA/图选择/阈值仅用训练与验证。
6. 每个动作和不动作对照使用相同历史；验证完整快照再分支。单种子短轨迹只证明接口，不证明稳健性。

目录建议：`data/raw/<source>/`、`data/generated/<engine_commit>/<run_id>/`、`experiments/<experiment_id>/{manifest,metrics,report}`。CSV 长表至少包含 run_id、split、t_seconds、变量原名、fault_config、fault_active、action_id、terminated；也可用每运行一份 53 列宽表加 JSON manifest。真实 IDV 和隐状态单独放评估真值文件。

## 7. 发现的上游质量问题

- README 的反应方程/状态范围与具体代码不可全部照单全收；本报告只采用核验过的变量映射。
- constants.SafetyLimits 把液位停机数值注释为 %，而实际 Python 方程使用液体体积 `vlr/35.3145` 等判断。这些值不能直接作为 XMEAS 液位百分比的 UI 阈值。正式安全监测必须核对方程和变换，另建配置。
- 包元数据版本 2.5.0 与 meson 1.1.0、许可标签不一致，说明打包元数据需清理。
- 未完成长时域 Fortran/Rust 差分验证，不能把 Python 版本视为已证明等价的真实工厂数字孪生。
