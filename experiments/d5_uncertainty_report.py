import json
from pathlib import Path
import numpy as np
from causalverse.decision.uncertainty import physical_coefficients
from causalverse.causal.dynamic import DynamicModel
from causalverse.data.manifest import write_json,digest

ROOT=Path('artifacts/d5/uncertainty')
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
protocol=read('protocol.json');metrics=read('metrics.json');gates=read('validation_gates.json');stress=read('d4_intervention_stress.json')
parameters=[]
for c in protocol['mechanisms']:
    p=np.load(ROOT/f'ensemble_m{c}.npz');physical=[];radii=[]
    for coef,mean,scale in zip(p['coef'],p['mean'],p['scale']):
        m=DynamicModel(6,.1,True);m.coef=coef;m.mean=mean;m.scale=scale;physical.append(physical_coefficients(m))
        A=np.zeros((42,42));A[:7]=coef[1:].T;A[7:,:-7]=np.eye(35);radii.append(float(np.max(np.abs(np.linalg.eigvals(A)))))
    a=np.array(physical);np.savez(ROOT/f'physical_parameter_summary_m{c}.npz',coef=a,mean=a.mean(0),std=a.std(0),spectral_radii=radii)
    parameters.append(dict(mechanism=c,members=len(a),spectral_radius_min=min(radii),spectral_radius_max=max(radii),unstable_members=sum(r>=1 for r in radii)))
write_json(ROOT/'parameter_summary.json',parameters)
old=read('protected_before.json');changed=[p for p,h in old.items() if digest(p)!=h]
write_json(ROOT/'protection_audit.json',dict(protected_files=len(old),changed_files=changed,unchanged=not changed));assert not changed
worst=[]
for seconds in protocol['horizons_seconds']:
    for name in ('T9','C21','P7'):
        rows=[r for r in metrics if r['horizon_seconds']==seconds and r['target']==name]
        worst.append(dict(horizon_seconds=seconds,target=name,min_test_coverage=min(r['run_simultaneous_coverage'] for r in rows),
                          max_test_width=max(r['mean_width'] for r in rows),max_test_mae=max(r['mean_absolute_error'] for r in rows)))
write_json(ROOT/'trust_summary.json',dict(state='有限可信：仅限部分原PI预测；不具备优化授权',optimization_allowed=False,
    reasons=['long_horizon_intervals_too_wide','IDV14_T9_300s_test_undercoverage','PI_calibration_does_not_transfer_to_interventions','insufficient_intervention_calibration_seeds'],worst_by_horizon=worst))
