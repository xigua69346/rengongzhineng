# 创新分析与可验证研究方案

日期：2026-11-14。下文是研究假设和预注册实验设计，不是已取得的算法成果。

## 1. 相似工作与创新边界

|原始来源|已做的工作|本项目可以研究的差异|
|---|---|---|
|[Karimi 等，NeurIPS 2020](https://proceedings.neurips.cc/paper_files/paper/2020/hash/02a3c7fb3f489288ae6942498498db20-Abstract.html)|因果机制不完整时，以模型不确定性选择高概率有效的行动|不能把“模型集成+概率干预”作为新概念；转向闭环化工过程中的动作可执行性与机制失效|
|[Dominguez-Olmedo 等，ICML 2022](https://proceedings.mlr.press/v162/dominguez-olmedo22a.html)|对抗扰动下的稳健因果 recourse|研究阀门粘滞、控制器覆盖与时间演化；不声称首次稳健因果优化|
|[Weilbach 等，ACML 2023/PMLR 2024](https://proceedings.mlr.press/v222/weilbach24a.html)|贝叶斯机制模型表达反事实不确定性|首版不复制完整 GP 贝叶斯方法，研究小规模动态机制集合与仿真校准|
|[Time Can Invalidate Algorithmic Recourse，FAccT 2025](https://facctconference.org/static/docs/facct2025-206archivalpdfs/facct2025-final48-acmpaginated.pdf)|时间变化会让行动建议失效|动作需给出起始时间、持续时间及有效期限；比较静态和时序方法|
|[CIPCaD-Bench，CASE 2022](https://arxiv.org/abs/2208.01529)|TEP 等工业过程的因果发现基准|工艺图评价已有工作；不能把 TEP 因果图可视化称原创|
|[TEP Studio optimization.py](https://github.com/khalidlabs/tep-studio/blob/main/src/tep_studio/simulation/optimization.py)|已有 snapshot/restore、动作序列 rollout 和有限差分优化接口|“TEP+多动作试验+优化”本身已有高度相似模块；价值需来自诊断歧义和风险验证|
|[CARLA causal_recourse](https://github.com/carla-recourse/CARLA/blob/main/carla/recourse_methods/catalog/causal_recourse/model.py)|因果行动集合与成本搜索|可参考对照设计，旧依赖栈不适合直接集成|
|[DoWhy whatif/anomaly](https://github.com/py-why/dowhy/tree/main/dowhy/gcm)|已提供干预、反事实与异常解释原语|集成 API 属工程实现，不是算法创新|

检索包括 counterfactual industrial process optimization、causal decision optimization、robust causal recourse、TEP fault diagnosis/industrial RCA；截至本次检索未确认一个可原样复用、同时覆盖诊断歧义、执行器失效、动态 SCM 和成对 TEP 风险验证的完整开源系统。这只是检索结论，不能据此宣称世界首创或排除未检索文献。

## 2. 拟研究核心：诊断歧义约束下的动态稳健干预选择

重点场景：IDV(4) 冷却水入口温度阶跃、IDV(11) 入口温度随机变化、IDV(14) 阀门粘滞；用 IDV(5) 冷凝回路异常检验混淆。相同温压症状未必有同一根因，增加冷却阀命令也未必实际增加冷却能力。

候选贡献：**把候选故障机制集合与控制执行能力绑定，使用保持相同历史的仿真评估，选择在诊断歧义和执行器不确定性下仍可行的动作，并在证据不足时拒绝推荐。** 这是拟验证的方法设计；是否有独立创新价值要由消融和更深入文献查重决定。

动态模型：

\[
x_{t+1}=f_{m,r}(x_{t:t-L},u^{impl}_{t:t-L},e_{t+1}),\quad
y_t=h_m(x_t)+v_t,\quad
u_t^{impl}=g_r(u_t^{cmd},u_{t-1}^{impl},\xi_t).
\]

其中 m 为工艺结构/参数模型，r 为候选故障机制，e/v 为过程和测量噪声，g 表示执行器滞后、饱和与粘滞。所有使用的图需时间展开为 DAG；把控制输入直接当成传感器特征改数值不能构成可行干预。

个体 SCM 反事实按 abduction→action→prediction：

\[
p(e_{\le t_0}\mid y_{\le t_0},u_{<t_0},m,r),\quad
Y^a_{t_0+1:t_0+H}=F_{m,r}(history,e,do(\pi=\pi_a)).
\]

历史噪声可从选定可逆机制反演；未来噪声仍需采样。无法反演的内部状态用后验状态集合或重放分支表达，不能标成已识别的唯一真实个体反事实。

### 目标与约束

将每个场景 s=(m,r,seed,noise,delay) 的 H 步损失归一化：

\[
L_s(a)=w_T\sum_t ((T_t-T^*)/s_T)^2
+w_Q\sum_t ((q_t-q^*)/s_Q)^2
+w_C\sum_t\|W_u\Delta u_t\|_1+w_R R_s(a).
\]

质量 q 可选 XMEAS(40/41) 目标产品组成与 XMEAS(17) 产出；成本为可解释的相对资源/动作成本，未获真实价格时不得声称货币节省。R 为约束越界严重度及停机惩罚；提前停机不能因轨迹较短获得更低损失，剩余时域必须补失败惩罚。

\[
J(a)=\max_{m,r\in\mathcal P}\{\mathbb E[L_s(a)]+\lambda\mathrm{CVaR}_{\alpha}(L_s(a))\},
\quad
\mathrm{CVaR}_\alpha(L)=\min_\eta\left[\eta+\frac{1}{(1-\alpha)N}\sum_i(L_i-\eta)_+\right].
\]

\(\mathcal P\) 为在验证集上固定的可信机制集合，不把未校准根因分数当贝叶斯概率。对每个可信机制分别要求压力、温度、液位及动作边界满足验证阈值；经验违反率及置信上界单独报告。只有通过筛选的动作进入成本—效果 Pareto 集。有限样本通过不等于真实概率安全保证；例如 10 条全通过轨迹不足以支持 1% 风险承诺。

动作仅开放 XMV(10) 冷却阀偏置/温控设定点及有限进料减载；范围、速率、持续时间和控制模式必须显式记录。首版枚举 5–15 个动作模板，以全场景仿真作基准；当预算不足再研究代理模型筛选与 top-k 真仿真，不先上深度强化学习。

### 输入、输出与流程

输入：观测历史、正常基线、工艺图及假设、候选根因、可控变量/控制器、预算和约束、训练场景与独立验证场景。

输出：排序的可行方案、推荐或“证据不足/无可行方案”、温压质量轨迹及区间、相对成本、越界率、模型分歧、反事实假设与证据链。

1. 在正常训练数据拟合动态机制；采用滞后窗口的分块 bootstrap 构建小型模型集合。
2. 用 PCA 报警定位时间段，用机制残差和工艺先验形成候选根因集合。
3. 从故障入口推导可行动作；阀门粘滞时保留减载/设定点替代动作，不假设命令一定生效。
4. 对每个候选从相同完整历史创建基线/动作分支，固定扰动轨迹或核验随机数配对。
5. 计算损失、CVaR、约束违反和模型分歧；过滤不可靠方案。
6. 在未参与搜索的种子/扰动上验证短名单；选定方案并保留全部失败。
7. 从轨迹、机制和动作日志生成解释；记录无法识别的边与根因。

## 3. 可证伪创新假设

|假设|比较和判定|
|---|---|
|H1：保留诊断歧义能减少错误干预|完整机制集合 vs 只取 Top-1；固定仿真预算，比较未见故障背景下违反率与 regret|
|H2：执行器模型有价值|带粘滞/延迟模型 vs 命令即执行；重点 IDV(14)，比较实际响应与预测误差|
|H3：风险目标提高尾部表现|均值目标 vs CVaR/可信机制 worst-case；同时报告成本增加，不只选好看的指标|
|H4：因果候选筛选能节约评估|随机/全变量动作搜索 vs 根因后代路径筛选；同预算比较可行率、性能和耗时|
|H5：动态机制优于静态替换|静态 SCM vs 时间展开 SCM；独立轨迹上的效应误差和区间覆盖|

若 H1/H2 无效，保留负结果并把贡献收缩为可复现诊断—干预验证平台，不夸大算法。

## 4. 实验协议

- 正常与 IDV(4/11/14/5) 分别先计划训练 20、验证 10、测试 20 个独立种子，具体规模由首日单次耗时决定并在跑测试前冻结。所有行动臂从相同事前历史分支；每个种子作为统计单元。
- 检测对照：阈值、PCA T²/SPE；根因对照：最大标准化异常、PyRCA HT/EpsilonDiagnosis、机制残差排序。PCA 贡献仅为异常关联基线。
- 决策对照：不干预、固定冷却规则、单模型最小均值损失、等预算随机搜索、全场景枚举参考；高阶优化器不作为创新。
- 模型失配：移除一条先验边、变化时滞、噪声强度、动作延迟与未见故障幅值；不能把仅改变随机种子称为结构不确定性。
- 指标：二分类 balanced accuracy/Macro-F1、误报率与检测延迟；根因 Top-1/3 和未知类覆盖；效应 RMSE/区间覆盖；成本、CVaR、停机率、越界事件数/持续时长/严重度；跨种子均值和分块 bootstrap 区间。
- 结构评估在有可信局部真值时算时滞边 precision/recall/F1、SHD。专家工艺图是先验而非全系统唯一真值；不能使用同一张先验图拟合后再计算“发现准确率”。
- 故障 IDV 标签映射到扰动入口；测量值异常不等同物理根因。冷却水入口温度在标准 41 测量中无直接观测，需允许“不可区分/候选集合”，额外仿真监控量只能列为扩展观测实验。

当前仅执行依赖/API/仿真能力验证；上述对照实验及性能结论均待真实运行。
