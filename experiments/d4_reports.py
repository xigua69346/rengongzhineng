from pathlib import Path
import json,numpy as np
from causalverse.data.manifest import write_json,digest

R=Path('artifacts/d4');D=Path('docs/research');A=R/'intervention_aligned'
def load(name):return json.loads((R/name).read_text(encoding='utf-8'))
metrics=load('diagnosis_metrics.json');audit=load('audit.json');effects=load('intervention_aligned/effect_summary.json')
selected=[]
for kind in ('SCM','VAR'):
    p=np.load(R/f'{kind}_model.npz');selected.append(f"{kind}: lag={int(p['lag'])}（10s网格，最长{int(p['lag'])*10}s），ridge={float(p['alpha'])}")
(D/'D4_CAUSAL_MODEL_REPORT.md').write_text('''# D4 动态结构模型报告

## 模型及因果结论等级

本次真正实现可执行的局部线性动态结构方程、残差诊断和do命令递推；但它是**带工艺约束的约化动态SEM/候选SCM**，未证明是可识别的真实工厂SCM。函数可执行不等于潜在混杂已消除。若将其用于因果解释，必须附带机制稳定、历史充分、正确结构、可支持干预范围等假设。

局部节点为T9/C21/P7/L8/F6/U10/U4。公式 z_j(t)=b_j+Σ_l Σ_i∈Pa_j a_ijl z_i(t−10l)+e_j(t)。使用岭回归拟合；将时间展开后所有边指向未来，没有静态有向环。可观测控制器输出也单独建动态方程，覆盖某一命令时用do(U10=value)替换该节点，而不是更改全部测量。

未显式测得入口温度、实际阀位、反应组分等仍位于误差/潜在中介中，误差独立性没有成立证明。因此本阶段不声称后门调整已识别干预效应。DoWhy未参与本次拟合，避免把静态API当完整动态识别方法。

## 数据和拟合

只读取D3现有raw数据的XMEAS和XMV，派生到D4独立observations目录；不重新生成D3。原始1s测量精确抽取10s，当前选的5个过程量均为连续测量，两个控制为已执行历史。未使用组成分析仪的保持值；180s数据用于保留D3基线，不上采样成1s，也不把不同采样网格混算一个模型。10s网格也不与3s PI调度完全同步，可能产生控制相位混合；当前未显式加入控制时钟相位，这是局限。

20条正常训练运行从1800s预热后拟合均值、尺度和动态系数；10条正常验证运行在固定候选阶数1/3/6和岭系数.1/10中按一阶标准化MSE选择。每条运行单独形成滞后矩阵再堆叠，绝不跨运行边界。测试不调参。模型选择全记录在model_selection.json。

'''+ '\n'.join(selected)+'''

参数保存SCM_model.npz和VAR_model.npz；parameter_stability.npz保存20条训练运行各自重拟合系数及汇总系数，不能把不同缩放下的系数波动当物理效应置信区间。audit.json记录伴随矩阵谱半径和正常训练残差跨节点相关；谱半径接近1，长程响应敏感，不能由一步误差小推断干预正确。

## 比较与发现

静态基线是观测均值/对数标准差的候选机制签名，另保存完整正常相关矩阵；VAR是无工艺父节点约束的动态预测模型；SCM为受约束动态方程。Granger结果、PCMCI假设与许可比较见动态图报告。PCMCI未实际运行，不能把文档比较写成其性能实验。

TEP没有已确认完整观测层真值图，结构Precision/Recall/F1记N/A。单元测试的已知线性链只证明滞后设计及系数恢复实现可用，不是TEP因果图验证。

## 输入边界与保护

online observed()只接受41列测量与12列控制，再选择7个节点；接口没有IDV、RNG或内部阀位参数。机制训练标签只用于离线故障样本分组，测试真值只用于计分。诊断窗口使用预定实验时钟3600s起600/1800/3600s，所有正常和故障运行相同；这是已知计划的定位研究，不宣称未知故障起始时刻下的端到端在线诊断已完成。

D2/D3保护哈希、144条配对轨迹有限性及回归结果见audit.json/test_report.txt。核心代码src/causalverse/causal/dynamic.py；未修改D2 adapter.py或旧实验结果。
''',encoding='utf-8')