lines=['# D5.1 模型可信度与不确定性评估','',
 '本次只执行附件最后指定的D5.1，并未完成整个D5。已实现不确定性模块、实际区间校准和测试；没有开发候选生成器、风险损失、CVaR优化器或闭环推荐策略。模型总体为**有限可信（仅原PI预测）**；目前**不足以授权模型驱动干预优化**。','',
 '## 预先冻结的协议与数据独立性','',
 '正式执行前测得一次20运行拟合约0.029s，80成员拟合粗估2.33s；完整预测及校准另计。冻结文件为 artifacts/d5/uncertainty/protocol.json。每种机制20个完整训练运行、10个验证运行、20个测试运行，沿用D3划分，只读取D4已派生的7维可观测数据。未新建TEP轨迹、未覆盖D2/D3/D4。',
 '', '这些测试运行相对训练独立，但此前已用于D3/D4，属于分阶段回顾性研究，不是全新盲测。D5将来的闭环策略实验仍需另行冻结新种子；本次样本数量不能代替未来D5.5的闭环验收。',
 '', '## 三类不确定性','',
 '1. 参数：按完整训练运行有放回Bootstrap，每机制20个模型，共80个。每个成员重新拟合其训练尺度和方程参数；保存抽样运行索引。另将系数转换到共同物理单位坐标，避免直接比较不同标准化下的系数。所有成员均保留，包括谱半径超过1的成员，不按测试效果删模型。',
 '2. 过程：从训练残差按连续12个10s步（120s）抽样，七节点残差向量联合抽取，保留块内时序和节点相关。块不越过原始运行边界，块间相关被近似截断，不承诺保留任意长依赖。每个参数成员2条过程路径，每机制40条；它们是Monte Carlo样本，不是40个独立实验种子。',
 '3. 机制：正常/IDV4/11/14分别拟合，标签只用于离线训练分组。预测接口不接受真实IDV、仿真器RNG或实际阀位；对同一可观测历史评估全部4种模型，再取区间并集。均值为候选模型等权均值，不是校准的机制概率。IDV14的线性条件模型也不等于已精确建模死区与延迟。',
 '', '## 预测区间及校准单位','',
 '对固定时刻3600/5400/9000s的合法历史，递推10、30、60、120、300、600s，评估T9/C21/P7。条件模拟分位数5%–95%先形成区间，机制间取最小下界/最大上界。',
 '', '校准分数为每运行跨3个固定时刻的最大非覆盖距离，分变量、分预测时域计算。每类10个验证运行使用ceil((n+1)*0.9)阶统计量，再取4类校准半径最大值；在线无需真实机制。测试主指标是“一整条运行的3个时刻均覆盖”的比例，同时保存逐时刻边际覆盖，不能把60个时间点称为60个独立运行。',
 '', '有限样本覆盖解释仍要求同机制完整运行可交换，且本次只对固定3个时刻、单个变量/时域校准，没有给所有变量、所有预测时域、任意在线时刻的联合90%保证。Bootstrap覆盖区间也按20条完整测试运行重采样500次；20条中漏1条就是5个百分点，小样本区间仍较宽。',
 '', '## 可信度门槛','',
 '测试前规定：验证集最坏机制覆盖不低于90%；MAE上限T9=0.25°C、C21=0.5°C、P7=5kPa；平均区间宽度上限分别1°C、2°C、20kPa；每机制至少10条独立校准运行。它们是研究精度/可用性容差，**不是工程安全限值**。不能通过无限放宽区间获得可信状态。',
 '', '逐单元状态与拒绝理由已在validation_gates.json于测试预测前写入；之后不使用测试结果重新选择门槛。聚合状态允许“有限可信”，未通过的变量/时域不能被其它单元平均掩盖。所有单元的optimization_allowed均为false，因为原PI预测校准不验证命令干预后的分布。',
 '', '## 验证门槛的原始判定','', '|变量|时域s|验证最坏MAE|验证最坏平均宽度|冻结状态|','|---|---:|---:|---:|---|']
for g in gates:lines.append(f"|{g['target']}|{g['horizon_seconds']}|{g['validation_worst_mae']:.4f}|{g['validation_worst_mean_width']:.4f}|{g['state']}|")
lines+=['','## 独立测试结果（四种背景中的最差值）','','|变量|时域s|最低运行级覆盖|最大平均宽度|最大MAE|','|---|---:|---:|---:|---:|']
for r in worst:lines.append(f"|{r['target']}|{r['horizon_seconds']}|{r['min_test_coverage']:.3f}|{r['max_test_width']:.4f}|{r['max_test_mae']:.4f}|")
lines+=['','单位：T9/C21为°C，P7为kPa。全部按背景、变量、时域的指标及运行Bootstrap区间在metrics.json；误覆盖和超支持范围的全部案例在failure_cases.json。IDV14的300s釜温运行级覆盖为80%，尽管该单元验证时通过，说明冻结门槛也会失效，不能隐藏或用测试数据补校准。',
 '', '## 已有干预轨迹的域外压力测试','',
 '仅复用D4的5个测试种子、正常/三故障背景、+1/+5百分点已执行动作，共40个条件。采用同一PI校准区间，预测10/30/60/120/300s；这是分布迁移压力测试，不将其写为已校准的干预区间。3个D4验证种子不足以支持有限90%类条件校准，未据测试结果重新校准。',
 '', f"全部15个变量×时域观测均覆盖的条件仅 {sum(r['covered_all'] for r in stress)}/{len(stress)}；同种子下不同背景和动作不能当独立样本。分量边际覆盖见下表，仅用于揭示迁移失败，不是尾部风险概率。",'',
 '|动作|T9边际覆盖|C21边际覆盖|P7边际覆盖|','|---|---:|---:|---:|']
