# D2 仿真器适配与控制实现报告

日期：2026-11-14。交付范围为可安装的仿真适配层、真实轨迹与测试；未开发 UI、LLM、强化学习或优化算法。

## 实现入口与版本

核心：[adapter.py](../../src/causalverse/simulation/adapter.py)。统一实现 initialize、reset、step、run、get_measurements、get_control_variables、set_control、inject_fault、snapshot、restore、branch。构造时自动初始化，默认闭环且显式 `backend='python'`；没有 Fortran 自动选择路径。step 固定推进一秒，run 参数是额外运行的整数秒。

固定上游 `9a6c8e5fcef4a2850778704e7793c87b0a187005`。原始审计 checkout 未修改，`git status --short` 为空。将其 12 个 Python 模块原样复制到 `src/tep`，不改数值方程和 PI 实现；哈希、来源、commit 和打包差异记录在 `src/tep/PROVENANCE.json`。使用独立 setuptools 配置替代原包 Meson 构建，不包含编译扩展；保留 `LICENSE.upstream`。这属于有来源的第三方打包，不是原创数值引擎。

纯 Python wheel：`dist/causalverse_simulation-0.2.0-py3-none-any.whl`。运行依赖只有锁定的 NumPy 2.4.6；当前支持范围明确限制 Windows x64 CPython 3.12，其他平台未验收。不要与另一个提供顶层 `tep` 模块的包共装；独立环境避免同名覆盖。复制的 dashboard 等可选模块未安装其依赖，本阶段不调用。

## 选择性控制的实际机制

上游 `controllers.py` 的 fast loop 每 3 秒执行一次。ctrl10 使用 XMEAS(21) 更新 XMV(10)；ctrl18 根据 XMEAS(9) 更新冷却水温度设定点，形成串级控制。其他回路另有 360/900 秒调度。PI 使用速度式：当前命令加上误差变化和积分增量，状态包括 err_old、串级 setpoints、purge_flag 等，不是单独一个积分数组。

SelectiveController 每秒调用原始 controller.calculate，让全部回路按原调度更新。随后只在 `[start,end)` 窗口替换指定的输出分量，其余输出逐元素采用本次 PI 建议。不是冻结全部 12 路，也不是反复调用 set_mv 后被 PI 覆盖。动作结束后输出恢复 PI 建议。

当前策略为**有时限的绝对命令覆盖**。用户可读取当前值后加上给定百分点生成动作；日志记录排程时命令、每秒动作前命令、PI 建议和最终下发命令。原始速度式 PI 下一次使用实际下发值更新，覆盖期间其误差与串级状态仍继续演化；不宣称已证明无扰切换或全工况抗饱和，需要在未来控制策略研究中校验恢复瞬态。

```python
from causalverse.simulation import TEPAdapter
sim = TEPAdapter(random_seed=12345)
sim.inject_fault(14, onset_seconds=1800)
sim.run(3600)
baseline = sim.branch()
action = sim.branch()
current = action.get_control_variables()[9]
action.set_control(10, current + 1, duration_seconds=120,
                   action_id='coolant_test')
baseline.run(600)
action.run(600)
baseline.save('artifacts/example/baseline')
action.save('artifacts/example/action')
```

外部 ID 严格 1-based，内部数组 0-based。非法编号、非有限命令、范围外百分比、过去时刻、同路重叠动作会抛异常；不悄悄剪裁用户命令。XMV 是归一化命令，不是实际冷却流量。

## 执行器响应与 IDV(14)

上游 `python_backend.py` 中 `yy[38:50]` 为执行器位置状态，`_teproc.vcv` 为通过死区判断后的阀门目标；命令为 `_xmv`。IDV(14) 开启第 10 路粘滞：只有命令与已接受目标之差 **大于 2 个百分点**才更新目标，位置随后按时间常数趋近目标。这个实现不是永久机械锁死。

因此三种数据分别输出：PI 建议命令、实际下发 XMV、阀门目标/动态位置。阀门位置是仿真内部真值，不是标准 41 路传感器之一。内部冷却入口温度也作为诊断注入核查量保存，未来因果模型若使用这些额外量必须标为扩展观测实验。

本次使用同一 IDV14 历史，+1 与 +5 相对已接受目标的两组探针，分别验证命令被死区拦截和突破死区。具体数值与原始文件见 [验收结果](D2_VALIDATION_RESULTS.md)。

