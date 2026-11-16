# 本机可行性验证记录

执行日期：2026-11-14；Windows 11 x64，CPython 3.12.14。独立环境 `.research/venv-tep`，不修改系统 Python。这里的数值来自实际执行；没有故障识别准确率、根因准确率或优化优越性结果。

## 已完成验证

|检查|结果|证据|
|---|---|---|
|checkout|成功，固定 commit 9a6c8e5fcef4a2850778704e7793c87b0a187005|`.research/upstream/tennessee-eastman-profbraatz`|
|原包 pip install|**失败**：Meson 即使 `fortran=disabled` 仍要求 C 编译器；本机无 cl/gcc/clang|meson.build 的 `project('tep','c',...)`；错误为 `Unknown compiler(s)`|
|依赖安装|NumPy、DoWhy 0.14、pytest 成功；pip check 无损坏依赖|`.research/requirements-tested.txt`|
|源码导入|将审计 checkout 的 src 放入 sys.path，显式 python 后端；成功|`.research/smoke_feasibility.py`|
|2h 正常工况|41 个记录点×41 测量，未停机，数值有限|`.research/tep_smoke_result.json`|
|种子|同种子测量逐元素完全一致，不同种子改变测量|同上；只验证这组配置|
|IDV4|0.5h 启动，持续至 2h，active_idv=[4]，未停机|JSON 及 `.research/smoke_trajectories.npz`|
|冷却控制|相同故障历史深拷贝后，两臂均冻结当前全部控制命令，动作臂 XMV10 增加 5 个百分点，推进 600 个 1s 步|JSON 中 initial=45.3983738%，requested=50.3983738%；两臂均继续运行|
|温度响应|动作臂末端温度比对照低约 26.4015°C|能力探针，**不是安全推荐或优化结果**；手动冻结全部控制后响应较大，需要后续选择性控制和多种子校验|
|流式接口|返回 time、time_seconds、measurements、mvs、shutdown|smoke 脚本/JSON|
|上游仿真器测试|`tests/test_simulator.py` **24 passed in 1.70s**|本次 pytest 实际输出；不是整个上游测试套件|
|24h 正常工况|完成 24h，未停机、数值有限；温度约 120.349–120.453°C，压力约 2685.724–2731.687kPa|`.research/reference_check_result.json`|
|参考数据读取|d00.dat=(52,500)，d00_te=(960,52)，d01=(480,52)，d01_te=(960,52)，d21=(480,52)，所查文件有限|同上；d00.dat 需要转置，不能认定所有训练文件均 480 行|
|DoWhy 估计与反驳|自建线性合成 SCM 真值 2.0，估计约 1.96234，random_common_cause 5 次小规模探针约 1.96206|`.research/dowhy_smoke_result.json`；仅 API 验证，不是 TEP 效应|
|DoWhy 个体反事实 API|显式可逆加性线性机制下，对 5 条证据执行 X→X+1，得到 5 行反事实|同上；机制已指定，不能证明未知工业 SCM 可识别|

正常与 IDV4 的 2h 末端温度差只有约 0.00169°C；闭环控制可补偿，单个末端温度差不能当故障检测依据，也不能由此认定该故障无影响。必须分析全轨迹、控制努力、其他变量及多次运行。

## 遇到并保留的失败

1. 沙箱联网 git/pip 失败，获得网络安装权限后继续；没有把网络失败误判为项目不存在。
2. 安装原 TEP 包的 Meson 错误见上表。源码路径运行成功仅说明绕过打包阶段后后端能运行；没有声称已修好原包。
3. DoWhy `gcm.auto.assign_causal_mechanisms` 默认 joblib 并行在中文临时路径遇到 `UnicodeEncodeError: 'ascii' codec can't encode characters`。本次改为显式线性机制，正好符合合成 SCM 设计，并非自动模型选择已修复。未来可测单进程或配置 ASCII 临时目录；当前不依赖自动搜索。
4. 首次导入绘图库尝试向用户目录写字体缓存，被限制；后续设置项目内 `MPLCONFIGDIR`。这不影响已保存的数值验证。

## 复现方式

在工作区根目录 PowerShell 中执行（依赖已安装；源码 checkout 需位于记录路径）：

```powershell
$env:MPLCONFIGDIR = Join-Path (Get-Location) '.research/mpl-cache'
.\.research\venv-tep\Scripts\python.exe .research/smoke_feasibility.py
.\.research\venv-tep\Scripts\python.exe .research/check_reference.py
$env:PYTHONPATH = (Resolve-Path '.research/upstream/tennessee-eastman-profbraatz/src').Path
.\.research\venv-tep\Scripts\python.exe -m pytest .research/upstream/tennessee-eastman-profbraatz/tests/test_simulator.py -q
.\.research\venv-tep\Scripts\python.exe -m pip check
```

新机器先创建独立 venv，根据 `.research/requirements-tested.txt` 安装依赖，clone 指定仓库并 checkout 上述 commit。此验证没有把有打包问题的 `tep` 注册成已安装发行包；脚本显式导入审计的源码路径。正式交付须解决安装封装。

## 尚未完成的实验

未安装/运行 tep-rust、TEP Studio、pyTEP、PyRCA、Tigramite、Causal-TS 或 UI；未做跨后端差分、完整故障多种子基准、真实 TEP 因果效应估计、风险校准、优化消融和真实工厂验证。本次目标是技术论证，这些已转入 [开发计划](DEVELOPMENT_PLAN.md)，不作为已取得成果。