text='''# D4 根因候选与歧义分析

## 机制证据而非强制分类

候选为正常、IDV4入口温度阶跃、IDV11入口温度随机变化、IDV14阀门粘滞。正常作为显式备选，避免所有正常窗口被强行指派故障。训练故障标签用于拟合每类残差签名：均值、对数均方、滞后一阶自相关；静态对照使用均值/标准差。标准化后对角方差收缩距离仅为机制似然代理，不是物理故障后验概率。

本方法的“机制”来自已审核工艺图、动态残差和配对探针，但签名识别部分仍是监督统计模型，不能把其Top-1直接包装成因果推断成功。所有运行保留排名，同时用独立验证集校准候选集合。集合多于1或空集均输出“当前观测不足以确定根因”；空集另表示超出已知机制支持范围。

每类10条D3验证运行用class-conditional split conformal形式的90%阈值，第ceil((n+1)*.9)个分数；不使用softmax伪概率。解释需同分布运行交换性，窗口多重比较未提供联合覆盖保证。三种已知故障的Top-3若全部列出必然100%，不当创新指标；总体四类Top-3另报。

## 固定测试结果

|窗口s|方法|四类Top-1|Top-3|确定诊断覆盖率|拒绝率|错误确定/全部运行|
|---:|---|---:|---:|---:|---:|---:|
'''
for m in metrics:text+=f"|{m['window']}|{m['kind']}|{m['top1']:.4f}|{m['top3']:.4f}|{m['diagnosis_coverage']:.4f}|{m['refusal_ratio']:.4f}|{m['wrong_certain_rate_all_runs']:.4f}|\n"
text+='''
每行80条独立D3测试运行，含20正常与每故障各20。混淆矩阵、各故障Top-1与拒绝率见diagnosis_metrics.json；逐运行候选、距离、状态见test_diagnoses.json，全部误排名/拒绝/未覆盖真因见failure_cases.json。不能只展示60min的好看结果而忽略10min短窗。

IDV4与14在足够长的固定窗口、同版本工况下可以统计区分，但短窗可能混淆，并不构成一般可识别性定理。IDV4的快速瞬态和闭环补偿使D3逐点检测薄弱，而本次已知时钟的运行级签名保留瞬态/控制努力，任务难度与D3不同；不能直接把两种准确率相减称算法提升。

IDV11呈随机时变入口扰动，短窗形状和方差受种子影响，扩大窗口改善本数据中的签名区分；仍可能与其他未知扰动混淆。当前只覆盖三种单一故障，未测试组合故障/OOD，空候选拒绝机制不等于已验证未知故障检测能力。

## 主动探针是否有额外价值

配对实验训练4、验证3、测试5个种子，每个种子四类同历史分支。用+1/+5百分点探针相对不干预的温度/压力早期与晚期响应形成证据；实际输入仍只有允许的测量与命令历史，内部阀位只离线校验。

3个验证样本/类不足以提供有限90% conformal阈值，程序采用无限阈值的有限数值表示，所有类均保留，主动探针**拒绝确定诊断比例100%**。这是校准样本不足的真实失败，不用裁剪rank制造确定诊断。

主动排名和同批被动基线结果见intervention_aligned/intervention_metrics.json与paired_passive_metrics.json。被动和主动都使用截至6000s的证据，但主动需要额外两条分支/更高仿真预算，不能忽略预算比较。主动证据本次未显示优于被动，保留负结果。
'''
(D/'D4_ROOT_CAUSE_ANALYSIS.md').write_text(text,encoding='utf-8')

