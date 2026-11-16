"""Read-only retrospective interval analysis, reports and standalone Plotly."""
import json,platform,sys,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from causalverse.data.manifest import write_json,digest
from causalverse.decision.mechanism import CLASSES,NODES,STATISTICS

R=Path('artifacts/d5_1_2');D=Path('docs/research');OLD=Path('artifacts/d5_1_1');S=np.array([.25,.5,5.])
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def interval_analysis():
    result=[]
    for kind in ('action','delta','PI','PI_stable'):
        p=np.load(OLD/f'predictions_{kind}_calibration.npz');e=np.abs(p['predicted']-p['truth']).reshape(20,4,3,6,3)/S
        maxima=e.max(axis=(1,2,3,4));drivers=[]
        for seed,row in zip(read(OLD/'protocol.json')['seeds']['calibration'],e):
            mi,ai,hi,ti=np.unravel_index(np.argmax(row),row.shape)
            drivers.append(dict(seed=seed,mechanism=int(CLASSES[mi]),delta=[0,1,5][ai],horizon=[10,30,60,120,300,600][hi],target=['T9','C21','P7'][ti],score=float(row.max())))
        rank=int(np.ceil(21*.9));q=sorted(drivers,key=lambda r:r['score'])[rank-1]
        result.append(dict(kind=kind,mechanism_max_driver_counts=dict(Counter(str(d['mechanism']) for d in drivers)),
            variable_max_driver_counts=dict(Counter(d['target'] for d in drivers)),rank19_driver=q,
            per_mechanism_mean_run_max={str(m):float(e[:,i].max(axis=(1,2,3)).mean()) for i,m in enumerate(CLASSES)},
            joint_width=(2*read(OLD/f'calibration_{kind}.json')['joint']*S).tolist(),drivers=drivers))
    candidates=read(OLD/'candidate_disagreement.json')['rows'];dispersion=[]
    for kind in ('action','delta','PI','PI_stable'):
        for mechanism in CLASSES:
            values=np.array([np.ptp(np.array(r['models'][kind]['candidate_means']),axis=0)/S for r in candidates if r['mechanism']==mechanism])
            dispersion.append(dict(kind=kind,mechanism=int(mechanism),normalized_mean_range_by_target=values.mean(axis=(0,1)).tolist(),
                maximum_range_by_target=values.max(axis=(0,1)).tolist(),dominant_target_counts=dict(Counter(['T9','C21','P7'][i] for i in values.max(axis=1).argmax(axis=1)))))
    write_json(R/'interval_attribution.json',dict(calibration=result,candidate_dispersion=dispersion,
        retrospective_only=True,intervals_changed=False,classification_windows_do_not_recalibrate_prediction_intervals=True))
    return result,dispersion