for delta in (1,5):
    a=np.array([r['covered'] for r in stress if r['delta']==delta]).mean(axis=(0,1))
    lines.append(f'|+{delta}百分点|{a[0]:.3f}|{a[1]:.3f}|{a[2]:.3f}|')
lines+=['', '干预模型缺少实际阀位/死区状态、精确控制时钟和未观测过程状态，因此即使PI预测覆盖良好，也可能严重低估动作响应。现阶段拒绝模型驱动推荐是合理结果，而不是让优化器绕过可信度门槛。没有执行任何新的控制覆盖，原PI运行方式不受影响。',
 '', '## 参数稳定性','', '|训练机制|成员数|谱半径最小|谱半径最大|不稳定成员数|','|---|---:|---:|---:|---:|']
for r in parameters:lines.append(f"|{r['mechanism']}|{r['members']}|{r['spectral_radius_min']:.6f}|{r['spectral_radius_max']:.6f}|{r['unstable_members']}|")
lines+=['', '短时有限预测不意味着所有参数成员长时稳定；谱半径/系数数组与参数方差、过程总方差、机制均值分歧均独立保存，不把总方差严格等于各部分之和。当前40条模拟路径的分位数近似也存在Monte Carlo误差。',
 '', '## 测试、保护与复现','', '```text', (ROOT/'test_report.txt').read_text(encoding='utf-8-sig').strip(),'```','',
 f"历史保护检查：{len(old)}个D2/D3/D4文件及既有接口源文件哈希逐项未变。未删除校准或预测失败样本。",'',
 '核心模块：[uncertainty.py](../../src/causalverse/decision/uncertainty.py)。结果目录artifacts/d5/uncertainty：ensemble_m*.npz保存完整成员及残差库；validation/test目录保存每运行真值、预测、原始区间、参数/总标准差和机制分歧；calibration.npz保存正式半径。实际区间=原始区间±半径。',
 '', '在Windows CPython3.12/NumPy2.4.6下，项目根目录执行（已有结果需归档到新目录，禁止覆盖旧证据）：', '', '```powershell',
 "$env:PYTHONPATH=(Resolve-Path src).Path", ".\\.research\\venv-tep\\Scripts\\python.exe experiments/d5_model_uncertainty.py --freeze", ".\\.research\\venv-tep\\Scripts\\python.exe experiments/d5_model_uncertainty.py", ".\\.research\\venv-tep\\Scripts\\python.exe -m pytest tests -q | Tee-Object -FilePath artifacts/d5/uncertainty/test_report.txt", ".\\.research\\venv-tep\\Scripts\\python.exe experiments/d5_uncertainty_report.py", '```',
 '', '试运行pilot.json仅为成本测量，不参与参数、校准或测试；全量脚本从冻结协议重现。D5.1使用现有数据的计算规模已满足20/10/20条件，但尚未执行D5.5要求的扩大闭环策略实验，也没有CVaR90稳定性结果。',
 '', '## 方法来源和创新边界','',
 '按运行Bootstrap、残差块重采样及conformal校准均是成熟思想，本次不将其称为原创。EnbPI研究了Bootstrap集成的时序区间：[Xu与Xie，ICML2021](https://proceedings.mlr.press/v139/xu21h.html)；SPCI研究序列依赖下的预测区间：[ICML2023](https://proceedings.mlr.press/v202/xu23r)。本实现不是这些算法的复刻，也不直接继承其理论保证；本次采用完整运行作为校准单位。未复制其代码或增加第三方软件依赖，继续使用既有NumPy与TEP许可记录。',
 '', '## D5执行状态','', 'D5.1已实现并运行；结论为PI预测有限可信、干预优化未获授权。D5.2候选/损失、D5.3风险优化、D5.4完整策略拒绝模块、D5.5新种子闭环比较、D5.6消融与完整创新性分析均未实施。本报告不宣称第五阶段整体验收完成，也不具备进入第六阶段完整沙盘的条件。']
Path('docs/research/D5_MODEL_UNCERTAINTY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
write_json(ROOT/'source_manifest.json',{str(p):digest(p) for p in [Path('src/causalverse/decision/uncertainty.py'),Path('experiments/d5_model_uncertainty.py'),Path('experiments/d5_uncertainty_report.py'),Path('tests/test_uncertainty.py')]})
print('D5.1 report and history protection audit complete')
