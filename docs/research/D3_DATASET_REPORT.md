# D3 工业故障数据集报告

本阶段复用 D2 TEPAdapter；未修改仿真器、控制、快照或历史分支接口。数据是 TEP 仿真输出，不是真实工厂采集数据。运行统计及验收见 [实验结果](D3_EXPERIMENT_RESULTS.md)。

## 冻结协议

先测量单条4h仿真：模拟10.2214s，含原始数据导出11.3672s；四进程200条的粗估为568.36s，磁盘空间约428GB足够。因此保留完整规模，没有缩减样本数。实测耗时和估算保存在 `artifacts/d3/pilot_timing.json`；并行争用及导出会令实耗不同于估算。

正式生成前单独执行 `experiments/run_dataset.py --freeze` 保存 split_plan.json，之后生成程序只读取该清单。四类工况分别为正常/IDV4/IDV11/IDV14，每类 train20、validation10、test20，总计200条完整独立初始化运行。共200个不同种子，无分支共享历史；单次pilot的seed99101不进入正式数据。

每条运行14400s，故障在3600s启用，到14400s结束，设定持续10800s。前1800s为预热，从1800s开始用于建模和评估。以t%180==0精确抽样，共70个处理后样本/运行；故障运行有10个故障前样本、60个故障后样本。训练数据保留所有故障，但本阶段标准化和正常检测模型仅拟合20条正常训练运行。

种子规则为 train100000、validation200000、test300000 加 fault_id*1000 + 从0起的运行序号。完整种子和run_id清单是唯一划分依据。不同运行使用独立对象及种子，不宣称已证明伪随机数子流在数学上绝不重叠。所有数据按完整运行划分，不随机拆行，窗口不跨运行构建。

## 目录与来源

- `artifacts/d3/dataset/split_plan.json`：正式划分及检测协议。
- `dataset/raw/<dataset_run_id>/`：每次运行的trajectory.csv、trajectory.npz、aligned_180s.npz、独立manifest.json。
- `dataset/processed/<dataset_run_id>.npz`：预热过滤后的180s数据，XMEAS、XMV分数组存储，另有时间和标签。
- `dataset/generation_log.json`：每条完成/失败状态、记录数、耗时；失败不会悄悄排除。
- `dataset/integrity_audit.json`：逐运行哈希、完整性与处理后数组一致性核查。
- `dataset/reproduction_audit.json` 和 `artifacts/d3/replay/`：四类各一条完整重放，原始数组逐元素比较。

manifest 继承D2记录的engine_commit、backend、random_seed、controller_mode、故障/动作时间和文件SHA256；额外记录split、dataset_run_id、冻结清单哈希、请求时长、设定及实际故障持续时间。engine_commit固定9a6c8e5fcef4a2850778704e7793c87b0a187005，backend固定python。无动作干预，不人为制造更易检出的故障。

## 数据契约与检查

严格区分41路测量、12路归一化控制命令。外部编号1-based、数组0-based，XMEAS(21)为反应釜冷却水出口温度；XMV(10)为冷却阀命令，不能标成实际水流量。53路完整仿真过程变量与52路历史数据、55列含元数据数据不是同一种模式，未进行跨版本拼接。

1s测量时间沿用D2：t_seconds是积分前求值时刻，state_t_seconds是积分后状态时刻。4h原始轨迹记录t=0..14399，而最终状态时刻为14400。CSV含额外时间和执行器诊断列，整体列数不是53。

完整性检查要求原始时刻从零开始且逐秒连续、14400行、XMEAS shape=(14400,41)、XMV=(14400,12)、全部有限。出现缺失、NaN、Inf、错误列数或提前终止则保留原始运行并标失败，停止正式评估，不插值、不填零、不删除失败样本。

标签由冻结的故障计划和测量时间生成，故障前为0、故障启用时刻起为1；随机故障的物理响应可能晚于开关启用，此差异不通过移动真值时刻消除。IDV内部标志只在离线完整性审计核对，不进入在线检测特征。执行器真值、RNG、入口温度等保存在原始档案，但检测只用XMEAS。

组成分析仪有采样保持，180s抽样并不令所有41路变成同速独立观测；样本仍存在自相关。保留1s原始数据供下一阶段时滞和多速率研究，不能只留下抽样表。

## 复现

使用CPython3.12；核心依赖NumPy2.4.6，图表可选依赖Plotly7.1.0。当前源代码在项目根目录通过以下命令使用，D2 wheel保留不覆盖：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.\.research\venv-tep\Scripts\python.exe experiments/run_dataset.py --freeze
.\.research\venv-tep\Scripts\python.exe experiments/run_dataset.py
.\.research\venv-tep\Scripts\python.exe experiments/verify_dataset.py
.\.research\venv-tep\Scripts\python.exe experiments/run_detection.py
.\.research\venv-tep\Scripts\python.exe -m pytest tests -q
```

完整重跑前将已有artifacts/d3移到明确命名的归档目录，保留证据。freeze遇到已有计划会拒绝，单运行生成遇到已有目录会拒绝，检测遇到已有输出会拒绝。入口脚本 `experiments/reproduce_d3.ps1 -Python <解释器路径>` 包含失败退出检查。首次新环境可安装本项目 `.[analysis]`，或用归档的精确环境锁恢复环境；无需编译TEP数值扩展。

原始引擎许可和来源继续遵循 [第三方声明](../../THIRD_PARTY_NOTICES.md)。本阶段不把新仿真数据宣称为不受上游权利约束的公共领域数据，也未导入Harvard大数据文件。