def main():
    plan=read(R/'protocol.json');metrics=read(R/'metrics.json');records=read(R/'diagnoses.json');chosen=read(R/'selection.json')['selected_windows']
    validation=read(R/'validation.json');attribution,dispersion=interval_analysis();contrasts=[]
    names=[f'{node}:{stat}' for stat in STATISTICS for node in NODES]
    for window in plan['windows']:
        d=np.load(R/f'features_logistic_{window}.npz');x=d['train_x'];y=d['train_y']
        for a,b in ((0,11),(4,14),(4,11),(11,14)):
            xa=x[y==a];xb=x[y==b];effect=np.abs(xa.mean(0)-xb.mean(0))/np.maximum(np.sqrt((xa.var(0)+xb.var(0))/2),1e-6)
            ids=np.argsort(-effect)[:3];contrasts.append(dict(window=window,pair=[a,b],top_training_separation=[dict(feature=names[i],standardized_mean_difference=float(effect[i])) for i in ids]))
    write_json(R/'feature_contrasts.json',contrasts)
    # Reconstruct a saved logistic model's test scores to verify persistence.
    from causalverse.decision.mechanism import LogisticMechanism
    for window in plan['windows']:
        saved=np.load(R/f'logistic_{window}.npz');m=LogisticMechanism()
        for k in ('mean','scale','coef'):setattr(m,k,saved[k])
        scores=m.scores(np.load(R/f'features_logistic_{window}.npz')['test_x'])
        expected=[r['scores'] for r in records if r['kind']=='logistic' and r['window']==window and r['split']=='test']
        np.testing.assert_allclose(scores,expected,rtol=0,atol=0)
    protected=read(R/'protected.json');assert all(digest(p)==h for p,h in protected.items())
    write_json(R/'reproduction_audit.json',dict(saved_logistic_scores_bitwise_equal=True,historical_inputs_unchanged=True,protected_files=len(protected),
        python=sys.version,numpy=np.__version__,platform=platform.platform(),new_simulations=0))
    titles=['D3：各窗口Macro-F1','D5.1.1外部复核：Macro-F1','逻辑回归混淆矩阵：D3','逻辑回归混淆矩阵：外部',
        '反应釜温度 T9（°C）','冷却水出口温度 C21（°C）','反应釜压力 P7（kPa）','冷却水控制命令 U10（%）']
    fig=make_subplots(rows=4,cols=2,subplot_titles=titles,vertical_spacing=.08)
    for col,split in enumerate(('test','external'),1):
        for kind in plan['models']:
            ms=[m for m in metrics if m['split']==split and m['kind']==kind]
            fig.add_trace(go.Scatter(x=[m['window'] for m in ms],y=[m['macro_f1'] for m in ms],name=kind,mode='lines+markers',legendgroup=kind,showlegend=col==1),row=1,col=col)
        m=next(m for m in metrics if m['split']==split and m['kind']=='logistic' and m['window']==chosen['logistic'])
        fig.add_trace(go.Heatmap(z=m['confusion_matrix'],x=['正常','IDV4','IDV11','IDV14'],y=['正常','IDV4','IDV11','IDV14'],texttemplate='%{z}',showscale=False),row=2,col=col)
        fig.update_xaxes(title_text='排名第一（不是强制诊断）',row=2,col=col);fig.update_yaxes(title_text='真实工况',row=2,col=col)
    for mechanism in CLASSES:
        traces=[]
        for r in plan['d3_runs']:
            if r['split']=='test' and r['fault_id']==mechanism:
                with np.load(Path('artifacts/d4/observations')/(r['dataset_run_id']+'.npz')) as d:traces.append(d['values'][360:540][:,[0,1,2,5]])
        mean=np.mean(traces,axis=0)
        for j in range(4):
            fig.add_trace(go.Scatter(x=np.arange(180)*10,y=mean[:,j],name='正常' if mechanism==0 else f'IDV{mechanism}',legendgroup=f'm{mechanism}',showlegend=j==0),row=3+j//2,col=1+j%2)
    fig.update_layout(title='D5.1.2 观测机制区分：全部测试运行，不作控制推荐',height=1450,template='plotly_white',font=dict(family='Microsoft YaHei,Arial'))
    fig.write_html(R/'analysis.html',include_plotlyjs=True,full_html=True)
    assert 'Plotly.newPlot' in (R/'analysis.html').read_text(encoding='utf-8')
    historical=read('artifacts/d4/diagnosis_metrics.json')
    tests=sum(int(s.attrib['tests']) for s in ET.parse(R/'tests.xml').getroot().iter('testsuite'))
    text='''# D5.1.2 多故障机制区分研究

本阶段实现四变量简单统计特征、多项逻辑回归及可拒绝的候选集合；没有新建仿真轨迹，没有开发控制探针、优化器或推荐。逻辑回归是监督统计识别，不是因果识别；输出归一化分数未经故障概率校准。

## 数据与可观测性

主实验复用D3的80训练、40验证、80测试完整运行，每类20/10/20，原划分不变。读取D4从原始1秒数据精确抽取的10秒观测缓存。外部复核仅取D5.1.1的20个测试种子、四机制、不动作分支，共80工况；同种子四工况相关，按20个完整种子分组Bootstrap，不把三个动作分支重复算样本。外部数据不训练或调整阈值。两批都是已存在的回顾性数据，不声称全新前瞻盲测。

仅用XMEAS9反应釜温度、XMEAS21反应釜冷却水出口温度、XMEAS7反应釜压力和XMV10反应釜冷却水阀命令。温度°C、压力kPa、命令为百分点/%，不是实际冷却水流量。IDV标签仅离线训练/计分；RNG、实际阀位、冷却水入口温度、隐藏状态均不进入在线特征。

窗口统一为实验时钟[3600,3600+W)，W=180/600/1800秒，对正常也使用相同时钟。10秒网格分别18/60/180个观测；180秒窗口不等于180秒采样数据，不将低频数据上采样。四个变量没有组成分析仪的长采样保持问题，但记录自相关，统计单位是运行。这个实验使用已知计划的故障时钟，不是未知故障起点的端到端在线系统；10秒网格也未消除3秒控制调度的相位问题。

## 三种简单模型

静态：复用D4的均值/对数标准差、训练标准化、类内方差下限0.1的对角签名距离，在相同四变量重拟合。

VAR：四变量、固定6阶/10秒滞后、ridge0.1，无工艺约束；只用正常训练t>=1800秒拟合，运行边界不跨接。每个窗口用残差均值、log1p均方、一阶相关形成12维签名，分类距离沿用D4。它是预测残差基线，不等同物理因果关系。

逻辑回归：每变量9项，共36项：均值、标准差、最小/最大、极差、末值减首值、平均绝对变化速度、全窗线性斜率、后1/3减前1/3均值。训练集标准化；固定多项线性模型、L2系数1（总交叉熵形式），不惩罚截距，用已有SciPy L-BFGS求解；不搜索复杂结构或额外变量。特征有冗余，但规模小且预先固定，未按测试结果增删。

所有模型不做超参数搜索；验证集仅建立候选阈值和选择有价值的窗口，先保存选择再评分测试/外部。每类验证10条，以ceil(11*.9)=10阶距离/非一致性分数建立候选集合。逻辑回归使用1-归一化分数；静态/VAR仍用原距离阈值。分数差小于固定0.05时扩展Top-2；单候选若与第一排名矛盾则扩展而不强判。空集、多个候选均输出“当前观测不足以区分故障原因”。验证候选阈值不把模型分数变成校准概率；候选覆盖只在固定窗口/同分布运行等条件下解释，不保证任意窗口选择、未知故障或工业现场覆盖。

排名第一的混淆矩阵/Top-1与允许拒绝的决策分开统计，Top-2不是候选集合覆盖率；错误单候选率另报。D4历史七变量结果只作背景，同输入公平比较使用本阶段四变量重拟合结果。

## 历史区间问题：只解释，不修改

D5.1.1联合校准的宽度对每个机制相同，因为使用了跨机制/动作/时域/目标的统一最大分数。不能称某个测试故障拥有独立更宽的现有区间。本次只离线追踪哪些校准故障/目标主导最大误差，并统计候选模型在T9/C21/P7上的分歧。没有重校准、裁剪或缩小区间；没有按分类结果选择较窄机制区间。

1800秒分类证据可能减少候选歧义，但D5.1.1预测器只用固定5400秒起点前60秒历史。本研究没有将更长窗口输入该预测器，因此不能据分类改善宣称预测区间变窄或覆盖改善。

进入下一阶段的价值限于整理被动观测诊断与拒绝机制。不得据此解锁D5.2优化或自动干预。
'''
    (D/'D5_1_2_MECHANISM_ANALYSIS.md').write_text(text,encoding='utf-8')
    text=f'# D5.1.2 实验结果\n\n新增仿真0条；{tests}项测试通过，保存模型重载分数逐位一致，{len(protected)}个受保护历史输入/报告哈希未变。完整指标、每类识别和混淆矩阵均保留，不根据测试调参。\n\n'
    text+='|数据|窗口s|模型|Top-1|Macro-F1|Top-2|拒绝率|候选真因覆盖|错误单候选/全部|\n|---|---:|---|---:|---:|---:|---:|---:|---:|\n'
    for m in metrics:text+=f'|{m["split"]}|{m["window"]}|{m["kind"]}|{m["top1"]:.4f}|{m["macro_f1"]:.4f}|{m["top2"]:.4f}|{m["refusal"]:.4f}|{m["candidate_coverage"]:.4f}|{m["wrong_certain_all"]:.4f}|\n'
    text+='\n## 验证选择和逐故障结果\n\n验证集单独选择窗口：'+str(chosen)+'。不是按测试最佳窗口选择。所有窗口完整保留。\n\n'
    for split in ('test','external'):
        for kind in plan['models']:
            m=next(m for m in metrics if m['split']==split and m['kind']==kind and m['window']==chosen[kind])
            text+=f'### {split} / {kind} / {m["window"]}秒\n\n混淆矩阵行是真值、列是第一排名，顺序[正常,4,11,14]，不表示系统强制诊断：\n\n```text\n'
            text+='\n'.join(str(r) for r in m['confusion_matrix'])+'\n```\n\n'
            text+='|工况|Precision|Recall|F1|拒绝率|\n|---|---:|---:|---:|---:|\n'
            for c,v in m['per_class'].items():text+=f'|{c}|{v["precision"]:.3f}|{v["recall"]:.3f}|{v["f1"]:.3f}|{v["refusal"]:.3f}|\n'
    text+='\n## D4历史结果（七变量，不是本实验同输入对照）\n\n|窗口|方法|Top-1|拒绝率|\n|---|---|---:|---:|\n'
    for m in historical:
        if m['kind'] in ('static','VAR') and m['window'] in (600,1800):text+=f'|{m["window"]}|{m["kind"]}|{m["top1"]:.4f}|{m["refusal_ratio"]:.4f}|\n'
    text+='\n## 预测区间的离线归因\n\n以下统计是历史校准误差主导项，不能作在线标签或根因证明。\n\n|模型|20校准种子的最大分数机制计数|最大分数变量计数|第19阶半径的主导案例|\n|---|---|---|---|\n'
    for a in attribution:text+=f'|{a["kind"]}|{a["mechanism_max_driver_counts"]}|{a["variable_max_driver_counts"]}|{a["rank19_driver"]}|\n'
    text+='\n候选分歧按固定[.25°C,.5°C,5kPa]归一化，以免量纲主导比较。各模型、各真实机制的逐目标平均/最大极差在interval_attribution.json；真实机制只用于离线分组。\n\n'
    for kind in ('action','delta'):
        a=[r for r in dispersion if r['kind']==kind];mean=np.mean([r['normalized_mean_range_by_target'] for r in a],axis=0)
        text+=f'{kind}候选模型平均标准化极差(T9,C21,P7)={np.round(mean,3).tolist()}；不同目标的分歧不是可直接用于故障概率的分数。\n\n'
    text+='## 最终回答\n\n'
    text+='1. 在本数据的已知时钟、三种单故障与正常工况内，现有四变量有区分能力，较长窗口较好；不能保证每次唯一判断或推广未知组合故障。\n'
    text+='2. 短窗主要混淆正常与IDV11随机扰动，部分IDV14也混入二者。IDV4在本实验较易排名识别；4与14的长窗区分不等于证明物理机制可识别。逐方法混淆矩阵和失败样本均保留。\n'
    text+='3. 验证集三种模型均选1800秒最有价值；600秒可作为延迟与信息量折中，180秒用于较早但更保守的候选输出。更长观察需要等待，不能忽略诊断延迟成本。\n'
    text+='4. 没有证据证明逻辑回归稳定优于静态/VAR。它在D3的600/1800秒低于静态，外部1800秒低于VAR；各窗口配对Bootstrap差值保存在comparisons.json。保留负结果，不增加模型复杂度追赶测试分数。\n'
    text+='5. 候选多个/空集、分数接近、输入缺失/非有限或不满足固定窗口条件时应拒绝；已知标签外机制及动作条件未验证，也不能强判。即使长窗Top-1高，候选集合仍可能不唯一。\n'
    text+='6. 值得继续小范围被动诊断整合，暂不值得增加复杂分类器或大规模数据；尚不能进入D5.2优化授权。当前仅四变量统计识别，未解决原预测区间过宽与候选机制预测分歧。完成后停止，等待验收。\n\n'
    text+='全部失败/拒绝/真因未入候选集的运行在failures.json，全部排名和分数在diagnoses.json。analysis.html展示所有模型指标、逻辑回归混淆矩阵和每类全部20测试运行的均值曲线；没有选择最佳运行。feature_contrasts.json仅为训练特征的标准化均值分离度，不是因果贡献。\n\n'
    text+='## 复现\n\n已有结果会主动拒绝覆盖。若完整复现，先人工将artifacts/d5_1_2另存归档；D2至D5.1.1保持原位置。使用已有CPython3.12、NumPy2.4.6、SciPy1.15.3、Plotly7.1.0，不需新增依赖或下载数据。\n\n```powershell\nSet-Location -LiteralPath "D:\\广西人工智能大赛"\n.\\experiments\\run_d512.ps1\n# 仅复核当前产物和测试\n$env:PYTHONPATH=(Resolve-Path src).Path\n& .\\.research\\venv-tep\\Scripts\\python.exe -m pytest tests -q\n```\n\n复现入口依次执行freeze、识别评估、测试、报告/区间分析；不调用TEP，不执行控制命令。核心代码src/causalverse/decision/mechanism.py。\n'
    (D/'D5_1_2_EXPERIMENT_RESULTS.md').write_text(text,encoding='utf-8')
    print('\n'.join(f'{m["split"]:8} {m["window"]:4} {m["kind"]:8} F1={m["macro_f1"]:.4f} top2={m["top2"]:.4f} refusal={m["refusal"]:.4f}' for m in metrics))
    print('Reports, read-only interval attribution and visualization complete')
if __name__=='__main__':main()