## 完整快照与分支

snapshot 对适配器整个对象图一次 deepcopy，restore 再 deepcopy；不是只复制 50 维状态。包括 process.yy/yp、_g 随机字、_wlk 随机游走参数及调度、_teproc 分析仪 xdel/采样时间和阀门缓存、测量与命令、控制器全部状态、仿真时钟与步号、故障/动作排程、终止原因和已记录历史。一次整体复制保留 state/disturbance wrapper 指向 process 的内部别名；测试确认分支没有共享 process。

branch 从此完整快照恢复并产生独立 run_id，记录 parent_run_id；此前历史完整保留。当前快照是同进程内存对象，不是可跨 Python/代码版本加载的持久化格式，也不接受外部 pickle。复制成本随历史增长，后续可拆分不可变历史以降低内存，但不能牺牲状态完整性。

无动作分支采用预定义零容差，即 np.array_equal；当前恢复、双分支及清洁环境重放均达到此要求。成对动作实验逐秒比较 RNG 字，当前两种动作都一致。配对结论限同版本、相同故障计划、相同时域且未停机的已测场景；停止时间或随机数调用路径不同可能破坏配对，不宣称已实现任意故障组合通用的外置扰动磁带。

## 数据时间语义与格式

上游 step 先在旧时刻 evaluate，再 Euler 积分到新状态。为避免额外 evaluate 消耗随机数，适配器不重复读数计算：`t_seconds` 是本次方程求值/测量时刻，`state_t_seconds` 是积分后执行器位置的时刻。第一秒记录 t=0/state_t=1；24h 保存 86400 行 t=0..86399，最终状态时刻 86400。调用 get_measurements 是最近一次已有测量，不做新求值。

每个目录包含 trajectory.csv、trajectory.npz、aligned_180s.npz、manifest.json；manifest 包含用户要求的运行/后端/种子/故障/动作/控制模式/终止字段和文件 SHA256。NPZ 保留 41 列 XMEAS、12 列 XMV，以及 PI/命令前值、阀门状态、IDV、RNG、内部入口温度。CSV 含 53 个标准过程通道加独立时间和阀门诊断列，不能把整张 CSV 称为“53 列”。

180s 对齐为 t%180==0 的精确抽取，不插值、不平均、不把历史缺少的第 12 路控制伪造出来。41/52/53/55 维各有来源模式；本阶段输出完整 53 路加独立元数据，未拼接 Harvard 数据。

## Windows 可复现安装

已在全新 `.venv-d2` 中完全离线安装 wheel 与 NumPy，然后运行同一测试和故障重放，不依赖 PYTHONPATH 或审计 checkout。命令（工作区根目录；Python 参数替换为 CPython 3.12 的路径）：

```powershell
python -m venv .venv-d2-repro
.\.venv-d2-repro\Scripts\python.exe -m pip install --no-index --find-links dist/wheelhouse dist/causalverse_simulation-0.2.0-py3-none-any.whl pytest==9.2.0
.\.venv-d2-repro\Scripts\python.exe -m pytest tests -q
.\.venv-d2-repro\Scripts\python.exe -m pip check
```

从源码重新构建（已提供 wheelhouse 中的 setuptools）：

```powershell
New-Item -ItemType Directory -Force build/tmp,dist | Out-Null
$env:TEMP = (Resolve-Path build/tmp).Path
$env:TMP = $env:TEMP
.\.venv-d2-repro\Scripts\python.exe -m pip install --no-index --find-links dist/wheelhouse setuptools==84.2.1
.\.venv-d2-repro\Scripts\python.exe -m pip wheel . --no-build-isolation --no-deps --no-cache-dir --wheel-dir dist
```

完整集成：`python scripts/validate_d2.py`，再 `python scripts/verify_artifacts_d2.py`，均使用已安装包的环境解释器。先把现有 artifacts/d2 **移到明确命名的归档目录**以保留证据，禁止覆盖失败；`scripts/reproduce_d2.ps1 -Python <Python312路径> -Full` 检测已有结果时会拒绝覆盖。快速验收省略 -Full。

最初默认临时目录打包曾出现 WinError 3；明确设置项目内 TEMP/TMP 后构建成功。已解决的是独立发行包的部署，不是修改原始 Meson 仓库。版本锁和清洁环境日志位于 artifacts/d2。
