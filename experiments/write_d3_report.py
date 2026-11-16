import json
from pathlib import Path
from causalverse.data.manifest import digest,write_json

base=Path('artifacts/d3');root=base/'dataset';det=base/'detection'
metrics=json.loads((det/'metrics.json').read_text());top=json.loads((det/'contributions.json').read_text())
gen=json.loads((root/'generation_log.json').read_text());audit=json.loads((root/'integrity_audit.json').read_text());replay=json.loads((root/'reproduction_audit.json').read_text())
qa=json.loads((det/'browser-qa.json').read_text())
test=(base/'test-report.txt').read_text(encoding='utf-8-sig')
lines=['# D3 实际实验结果与阶段验收','',
 '所有数值来自本次实际仿真与冻结协议。异常检测贡献度不代表因果关系。本阶段到此停止，未开发动态因果模型或稳健优化。','',
 '## 完整运行与复现记录','',
 f"正式生成 {len(gen['runs'])} 条运行，耗时 {gen['elapsed_seconds']:.1f}s；全部原始数据保留，每条14400个1s记录。四类各训练20/验证10/测试20，共288万原始记录、14000个180s处理后样本。",'',
 f"完整性审计 {len(audit)} 条通过；四类代表性完整重放通过 {sum(r['all_raw_arrays_identical'] for r in replay)}/{len(replay)}（容差0，比较所有原始数组）。D2接口不变，回归测试包含在测试报告中。",'',
 '```text',test.strip(),'```','',
 f"离线HTML浏览器检查：{qa['runOptions']} 条运行可选，页面脚本错误 {len(qa['errors'])} 个，已切换至 {qa['selectedRun']} / {qa['selectedDetector']} 并保存截图。",'',
 '## 独立测试结果','',
 '每种故障行合并20条该故障运行与同一组20条正常运行；正常对照在不同故障行重复使用。纯正常行无正类，固定两类Macro-F1的空类记0，主要看其FPR。延迟只对检出运行计算，未检出不填0。','',
 '|故障|方法|Accuracy|Precision|Recall|Macro-F1|FPR|检出故障运行|平均延迟s|',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|']
for m in metrics:
    lines.append('|'+ '|'.join([str(m['fault_id']),m['detector'],*[f"{m[k]:.4f}" for k in ['Accuracy','Precision','Recall','Macro_F1','False_Positive_Rate']],str(m['detected_fault_runs']) if m['fault_id'] else '不适用',str(round(m['delay_mean_seconds'],1)) if m['delay_mean_seconds'] is not None else '未检出/不适用'])+'|')
lines+=['','## 进入第四阶段前的六个问题','']
for fid in (4,11,14):
    p=next(m for m in metrics if m['fault_id']==fid and m['detector']=='PCA')
    t=next(m for m in metrics if m['fault_id']==fid and m['detector']=='Threshold')
    lines += [f"- **IDV({fid})检测能力**：PCA召回{p['Recall']:.4f}，检出{p['detected_fault_runs']}/20条，传统阈值召回{t['Recall']:.4f}。必须同时看逐点漏报和检出运行数，偶发报警不等于稳定识别。",
              f"- **IDV({fid})种子影响**：PCA单条运行召回范围{p['recall_min']:.4f}–{p['recall_max']:.4f}，标准差{p['recall_std']:.4f}；检出运行延迟范围{p['delay_min_seconds']}–{p['delay_max_seconds']}s。",
              f"- **IDV({fid})异常贡献**："+'、'.join(v['variable'] for v in top[str(fid)][:5])+'。按所有故障后样本统计，不等于根因。',
              f"- **IDV({fid})方法比较**：PCA Macro-F1={p['Macro_F1']:.4f}，传统阈值={t['Macro_F1']:.4f}；同时比较FPR和漏报，不能仅凭聚合准确率判优。"]
per_run=json.loads((det/'per_run_metrics.json').read_text())
lines+=['','正常工况的跨种子误报情况：']
for name in ('Threshold','T2','SPE','PCA'):
    rows=[r for r in per_run if r['fault_id']==0 and r['detector']==name]
    worst=max(rows,key=lambda r:r['FP'])
    lines.append(f"- {name}：正常运行FPR范围{min(r['False_Positive_Rate'] for r in rows):.4f}–{max(r['False_Positive_Rate'] for r in rows):.4f}；最多误报的保留案例{worst['run_id']}（seed={worst['seed']}，FP={worst['FP']}）。")
lines += ['','误报不能解释为“某个故障的正类误报”：FPR计算于正常运行和故障前片段。error_cases.csv保留全部FP/FN，per_run_metrics.json保留故障前报警数；本次未通过测试集调控制限来消除这些错误。',
 '','PCA能综合多变量主子空间和残差偏移，但依赖正常数据分布、线性低维假设和采样频率；传统阈值更易解释，但忽略协方差。此处只有预定工况和短时域，不推广成所有工业故障上的优势。',
 '','**动态因果建模数据基础已具备**：有完整1s测量/控制历史、明确故障时刻、独立运行划分及可复现实验。仍须处理闭环反馈、多速率测量、潜在混杂、执行器死区和观测可识别性；不能以PCA载荷直接生成因果结论。IDV4的持续漏报是已确认的困难案例，IDV11也有明显漏报和种子差异，均留给下一阶段分析，不移除样本。',
 '','## 文件入口','',
 '- 数据协议与源档案：`artifacts/d3/dataset/`，解释见 [数据集报告](D3_DATASET_REPORT.md)。',
 '- 训练模型和冻结控制限：`artifacts/d3/detection/model.npz`、`model_manifest.json`。',
 '- 全部测试统计、投影、贡献、逐点结果：`artifacts/d3/detection/test_*.npz`。',
 '- 总体和逐运行指标：`metrics.csv/json`、`per_run_metrics.csv/json`；所有误报漏报：`error_cases.csv`。',
 '- 独立HTML：[experiment.html](../../artifacts/d3/detection/experiment.html)；浏览器截图：[visual-qa.png](../../artifacts/d3/detection/visual-qa.png)。',
 '- 检测原理和口径：[检测报告](D3_ANOMALY_DETECTION_REPORT.md)。',
 '','## 验收范围和失败保留','',
 '四类、多种子、独立划分、预处理、PCA训练、T²、SPE、传统阈值、独立评估、离线可视化、重放和运行档案均有实际产物。若出现检测误报/漏报属于测量到的性能失败，原始数据及预测全部保留；未因检测不佳删除运行。生成/完整性失败会阻断评估。',
 '','正式数据的生成状态、文件哈希、训练/校准运行清单和模型哈希均已存档；实验解释以这些原始文件为准。依赖版本与源文件哈希见 artifacts/d3/execution_provenance.json。',
 '', '环境检查曾出现一次沙箱内Edge启动失败（浏览器进程关闭）；获准在沙箱外以无界面方式重试后，80条运行选项、图表和切换检查通过，页面脚本错误为0。此环境失败不涉及修改检测阈值或数据。']
Path('docs/research/D3_EXPERIMENT_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
sources=[*Path('src/causalverse/data').glob('*.py'),*Path('src/causalverse/detection').glob('*.py'),*Path('experiments').glob('*.*'),Path('src/causalverse/simulation/adapter.py')]
write_json(base/'execution_provenance.json',dict(plan_sha256=digest(root/'split_plan.json'),model_sha256=digest(det/'model.npz'),sources={str(p):digest(p) for p in sources},generation_environment='generation-environment-lock.txt',analysis_environment='analysis-environment-lock.txt'))
print('Report written')