text='''# D4 配对干预验证

## 预先固定的协议

不改变D3数据。新D4实验用12个新种子（训练4、验证3、测试5），先共同运行3600s，snapshot后分别保持正常或inject_fault(4/11/14)，运行至5400s。每个故障状态branch为不动作、当前合法XMV10命令+1、+5百分点三臂，动作120s，再观察至6000s。全部144条完整轨迹及manifest在pairs/，没有冻结其他PI。

A正常/故障比较，B同历史IDV4/14比较，C不同命令比较，D跨种子重复性均由此协议覆盖。pair_log.json记录恢复重放一致性、停机与时域；cross_fault_pairing.json记录跨故障RNG比较，已测48组与正常配对均相同。每个动作与不动作逐秒RNG和入口温度均一致，不把额外随机输入误作动作效果。

do动作施加在命令而非传感器或真实流量。+1是相对**当前命令**，不是D2小死区测试的相对已接受阀门目标；IDV14下当前命令可能已经积累偏差，+1也可能突破死区。不能把“粘滞”错误建模为永久锁死。

## 效应估计与独立测试

使用正常训练拟合、验证集选定的结构方程递推，命令节点do替换，其他节点包括控制反馈继续递推。对5400s前的历史构造基线与动作预测；命令在5400s历史节点立即替换，再预测5410..5990s，共59个10s点。对照同时间TEP测量差，不使用测试轨迹调整系数。

模型未执行外生噪声反演的abduction，递推结果是候选模型的确定性均值响应，不能称为已识别的个体反事实。这些是已知模拟系统中的配对机制干预，并非现实工厂个体反事实的已识别结论。模型将遗漏执行器/入口/组分等状态折到误差，不能期望等价数值模型。

|输出|独立测试平均效应绝对误差|平均响应方向正确率|RNG/入口配对|
|---|---:|---:|---|
'''
for r in effects:text+=f"|{r['target']}|{r['mean_absolute_effect_error']:.6f} {'kPa' if r['target']=='P7' else '°C'}|{r['direction_accuracy']:.3f}|{r['all_rng_paired']}/{r['all_inlet_paired']}|\n"
text+='''
每输出40个比较=5个测试种子×4故障背景×2动作；并非40个独立种子。effect_seed_bootstrap.json按完整种子分组重采样，只有5组，区间应谨慎解释。逐方案真实/预测曲线、峰值响应时刻、误差、方向不符均保存；峰值时刻不是物理传播时延的因果识别。

总路径U10→冷却水温度/反应釜温度/压力获得已测动作范围内的方向证据，未对每条内部边独立做干预，也未检验全部工艺边。本次只能支持约化总路径，不能拆出入口温度与阀门状态各自唯一观测层效应。效应幅值误差较大，模型尚不能承担精确反事实优化。

## 所有失败与分析修正

初版效应分析预测与真实轨迹曾错开一个10s步。保留根目录旧intervention_effects.json/effect_*.npz，正式结果使用intervention_aligned/：包含5400s初态和对应do历史节点，比较5410..5990s。修正只涉及时间索引，未重训、重选模型或覆盖旧结果。修正脚本中曾出现OUT变量初始化NameError，修复后运行；该次未产生新数值结果。

intervention_aligned/intervention_failures.json保留所有方向不符、配对失败或绝对误差>0.1的测试案例。0.1仅作审计筛查阈值，不是不同单位统一的科学验收门槛。定量结果另按°C/kPa分别报告，不按该阈值删样本。

主动机制排名Top-1=80%，但在所需90%候选校准下全部拒绝确定诊断；不把排名准确率包装成确定诊断成功。正常/故障统计分离不能证明隐藏机制在所有工况下可辨识。
'''
(D/'D4_INTERVENTION_VALIDATION.md').write_text(text,encoding='utf-8')

