import json
from pathlib import Path
import numpy as np
from causalverse.data.manifest import write_json,digest
R=Path('artifacts/d5_1_1');D=Path('docs/research')
def read(n):return json.loads((R/n).read_text(encoding='utf-8'))
plan=read('protocol.json');metrics=read('metrics.json');log=read('data_log.json');support=read('support_results.json');gates=[];boot=[]
# Supplemental derived metrics preserve the original completed analysis file.
for kind in ('action','delta','PI','PI_stable'):
    d=np.load(R/f'predictions_{kind}_test.npz');err=np.abs(d['predicted']-d['truth']).reshape(20,4,3,6,3)
    for m in metrics:
        if m['kind']==kind:m['MAE_by_horizon']=err[:,(0,4,11,14).index(m['mechanism']),(0,1,5).index(m['delta'])].mean(0).tolist()
write_json(R/'metrics_by_horizon.json',metrics)
rng=np.random.default_rng(917)
for kind in ('action','delta','PI','PI_stable'):
    joint=np.load(R/f'joint_{kind}.npz')['covered'];ci=np.quantile([rng.choice(joint,20).mean() for _ in range(500)],[.025,.975])
    truth=np.load(R/f'predictions_{kind}_test.npz')['truth'].reshape(20,4,3,6,3)
    pred=np.load(R/f'predictions_{kind}_test.npz')['predicted'].reshape(20,4,3,6,3)
    baseline=np.load(R/'predictions_PI_test.npz')['predicted'].reshape(20,4,3,6,3)
    diff=(np.abs(pred-truth)-np.abs(baseline-truth)).mean(axis=(1,2,3))
    boot.append(dict(kind=kind,joint_coverage=float(joint.mean()),coverage95=ci.tolist(),MAE_difference_vs_PI=diff.mean(0).tolist(),
       paired_seed_bootstrap95=np.quantile([diff[rng.integers(0,20,20)].mean(0) for _ in range(500)],[.025,.975],axis=0).tolist()))
    for delta in (0,1,5):
        m=[r for r in metrics if r['kind']==kind and r['delta']==delta]
        mae=np.max([r['MAE_by_horizon'] for r in m],axis=(0,1));width=np.max([r['joint_width'] for r in m],axis=0)
        sup=[r['checks']['by_model'][kind]['supported'] for r in support if r['delta']==delta]
        reasons=[]
        if joint.mean()<.9:reasons.append('joint_test_coverage_below_90_percent')
        if np.any(mae>np.array(plan['mae_limits'])):reasons.append('per_horizon_MAE_exceeds_tolerance')
        if np.any(width>np.array(plan['width_limits'])):reasons.append('joint_interval_too_wide')
        if not all(sup):reasons.append('support_or_disagreement_or_stability_failure')
        gates.append(dict(kind=kind,delta=delta,research_eligible=not reasons,reasons=reasons,optimization_allowed=False,maximum_MAE=mae.tolist(),width=width.tolist(),support_rate=float(np.mean(sup))))
write_json(R/'gates.json',gates);write_json(R/'bootstrap.json',boot)
# Audit full data and history, not merely a successful subset.
for r in log['runs']:
    m=json.loads((Path(r['folder'])/'manifest.json').read_text())
    assert all(digest(Path(r['folder'])/p)==v for p,v in m['sha256'].items())
    assert not r['termination'] and r['records']==6121 and r['rng_paired']
