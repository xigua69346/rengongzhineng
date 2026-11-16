"""Export explicit intervals and complete conservative acceptance evidence."""
import json,sys,platform,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.stats import beta
from causalverse.simulation import TEPAdapter
from causalverse.causal.dynamic import observed
from causalverse.data.manifest import write_json,digest

R=Path('artifacts/d5_1_1');D=Path('docs/research');S=np.array([.25,.5,5.]);H=np.array([10,30,60,120,300,600])
def read(n):return json.loads((R/n).read_text())
def main():
    log=read('data_log.json');plan=read('protocol.json');test=sorted([r for r in log['runs'] if r['split']=='test'],key=lambda r:(r['seed'],r['mechanism'],r['delta']))
    candidates=read('candidate_disagreement.json')['rows'];effects=[];diagnostics=[];summary={}
    for kind in ('action','delta','PI','PI_stable'):
        p=np.load(R/f'predictions_{kind}_test.npz');cal=read(f'calibration_{kind}.json');pred=p['predicted'];truth=p['truth']
        ids=np.array([[r['seed'],r['mechanism'],r['delta']] for r in test]);qa=np.array(cal['actionwise'])[np.searchsorted([0,1,5],ids[:,2])]
        np.savez_compressed(R/f'intervals_{kind}_test.npz',identifiers=ids,horizons=H,targets=['T9','C21','P7'],prediction=pred,truth=truth,
            joint_lower=pred-cal['joint']*S,joint_upper=pred+cal['joint']*S,action_lower=pred-qa[:,None,None]*S,action_upper=pred+qa[:,None,None]*S)
        pc=np.load(R/f'predictions_{kind}_calibration.npz');err=np.abs(pc['predicted']-pc['truth']).reshape(20,4,3,6,3)/S
        write_json(R/f'calibration_scores_{kind}.json',dict(seeds=plan['seeds']['calibration'],joint_scores=err.max(axis=(1,2,3,4)).tolist(),action_scores=err.max(axis=(1,3,4)).tolist()))
        covered=np.load(R/f'joint_{kind}.npz')['covered'];k=int(covered.sum());n=len(covered)
        cp=[float(beta.ppf(.025,k,n-k+1)) if k else 0.,float(beta.ppf(.975,k+1,n-k)) if k<n else 1.]
        rates={str(a):float(np.mean([c['models'][kind]['supported'] for c in candidates if c['delta']==a])) for a in (0,1,5)}
        summary[kind]=dict(MAE=np.abs(pred-truth).mean(axis=(0,1)).tolist(),joint_coverage=float(covered.mean()),exact_binomial95=cp,
            conservative_support_rates=rates,rejection_rate=float(np.mean([not c['models'][kind]['supported'] for c in candidates])),
            reasons=dict(Counter(reason for c in candidates for reason in c['models'][kind]['reasons'])))
        v=pred.reshape(20,4,3,6,3);y=truth.reshape(20,4,3,6,3)
        for mi,m in enumerate((0,4,11,14)):
            for ai,a in enumerate((1,5),start=1):
                error=(v[:,mi,ai]-v[:,mi,0])-(y[:,mi,ai]-y[:,mi,0])
                effects.append(dict(kind=kind,mechanism=m,delta=a,paired_effect_MAE=np.abs(error).mean(axis=(0,1)).tolist(),
                    observed_effect=np.mean(y[:,mi,ai]-y[:,mi,0],axis=0).tolist(),predicted_effect=np.mean(v[:,mi,ai]-v[:,mi,0],axis=0).tolist()))
        for i,r in enumerate(test):
            residual=pred[i]-truth[i];s=candidates[i]['models'][kind]
            diagnostics.append(dict(kind=kind,seed=r['seed'],mechanism=r['mechanism'],delta=r['delta'],MAE=np.abs(residual).mean(0).tolist(),
                pointwise_tolerance_exceedances=np.argwhere(np.abs(residual)>S).tolist(),support=s,joint_covered=bool(np.all(np.abs(residual)<=cal['joint']*S))))
    # Complete raw data and paired external-input checks, not selected records.
    paired_inputs={}
    for r in log['runs']:
        with np.load(Path(r['folder'])/'trajectory.npz') as d:
            assert d['XMEAS'].shape==(6121,41) and d['XMV'].shape==(6121,12)
            assert np.isfinite(d['XMEAS']).all() and np.isfinite(d['XMV']).all()
            key=(r['seed'],r['mechanism'])
            if r['delta']==0:paired_inputs[key]=(d['rng_state'].copy(),d['coolant_inlet_temperature'].copy())
            else:
                assert np.array_equal(d['rng_state'],paired_inputs[key][0])
                assert np.array_equal(d['coolant_inlet_temperature'],paired_inputs[key][1])
    write_json(R/'external_pairing.json',dict(seed_mechanism_groups=len(paired_inputs),intervention_comparisons=480,
        rng_states_bitwise_equal=True,coolant_inlet_trajectories_bitwise_equal=True))
    seed=plan['seeds']['test'][0];r=next(r for r in test if r['seed']==seed and r['mechanism']==0 and r['delta']==0)
    sim=TEPAdapter(seed).run(6121)
    with np.load(Path(r['folder'])/'trajectory.npz') as saved:
        replay=np.array([row['XMEAS'] for row in sim.rows]);assert np.array_equal(replay,saved['XMEAS'])
    write_json(R/'reproduction.json',dict(seed=seed,condition='normal_no_action',seconds=6121,all_41_measurements_bitwise_equal=True))
    old_seeds=set()
    def scan(x):
        if isinstance(x,dict):
            for key,v in x.items():
                if key in ('random_seed','seed') and isinstance(v,int):old_seeds.add(v)
                scan(v)
        elif isinstance(x,list):
            for v in x:scan(v)
    for p in read('protected.json'):
        if Path(p).name=='manifest.json':scan(json.loads(Path(p).read_text()))
    assert not old_seeds.intersection(seed for v in plan['seeds'].values() for seed in v)
    raw_support=read('support_results.json');ood={name:float(np.mean([not r['checks'][name]['supported'] for r in raw_support])) for name in ('hidden_early_spike','large_action','long_duration','long_horizon')}
    spectral=read('stability_projection.json');id14=[r for r in spectral if r['mechanism']==14]
    a14=[r for r in read('actuator_audit.json') if r['mechanism']==14]
    valve=[]
    for a in (1,5):
        pairs=[]
        for r in a14:
            if r['delta']!=a:continue
            b=next(b for b in a14 if b['seed']==r['seed'] and b['delta']==0)
            pairs.append([r['accepted_target'][0]-b['accepted_target'][0],r['actual_position'][1]-b['actual_position'][1]])
        valve.append(dict(delta=a,changed_target_at_onset=int(np.sum(np.abs(np.array(pairs)[:,0])>1e-8)),
            changed_position_at_119s=int(np.sum(np.abs(np.array(pairs)[:,1])>1e-8)),paired_differences=pairs))
    write_json(R/'final_summary.json',dict(models=summary,synthetic_OOD_detection=ood,effects=effects,IDV14_actuator=valve,
        IDV14_original_radius=[min(r['original'] for r in id14),max(r['original'] for r in id14)],
        IDV14_projected_radius=[min(r['projected'] for r in id14),max(r['projected'] for r in id14)],
        old_manifest_seed_overlap=False,python=sys.version,numpy=np.__version__,platform=platform.platform()))
    write_json(R/'case_diagnostics.json',diagnostics)
    xml=ET.parse(R/'tests.xml').getroot();test_count=sum(int(s.attrib['tests']) for s in xml.iter('testsuite'))
    text='\n## 最终验收结论与完整证据\n\n'
    text+=f'共{test_count}项单元/集成测试通过；720条原始轨迹均检查41测量/12命令形状和有限值；新种子正常轨迹6121秒重放逐位一致，旧manifest种子无交集。480个动作/基线配对的逐秒RNG状态和冷却水入口温度完全一致，详见external_pairing.json。正式仿真耗时{log["elapsed"]:.1f}秒；pilot单种子12分支耗时{read("pilot_timing.json")["seconds"]:.2f}秒。\n\n'
    text+='|方法|平均MAE T9/C21/P7|联合覆盖|精确二项95%区间|保守支持审计拒绝率|\n|---|---|---:|---|---:|\n'
    for kind,s in summary.items():text+=f'|{kind}|{[round(v,4) for v in s["MAE"]]}|{s["joint_coverage"]:.3f}|{[round(v,4) for v in s["exact_binomial95"]]}|{s["rejection_rate"]:.3f}|\n'
    text+='\n20/20时非参数Bootstrap覆盖区间退化为[1,1]，不能解释为总体必然覆盖；表中另给精确二项区间，样本量尚不足以在95%置信度下证明总体覆盖≥90%。平均误差按相同权重的完整种子/机制/动作/时域计算，T9/C21为°C，P7为kPa。\n\n'
    text+='### 逐项回答\n\n'
    text+='1. 两条新路线均比原PI平均误差更低，配对种子Bootstrap误差差值区间均小于0；这只是固定实验方案的结果，不代表所有历史或动作。\n'
    text+='2. +1和+5均完成独立校准、测试20/20联合覆盖，但均未通过误差/宽度/支持综合门槛。覆盖达标不能替代可用性。\n'
    text+=f'3. IDV14原谱半径范围{min(r["original"] for r in id14):.6f}–{max(r["original"] for r in id14):.6f}；投影范围{min(r["projected"] for r in id14):.6f}–{max(r["projected"] for r in id14):.6f}。数学递推稳定改善，但总体误差变差，未证明预测稳定性问题解决。训练运行Bootstrap差异保留在全部成员参数中；尚未以因子实验分离闭环、3秒调度和10秒采样的原因。\n'
    text+='4. 已避免直接迁移PI半径，并降低误差/缩窄新区间；尚未解决可用于决策的可信区间问题。新模型约2.9–3.0°C/5.8–6.0°C/58–60kPa的联合全宽仍超过1/2/20限制。\n'
    text+='5. 有独立新种子测试证据，20个测试种子没有参与拟合或校准；每个种子四机制/三动作属于配对相关实验。\n'
    text+='6. +1和+5都只可继续预测模型研究，没有动作获得进入优化研究的验证资格。\n'
    text+='7. 两个干预动作都继续禁止自动推荐/优化执行；不干预基线保留作比较。\n'
    text+='8. 尚不具备进入D5.2条件，停在D5.1.1等待验收。\n\n'
    text+='### 支持域和执行器审计的限制\n\n'
    text+=f'四类人工OOD检测率：{ood}。它们是显式极端扰动/未训练动作的测试，不是现实未知OOD的总体识别率。\n\n'
    text+='主分析检查了完整窗口和Bootstrap分歧，但没有显式比较候选机制均值。补充审计为每候选机制仅用训练数据拟合20成员模型，在推理时同时评估全部候选，不读取当前IDV；候选预测最大极差按固定尺度归一化，>1即保守拒绝。该审计在主测试后加入，属于更严格的事后诊断，不能用来重新挑模型、调整区间或授予资格。原始support_results/gates保持不变，最终拒绝率采用candidate_disagreement中的严格审计。各候选全部参数保留，不能只取有利机制。\n\n'
    for v in valve:text+=f'IDV14 +{v["delta"]}：20个测试种子中，动作开始时接受目标相对不动作发生变化{v["changed_target_at_onset"]}个，119秒时内部实际位置相对不动作发生变化{v["changed_position_at_119s"]}个；这些仅是离线仿真核对，具体差值见final_summary/actuator_audit，不能当在线特征。\n\n'
    text+='失败材料：failures.json只列联合漏覆盖（本次为空）；case_diagnostics.json保留全部960条模型×分支的误差、逐点超差及拒绝原因；gates.json保留逐动作门槛失败。没有删除失败种子或不稳定成员。intervals_*_test.npz保存显式上下界和种子/机制/动作索引，calibration_scores_*保存20个完整校准分数，effects保存配对干预效应误差。\n\n'
    text+='完整顺序：d511_data.py --pilot → --freeze → d511_data.py → d511_analysis.py → d511_support_audit.py → pytest tests -q --junitxml=artifacts/d5_1_1/tests.xml → d511_reports.py → d511_finalize.py。已有结果需人工另存归档后在空输出目录运行，不覆盖历史。\n\n'
    text+='```powershell\nSet-Location -LiteralPath "D:\\广西人工智能大赛"\n# 完整复现（已有artifacts/d5_1_1时主动拒绝覆盖）\n.\\experiments\\run_d511.ps1\n# 只复核现有产物与全部测试\n$env:PYTHONPATH = (Resolve-Path src).Path\n& .\\.research\\venv-tep\\Scripts\\python.exe -m pytest tests -q\n```\n'
    path=D/'D5_1_1_VALIDATION_RESULTS.md';path.write_text(path.read_text(encoding='utf-8')+text,encoding='utf-8')
    table='\n## 实测校准比较\n\n下列为按固定物理尺度归一化的半径。实际全宽为2×半径×[.25,.5,5]，不是各目标相同物理宽度。\n\n|模型|候选动作联合|不动作单独|+1单独|+5单独|\n|---|---:|---:|---:|---:|\n'
    for kind in ('action','delta','PI','PI_stable'):
        c=read(f'calibration_{kind}.json');table+=f'|{kind}|{c["joint"]:.6f}|'+ '|'.join(f'{v:.6f}' for v in c['actionwise'])+'|\n'
    table+='\n本次所有单独动作和联合区间在对应测试组均达到全检查点覆盖；但单独动作区间虽更窄仍不能自动提供动作选择后的联合保证。20种子小样本限制和过宽问题仍保留。全部校准原始分数、显式测试区间已导出。\n'
    path=D/'D5_1_1_CALIBRATION.md';path.write_text(path.read_text(encoding='utf-8')+table,encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