text='''# D4 实验结果与验收结论

本阶段完成局部动态SEM/候选SCM、机制残差排名、歧义集合和实际配对干预验证。结论是**有可执行结构模型和局部方向证据，但没有证实完整因果识别，也没有获得相对静态/VAR的可重复优势**。

## 验收九问

1. 建立了带10..60s历史、可do命令递推的局部结构模型；隐藏变量与残差独立性未解决，不能声称唯一真实SCM已识别。
2. 每条先验边的原方程/控制器依据、直接/间接类型、未验证状态在D4_DYNAMIC_CAUSAL_GRAPH.md和process_graph.json逐条记录，未用PCA贡献添加边。
3. U10至C21/T9/P7的约化总路径有配对干预证据；其余工艺边未被单独验证。预测平均响应方向37/40正确，幅值仍有明显误差。
4. IDV4/14在本次固定长窗口中能统计区分；短窗和诊断候选仍有歧义，不推广为普遍可识别。
5. IDV11短窗随机形态增加残差和种子差异；扩窗改善本组识别，但不保证未知随机扰动下仍有效。
6. 短窗、多个候选、超出支持范围以及校准样本不足时拒绝唯一根因。主动探针90%校准因每类仅3验证种子而100%拒绝，不能声称成功确定诊断。
7. 未发现动态结构模型对静态或VAR的可重复Top-1改善。全部预定窗口和按运行配对bootstrap都报告，不选最佳窗口作为唯一成果。
8. 存在明确闭环反馈及部分可观测问题；残差相关小也不能证明无混杂。缺少入口温度、真实阀位、组分等，仍是核心技术障碍。
9. 干预结论只在本固定TEP实现、单故障、指定工况、+1/+5百分点120s动作和所测种子范围成立；不是工厂安全/生产收益证明。

## 全部方法与窗口

|窗口s|方法|Top-1|四类Top-3|确定诊断覆盖|拒绝|错误确定/全部|
|---:|---|---:|---:|---:|---:|---:|
'''
for r in metrics:text+=f"|{r['window']}|{r['kind']}|{r['top1']:.4f}|{r['top3']:.4f}|{r['diagnosis_coverage']:.4f}|{r['refusal_ratio']:.4f}|{r['wrong_certain_rate_all_runs']:.4f}|\n"
text+='\n## 按完整测试运行配对Bootstrap\n\n|窗口|SCM减去基线|准确率差|95%区间|\n|---:|---|---:|---|\n'
for r in load('paired_bootstrap.json'):text+=f"|{r['window']}|{r['baseline']}|{r['mean_difference']:.4f}|{r['bootstrap95']}|\n"
text+='\n不能因60min的四类Top-1为100%就说结构因果创新有效：同窗口静态和VAR也达到100%，任务限定于已知故障时钟和三种单一已知机制。短窗更能暴露模型差异。\n\n## 相同配对样本上的主动/被动比较\n\n|方法|四类Top-1|确定覆盖|\n|---|---:|---:|\n'
for r in load('paired_passive_metrics.json'):text+=f"|被动{r['kind']}|{r['top1']:.4f}|{r['diagnosis_coverage']:.4f}|\n"
active=load('intervention_aligned/intervention_metrics.json');text+=f"|主动探针签名|{active['top1']:.4f}|{active['diagnosis_coverage']:.4f}|\n"
text+='''
这里每方法20个条件运行共享5个独立测试种子，主动额外使用两条分支，不能与D3的80条独立运行直接混算。主动探针未显示额外优势，校准样本不足也阻止确定结论。

## 实现、测试和复现

'''+(R/'test_report.txt').read_text(encoding='utf-8-sig')+f"\n审计保护文件数：{audit['protected_files']}；D2/D3保护哈希未变：{audit['protected_d2_d3_unchanged']}；144条新配对轨迹均有限、完成6000s且未停机，恢复双分支一致。\n"
text+='\n模型稳定性诊断：\n\n'+json.dumps(audit['model_diagnostics'],indent=2)+'\n'
text+='''
谱半径接近1；噪声跨节点相关约0.21，不是独立外生误差证明。完整参数稳定性数组保留，不以一张最优图替代失败和变异。

复现使用现有CPython3.12与NumPy2.4.6/SciPy1.15.3，根目录设置 `$env:PYTHONPATH=(Resolve-Path src).Path` 后依次执行：

```powershell
python experiments/d4_freeze.py
python experiments/d4_pair_simulation.py
python experiments/d4_models.py
python experiments/d4_discovery.py
python experiments/d4_interventions.py
python experiments/d4_paired_diagnosis.py
python -m pytest tests -q | Tee-Object -FilePath artifacts/d4/test_report.txt
python experiments/d4_audit.py
python experiments/d4_reports.py
```

一键脚本为 experiments/reproduce_d4.ps1 -Python <解释器路径>。python替换为安装了上述依赖的解释器。全量重跑先将artifacts/d4移动到明确的归档目录，保留所有旧结果；不得删除或覆盖D2/D3。冻结脚本、模型/配对入口会拒绝已有核心结果。D4_VARIABLE_MAPPING.md和D4_DYNAMIC_CAUSAL_GRAPH.md是已审核规范，不需要随每次运行重新改写。

结果文件：diagnosis_metrics/test_diagnoses/failure_cases、intervention_aligned下的指标与全部效应轨迹；D3基线只读保留，未重算覆盖。Granger是预测候选，PCMCI未运行，TEP结构Precision/Recall/F1为N/A；不伪造完整真值图。原始未对齐的分析仍保留为审计历史，正式比较只用对齐版本。

第四阶段到此停止。后续如要改善，需要独立新协议验证更长校准集、未知起始时刻、控制恢复瞬态、机制模型及跨实现保真，不预先承诺优化有效。
'''
(D/'D4_EXPERIMENT_RESULTS.md').write_text(text,encoding='utf-8')
write_json(R/'execution_sources.json',{str(p):digest(p) for p in [*Path('src/causalverse/causal').glob('*.py'),*Path('experiments').glob('d4_*.py')]})
print('D4 reports written')