protected=read('protected.json');assert all(digest(p)==h for p,h in protected.items())
write_json(R/'audit.json',dict(trajectories=720,independent_seeds=60,all_paired=True,all_full_horizon=True,historical_files=len(protected),history_unchanged=True))
text='''# D5.1.1 干预条件预测模型

本阶段仅建模与校准，不开发优化推荐，不授权动作。所有训练、校准、测试采用全新种子，pilot seed610999不参与正式数据。正式每个split20种子，四种机制共享同一故障前历史，每种机制三个动作共享5400s快照，共720条分支；独立统计单位是60个种子，不是720条独立实验。

原动作定义保持：不干预，或XMV10相对当前命令增加1/5个百分点，绝对命令覆盖120s；0–100%边界严格检查，不扩大幅度、不冻结其它PI，结束后恢复原PI更新。观察至6120s，即恢复600s。原始每秒日志和manifest保存，故障3600s，动作5400s，所有动作及恢复过程可复核。

Action-conditioned模型：以六个10s间隔七节点历史的末值、均值、尺度、变化和控制变化，加当前已发生命令及动作增量/持续时间为输入，固定六个预测时域各有直接线性岭回归输出头；动作相位/退出状态由时域相对120s决定。开始时刻固定5400s，不声称泛化任意时刻或持续时间。最新历史测量为5390s，当前命令来自5399s，作为独立合法特征，不使用未来控制或内部阀位。

Paired Delta模型：训练标签为同历史动作减不动作的真实变化量；推理时基线由只用历史的模型预测，不读取测试分支真实未来基线。+0分支变化强制为0。两路线均固定ridge10、20个按完整种子Bootstrap成员，各成员包含该种子的全部机制/动作；无测试选择模型，不删除成员。直接有限时域预测器无递推伴随矩阵，谱半径不适用，这不等于无限时域稳定证明。

原PI集成80个成员保持不变。额外PI_stable是独立充分范数约束投影对照：将每输出全部滞后绝对系数和投影到<=0.995，保留原模型，非最优约束估计。谱半径降低必须同时比较误差，不能因小于1自动接受。原PI基线先由5390s历史估计5400s，再在5400s施加已知命令，保证5410s等目标时刻一致。

IDV14的粘滞、闭环、10s与3s相位不同步、线性结构不足均是可能因素；本次单一投影对照不能分离各因素的因果贡献。实际接受目标和阀位仅离线记录，不进入预测。+1相对当前命令也可能突破2百分点死区，不能当成永远失效。

完整历史支持域检查六步全部七节点、控制历史、当前命令饱和、动作幅度/120s持续时间、验证时域、实际Bootstrap分歧与递推谱半径。直接模型仅承诺固定有限输出时域；原PI与投影基线分别使用原/投影最大谱半径。人工早期历史尖峰、未见动作/持续时间/时域作为显式域外测试，不宣称验证了任意真实OOD识别。

代码src/causalverse/decision/intervention_model.py、intervention_calibration.py、action_support.py；保留原uncertainty.py不改。模型参数、支持域、原PI稳定投影保存在artifacts/d5_1_1。
'''
(D/'D5_1_1_INTERVENTION_MODEL.md').write_text(text,encoding='utf-8')
(D/'D5_1_1_CALIBRATION.md').write_text('''# D5.1.1 独立干预校准

严格区分训练20、校准20、测试20个新种子。校准集不做模型选择，ridge、特征、成员数、误差/宽度容差在测试前固定。目标90%不降低，不沿用PI半径。

误差按固定尺度[0.25°C,0.5°C,5kPa]归一化。联合分数对同一种子的4机制×3动作×6时域×3目标取最大绝对误差；20个校准种子的ceil(21*.9)=19阶分数为半径。动作条件对照只在固定动作内取最大，再各校准半径。联合区间允许在三个候选间选择而不额外丢失这组固定实验潜在结果的联合覆盖；单独动作校准不能直接提供选择后同等保证。

只研究一个固定预测起点5400s，不泛化未知故障开始时刻、任意在线时刻或连续全轨迹。对种子级完整潜在结果向量可交换的假设才有有限样本解释；20个测试种子仍存在较大不确定性，报告种子Bootstrap95%区间。参数Bootstrap成员及同种子分支不能当额外独立校准样本。

每模型新的半径在独立校准集计算；全部原PI及投影模型也用同一新干预校准以公平比较，未使用D5.1的旧半径。原始预测文件同时保存真值和预测，半径独立JSON可完整还原区间。联合半径若过宽即失败，不能用高覆盖掩盖低效用。

测试前研究容差沿用T9/C21/P7 MAE[.25,.5,5]、宽度[1,2,20]；逐时域最坏机制MAE及宽度都检查，研究适用还要求联合覆盖>=.9和支持/分歧/稳定检查通过。本阶段所有optimization_allowed固定false，即使研究门槛通过也不自动进入优化。
''',encoding='utf-8')
text='# D5.1.1 独立验证结果\n\n正式数据全部720条完成、RNG配对、无提前停机；历史文件哈希保持不变。新种子每类20训练/20校准/20测试，同一split跨机制共享20个种子。全部失败样本保留。\n\n|方法|全机制/动作/时域/目标联合覆盖|种子Bootstrap95%|相对PI平均MAE差(T9,C21,P7)|\n|---|---:|---|---|\n'
for b in boot:text+=f"|{b['kind']}|{b['joint_coverage']:.3f}|{b['coverage95']}|{b['MAE_difference_vs_PI']}|\n"
text+='\n## 分机制及动作\n\n|方法|机制|增量|MAE(T9,C21,P7)|联合校准宽度|该动作整运行覆盖|单独动作校准覆盖|\n|---|---:|---:|---|---|---:|---:|\n'
for m in metrics:text+=f"|{m['kind']}|{m['mechanism']}|{m['delta']}|{[round(x,4) for x in m['MAE']]}|{[round(x,4) for x in m['joint_width']]}|{m['run_action_coverage']:.3f}|{m['actionwise_coverage']:.3f}|\n"
text+='\n## 每动作研究门槛（不是优化授权）\n\n'
for g in gates:text+=f"- {g['kind']} +{g['delta']}：研究门槛{g['research_eligible']}，原因{g['reasons']}；支持率{g['support_rate']:.3f}，优化授权false。\n"
text+='''
完整逐时域MAE在metrics_by_horizon.json，分量覆盖在metrics.json；所有漏覆盖案例在failures.json，逐种子预测文件全部保留。相比原PI误差的差值及配对种子Bootstrap区间见bootstrap.json，负值表示更低误差；不能仅按联合覆盖提高就宣称更准确。

稳定投影原始/新谱半径逐成员在stability_projection.json；降低谱半径不证明误差改善。对IDV14所有机制均保留，不能按真实IDV选择在线模型。人工OOD识别详见support_results.json；只能证明对已设计的域外扰动的识别，不是所有未知分布的保证。

是否解决PI迁移：已经建立新的干预数据与独立联合校准，但是否达到可用宽度、误差和支持标准应以gates.json逐动作判定，不等于自动推荐获准。本阶段未建立CVaR优化器，未进入D5.2/5.3。即便某动作可进入后续研究，也必须另经用户验收，不把+1结论推广+5。

复现：Windows CPython3.12/NumPy2.4.6，根目录设置PYTHONPATH=src，先将artifacts/d5_1_1归档以保留旧结果，再依次执行 experiments/d511_data.py --pilot、--freeze、无参数生成数据，接着d511_analysis.py、pytest tests、d511_reports.py。使用现有.research/venv-tep/Scripts/python.exe即可。数据生成遇到已有路径会拒绝，禁止覆盖D2至D5.1。
'''
(D/'D5_1_1_VALIDATION_RESULTS.md').write_text(text,encoding='utf-8')
print('Reports and full audit complete')
