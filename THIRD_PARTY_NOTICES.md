# CausalVerse 第三方来源与版权记录

D3 补充：新增模型算法使用 NumPy SVD/数组运算，自研阈值、T²/SPE与评估编排；可视化实际使用 Plotly Python 7.1.0（MIT），HTML内嵌其Plotly.js发行脚本并保留脚本版权头。原始TEP模块不变，D2 wheel继续保留，D3增量包版本0.3.0。Plotly安装元数据/许可随安装包保留，依赖精确版本见artifacts/d3/analysis-environment-lock.txt。

核查日期：2026-11-14。D2 新增独立仿真适配发行包；尚无完整业务应用。`src/tep` 是固定 commit 的未修改 Python 模块副本，使用自有 setuptools 打包，不修改原始审计仓库；wheel 内含 LICENSE.upstream 与 PROVENANCE.json。新增 CausalVerse 代码与第三方数值引擎分目录存放。下面保留第一阶段来源审核记录；调研环境依赖不等于 D2 运行依赖。引用论文不授予代码权利，代码许可证不自动覆盖数据、模型、品牌或图片。

## 已用于本地验证的来源

### Tennessee Eastman Process / jkitchin Python 版本

- 仓库：[jkitchin/tennessee-eastman-profbraatz](https://github.com/jkitchin/tennessee-eastman-profbraatz)。本地未改动 checkout：`.research/upstream/tennessee-eastman-profbraatz`，固定 commit `9a6c8e5fcef4a2850778704e7793c87b0a187005`。
- 原始作者：James J. Downs、Ernest F. Vogel；修改代码：Evan L. Russell、Leo H. Chiang、Richard D. Braatz；Python 包装：John Kitchin。
- 实际 [LICENSE](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/master/LICENSE) 版权：1998–2002 The Board of Trustees of the University of Illinois；Developed by Large Scale Systems Research Laboratory。授权为 Illinois/NCSA 风格，要求保留版权、条件及免责，二进制分发也要附带，不可暗示原机构背书。
- README/pyproject 的 BSD-3-Clause 和 meson 的 MIT 与实际许可证不一致。本记录不擅自替换许可，分发前保留全部原始声明，核对 Python 新增文件的授权覆盖及作者确认。不能把整个上游改名当原创。
- 完整许可快照：`.research/licenses/jkitchin__tennessee-eastman-profbraatz/LICENSE`；原始目录亦保留 LICENSE/readme.txt。当前只运行已有后端，未修改数值方程。自研脚本位于 `.research/smoke_feasibility.py`、`.research/check_reference.py`，与上游分开。
- 历史参考数据位于上游 data/，不是 CC0 数据；数据独立许可边界见 [数据分析](docs/research/DATA_SOURCE_ANALYSIS.md)。本项目生成的 NPZ 是本地仿真实验输出，来源同样登记为此引擎，不称真实工厂采集数据。

### DoWhy 与科学计算验证环境

- [DoWhy](https://github.com/py-why/dowhy)：MIT；原始版权声明见 [LICENSE](https://github.com/py-why/dowhy/blob/main/LICENSE)，本地快照 `.research/licenses/py-why__dowhy/LICENSE`，保留作者原文。安装并验证的发布版 0.14；主分支源码只用于能力/依赖审核。
- NumPy、SciPy、pandas、scikit-learn、NetworkX、statsmodels、pytest 等通过 pip 安装在 `.research/venv-tep`，用于独立研究测试。准确安装版本见 `.research/requirements-tested.txt`。各 wheel 自带 LICENSE/许可元数据，发布时应从锁定版本收集完整传递依赖 notices，不能用本文件几个直接依赖取代整个分发 BOM。
- 此环境不作为精简参赛发行包直接复制；编译运行库和数学库的额外许可也需保留。当前未复制预训练模型权重。

## 已审核但尚未集成的候选

|项目/作者或版权方|已查许可与来源|处理要求/当前状态|
|---|---|---|
|[TEP-Rust / John Kitchin](https://github.com/jkitchin/tep-rust)|[MIT](https://github.com/jkitchin/tep-rust/blob/main/LICENSE) + [NCSA](https://github.com/jkitchin/tep-rust/blob/main/LICENSE-NCSA)、[NOTICE](https://github.com/jkitchin/tep-rust/blob/main/NOTICE.md)|2026 John Kitchin；原始 Illinois 衍生部分的版权链同上；分发同时保留两份 LICENSE 与 NOTICE。未安装、未复制模型代码进业务|
|[TEP Studio / Khalid](https://github.com/khalidlabs/tep-studio)|[包装 BSD-3-Clause，2026 Khalid](https://github.com/khalidlabs/tep-studio/blob/main/LICENSE)|底层 temexd_mod 来自 Downs/Vogel、Bathelt/Ricker/Jelali；包装许可明确不扩张底层权利。授权未闭合，禁止作为已许可整体打包|
|[pyTEP / Christopher Reinartz、Thomas Enevoldsen](https://github.com/ccreinartz11/pytep)|[BSD-3-Clause](https://github.com/ccreinartz11/pytep/blob/master/LICENSE)|保留上游版权全文；MATLAB/Simulink 是独立商业依赖，未选用|
|[Tigramite / Jakob Runge 及贡献者](https://github.com/jakobrunge/tigramite)|[GPL v3](https://github.com/jakobrunge/tigramite/blob/master/license.txt)|只作离线研究候选；若组合/分发，审查整体许可兼容、相应源代码与许可证义务；不以隔离进程自动免除|
|[PyRCA / Salesforce](https://github.com/salesforce/PyRCA)|[BSD-3-Clause，2023 Salesforce](https://github.com/salesforce/PyRCA/blob/main/LICENSE)|拟用于基线；未在本机安装验证。保留声明、不暗示背书，具体算法论文按使用引用|
|[Causal-TS / Bloomberg Finance L.P. 及贡献者](https://github.com/bloomberg/causal-ts)|[GPL-3.0-or-later](https://github.com/bloomberg/causal-ts/blob/main/LICENSE)，源码头和 pyproject 一致|候选未集成；需要保留 NOTICE、版权头和相应源代码，处理同 Tigramite|
|[TEP-Claude-Code / ScottDuncanAI 仓库](https://github.com/ScottDuncanAI/TEP-Claude-Code)|[MIT](https://github.com/ScottDuncanAI/TEP-Claude-Code/blob/main/LICENSE)，版权行仅 2025|不得补造版权持有人；只参考实验流程，未复制业务代码或其性能结果|
|[CARLA / Tobias Richter、Martin Pawelczyk 等贡献者](https://github.com/carla-recourse/CARLA)|[MIT，2020 Tobias Richter](https://github.com/carla-recourse/CARLA/blob/main/LICENSE)|研究行动集合与对照；未安装或集成旧依赖|
|[Dash / Plotly Technologies Inc.](https://github.com/plotly/dash)|[MIT，2015–2024 Plotly](https://github.com/plotly/dash/blob/dev/LICENSE)|拟集成 UI 框架；锁版本后随发行保留 LICENSE 及前端 bundle 的第三方许可|
|[Dash Cytoscape / Plotly Technologies Inc.](https://github.com/plotly/dash-cytoscape)|[MIT，2017–2024 Plotly](https://github.com/plotly/dash-cytoscape/blob/main/LICENSE)|拟集成因果图；图布局扩展和 cytoscape.js 许可另随实际发行审计|
|[CIPCaD-Bench / Giovanni Menegozzo、Diego Dall'Alba、Paolo Fiorini](https://github.com/giovanniMen/CPCaD-Bench)|根目录未见明确 LICENSE|仅引用论文，数据与代码暂不复用；不能将“GitHub 公共可访问”视作授权|

上述许可证研究快照在 `.research/licenses/`（UI 组件见其源码链接）；这些快照不表示相应软件已集成。

## 数据、模型、图片

- [Rieth、Amsel、Tran、Cook，2017，Harvard Dataverse V1](https://doi.org/10.7910/DVN/6C3JR1)：已读取官方 API 和公共领域奉献条款，保存 `.research/harvard_dataset.json`。license 字段为 null，条款允许复制修改分发、不暗示机构背书；不擅自改写为已核实标准 CC0 许可证。尚未下载四个 RData 文件。
- [DTU 扩展 TEP 数据 DOI](https://doi.org/10.11583/DTU.13385936)：仅为来源线索，文件条款未核查完成，不导入。
- 未复用第三方预训练权重或未经授权网页图片。计划中的工艺图可用自绘 SVG 或在完整许可明确后复用有授权的流程图代码。

## 学术引用

1. Downs, J. J.; Vogel, E. F. A plant-wide industrial process control problem. Computers & Chemical Engineering 17, 245–255 (1993). [DOI](https://doi.org/10.1016/0098-1354(93)80018-I)。
2. Russell, E. L.; Chiang, L. H.; Braatz, R. D. Data-driven Techniques for Fault Detection and Diagnosis in Chemical Processes (2000). [DOI](https://doi.org/10.1007/978-1-4471-0409-4)。
3. Chiang, L. H.; Russell, E. L.; Braatz, R. D. Fault Detection and Diagnosis in Industrial Systems (2001). [DOI](https://doi.org/10.1007/978-1-4471-0347-9)。
4. Rieth, C. A.; Amsel, B. D.; Tran, R.; Cook, M. B. Additional Tennessee Eastman Process Simulation Data for Anomaly Detection Evaluation (2017), V1. [DOI](https://doi.org/10.7910/DVN/6C3JR1)。
5. 本项目用到具体因果/根因算法时，再按 [DoWhy](https://github.com/py-why/dowhy)、[PyRCA](https://github.com/salesforce/PyRCA)、[Tigramite](https://github.com/jakobrunge/tigramite) 官方引用要求补充。创新相关论文的准确来源见 [创新分析](docs/research/INNOVATION_ANALYSIS.md)。

## 发行前的具体收尾项

由依赖锁和实际 import/前端 bundle 生成精确软件清单，补全每个传递依赖的原始版权和许可；记录每段修改的文件、来源 commit、修改摘要；将第三方完整条款连同源代码/二进制一起交付；从最终发行包剔除授权未闭合或未选用候选。此记录不声称这些发行工作已经完成。
