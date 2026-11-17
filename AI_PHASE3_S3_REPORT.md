# CausalVerse S3：实时工业数据与AI监控引擎验收报告

日期：2026-11-16；项目目录：D:/广西人工智能大赛。范围仅S3，不进入S4。此前中止报告的原字节已保存在本批次before_resume/，没有当作封存历史删除。

## 1. 结论与适用边界

S3核心闭环已实际完成：独立TEP生产进程 → 每秒41测量/12命令采集 → 原冻结PCA/Threshold真实计算 → 自动异常事件 → 独立8770工作台与证据账本。

最终独立release目录：18项Python测试通过、0失败/错误/跳过；3项Node展示逻辑测试通过。80个历史测试运行、5600个原检测时刻与P0-02真实运行时及历史档案匹配，所有数值最大绝对误差0，22400项Boolean逐项一致，容差仍rtol=atol=1e-12。

这是固定180秒网格的在线影子监控，不是已经验证的秒级故障报警系统。新LIVE数据泛化性能尚未验证；自动事件不是自动机制诊断或物理根因识别。没有DeepSeek、MPC、优化器、AI动作执行或set_control调用。原PI正常工作，optimization_allowed、sim_execution_allowed、physical_execution_allowed均false。

## 2. 实现与新增源码完整清单

原有业务源码修改0个。严格新增18文件：

|位置|文件|职责|
|---|---|---|
|src/causalverse/autonomy/|__init__.py|独立S3包|
|同上|contracts.py|固定53通道schema、序号/时间/shape/有限性及payload SHA|
|同上|identity.py|独立LIVE_TEP_V1随机Episode、Observation身份|
|同上|acquisition.py|原adapter输出白名单投影、真实时钟及分析仪新鲜度|
|同上|journal.py|排他创建、追加hash链、完整性核验和游标读取|
|同上|detection_bridge.py|恢复冻结参数、调用原transform/scores/score、评分/贡献/报警与推理ID|
|同上|events.py|原报警输出的事件策略：候选、连续2网格确认、去重、清除、未触发|
|同上|episode.py|spawn生产进程、单写者、时钟/倍率、暂停/停止/心跳监督|
|同上|gateway.py|仅127.0.0.1的HTTP控制台、会话/CSRF/Host/Origin、独占端口检查|
|同上|protection.py|累积原验收版本SHA核验，不重造历史基线|
|src/causalverse/autonomy/console/|index.html、app.js、style.css|3个独立工业HMI展示文件|
|autonomy_tests/|test_acquisition.py|真实采集、新鲜度、输入拒绝、账本篡改/截断|
|autonomy_tests/|test_detection_bridge.py|80运行重放、训练/控制限入口阻断、事件与非法网格|
|autonomy_tests/|test_episode_security.py|真实生产、1:1、加速、人工故障、暂停恢复停止、进程失联、跨运行访问|
|autonomy_tests/|test_live_console.cjs|前端语法、来源/状态、执行poll路径的UI传输替身单测|
|protocols/autonomy/|live_tep_v1.json|固定S3协议说明，无任意动作/模型配置入口|

报告、日志、截图、测试临时数据及验收清单属于明确授权的交付证据，不增加业务源码范围。源码逐文件SHA见本批次source_inventory.json，全部证据快照见new_files_inventory.json，清单自身SHA见inventory_seal.json。

## 3. 数据、进程与安全边界

复用原TEPAdapter及固定Python引擎；后台实际step推进，没有播放历史NPZ。每次启动使用原默认种子和正常PI；目前不提供种子配置或多生产实例。一个服务最多一条在运行生产链。模型参数只读来自原Registry，PCA29分量，41列次序/预处理/控制限不变。PCA保留T²严格大于 OR SPE严格大于，Threshold同样严格大于。

测量时间与积分后状态时间分别记录：第一条measurement_time=0、state_time=1。新鲜度使用引擎实际求值钟而非简单步号换算，避免浮点边界错位；1000秒真实测试逐次对照原气体/产品分析仪采样调度。19个组分通道明确标为延迟采样保持，不作为每秒新样本。

采集模块只输出白名单测量、命令及身份/质量/时刻，原始idv、RNG、隐藏阀位、内部入口温度等不进入观测/检测/事件。人工故障入口是操作员实验控制，仅支持4/11/14，私有请求日志和在线观测隔离；它不是AI自动控制，不向模型传递故障ID或注入计划。

每个观测有schema/hash/顺序；每次推理保留Episode、输入payload hash、模型参数hash/version、推理ID、实际耗时、全部数组/贡献和Boolean。完整源账本SHA在运行结束后独立记录，不用会增长的文件hash替代模型实际输入hash。

后台事件账本排他创建并hash链接，观测/推理/事件/生命周期按顺序追加。内存只保留最近5000条，断线后同会话可按游标继续，较大缺口回读已核验账本并分批返回。尚未完成写入的实时尾行只能在显式allow_partial模式下忽略；关闭账本截断默认拒绝。

生产进程由父服务监督：约15秒心跳失联会终止，非有限/序号/时刻异常会失败退出，原引擎停机继续作为硬保护；被强制结束的进程显示UNAVAILABLE_PROCESS_EXIT并保留账本和supervisor记录。强制退出路径已实测；15秒冻结心跳分支尚未单独做挂起压力实验，不把它计作实测通过。

## 4. 真实运行与自动事件证据

唯一验收目录：artifacts/autonomy/s3_acceptance_a9d93ec42bf004d1/。

|实际运行|结果与来源|
|---|---|
|最终测试真实生产|release/live/下保留4500条1秒观测、15次真实冻结推理及自动事件；完成状态COMPLETED；见release/live_summary.json和原events.jsonl|
|工作台正常/故障案例|Episode f7c56b45224a842288b7e9ef74b2964c；原日志位于artifacts/autonomy/s3_a7c2a6586cc224d4fb3ba7ab/runs/对应目录|
|该案例实际数量|13624条观测，measurement_time=0..13623；66次推理，66条事件/未触发更新；最终STOPPED|
|故障与检出|操作员于6812秒申请IDV14，私有日志保留；AI首次报警7020秒，之后CONFIRMED；这些是实测时刻，不预置触发|
|真实最新事件|最后记录13500秒、连续37个报警网格；同一event_id保持去重；变量为SPE贡献，不称根因|
|1:1工作台案例|Episode d964e3117b83c1e40b520e153ad46acc，61条观测0..60，STOPPED；暖机未齐，推理0次，明确WAITING|

工作台案例期间请求100×加速；扣除不了暂停的墙钟平均倍率会下降，界面如实显示实测平均值，而非硬填100。1:1案例约61秒墙钟推进61条记录。暂停/恢复不会重置原故障或偷偷替换轨迹。动画仅表示生产运行状态，阀/命令与流量读数都来自真采集；不显示虚构实际阀位。

浏览器案例日志SHA、数量、身份及最新事件汇总在browser_production_summary.json。所有验收生产已停止，当前8770仅保留服务待审核，不在后台持续推进新实验。

## 5. 80运行冻结重放与失败保留

release/80_run_comparison.json逐运行记录70点、所有数值最大误差、Boolean、原档案MATCHED及离线误报/漏报。release/recomputed_arrays/完整保存80份实际重算数组，release/p0_replay/保存原P0-02运行时的独立推理工件。

先从原41列原始轨迹按原reader校验processed和180秒网格，再调用S3桥接与P0-02计算，最后对照旧档案。没有用旧预测数组作为模型输入。所有训练fit及control_limit入口在验收进程中被拦截，计算仍完成；没有放宽容差或重新估计参数。

对原历史标签的统计仅在计算后的离线评价器读取，在线模块不读：PCA误报18点、漏报1953点；Threshold误报28点、漏报1857点。80个运行中完全未报警分别13/9条，包含正常运行，不能称13/9条故障运行漏检。以上保留旧弱故障/随机扰动性能局限，不把重放数值一致包装成检测性能改善。在线没有真标签，因此误报/漏报状态为NOT_EVALUATED/UNAVAILABLE，不能填0冒充正确。

## 6. 自动化测试与首次失败

最终release/tests.xml、tests.log：18 passed，33.35秒，0失败/错误/跳过。release/console.log：3 passed。测试内容包括：真实1000秒采集/分析仪调度、53通道、缺失/乱序/非有限/跨Episode/hash拒绝、账本篡改和截断拒绝、80运行全量重算、原训练/控制限入口拦截、事件确认/去重/清除/未触发、非法网格、真实4500秒生产、1:1推进、暂停/恢复/停止、杀进程后失联记录、游标续读、恶意Origin、无会话/跨owner访问和非法参数拒绝。

首轮tests_first.log/xml：15通过、1项本机HTTP被沙箱WinError10013阻止；原日志保留，随后获准环境HTTP复测通过。之后tests_security、tests_integrity等日志分别保留，最终全套写入新release目录。

新增前端曾出现重复声明/缺失poll、新Episode旧面板残留，以及修复时requestedEpisode未定义；均如实记录并修复，新增UI执行测试不冒充真实模型。首次浏览器连接超时及截图命名问题见first_failures.md。较早的报告范围差异没有被证实为外部写入，不再作此归因。最终真实运行依据是release日志和浏览器证据。

## 7. 三视口浏览器验收

使用真实IAB Chromium，实际视口1920×1080、1366×768、390×844。browser/final_*.png为自动报警已确认后的完整页面；expanded_*.png为完整证据展开；waiting_*.png为新Episode原模型暖机等待。DOM和viewport_checks/expanded_checks/waiting_checks分别保存身份、状态和宽度。

三个视口scrollWidth分别1905/1351/375，均不超过视口。长原因、hash和JSON无整页横向溢出；228863字符证据在折叠区内滚动。检查启动、人工故障、自动事件、暂停、恢复、停止、新Episode清空旧AI结果、详情展开/收起、页面滚动。console.json为[]。最终stopped_390.png对应真实STOPPED回执。

截图来自真实浏览器，没有改DOM填数或用截图替身。browser/warmup_1920.png是早期正常运行截图，名称不准确，未计作正式WAITING证据；正式以waiting_*为准。历史图片/失败均保留。三视口为浏览器CSS视口，不称手机真机测试。

## 8. 文件保护与Git

原累积12957项（含旧8992、各阶段封存并按已验收版本合并）写前匹配；服务启动时再次核验。最终protection_release.json：expected_count=checked_count=12957，changed_hashes/missing_files/unreadable_files/verification_errors/unknown_files均[]；另核8份V3文档，变化0。没有重造旧预期或覆盖旧清单。运行追加目录、S3本轮证据与既有4份Git清单副本分别归类，不把未封存追加文件冒充旧基线项。

独立备份仓库工作区保持干净，HEAD=e05a2a48f23667c543b381e8ac150eee1d407c20；原S2标签指向9e828050399eff3506c5806638eca2e67d7c4765，收尾标签指向上述HEAD，均未修改。没有Git提交、推送或main变更。8768、8769及七页/frontend/dist未改，也没有为本阶段启动或替换它们；其在线兼容性不在此报告新增通过项中。

## 9. 复现命令

使用已有环境，不安装依赖。8770已由本阶段服务占用时直接打开页面；不要重复启动或杀未知端口进程。重启服务后旧会话不能自动恢复，需刷新页面并新建Episode，历史账本仍在本机。

```powershell
Set-Location -LiteralPath 'D:/广西人工智能大赛'
$env:PYTHONPATH=(Resolve-Path src).Path
$env:PYTHONDONTWRITEBYTECODE='1'
& './.research/venv-tep/Scripts/python.exe' -B -m causalverse.autonomy.gateway --port 8770
```

测试必须新唯一输出目录，不能复用封存release目录：

```powershell
$env:S3_ACCEPTANCE=Join-Path (Get-Location) ('artifacts/autonomy/retest_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $env:S3_ACCEPTANCE | Out-Null
& './.research/venv-tep/Scripts/python.exe' -B -m pytest autonomy_tests -p no:cacheprovider --basetemp "$env:S3_ACCEPTANCE/tmp" --junitxml "$env:S3_ACCEPTANCE/tests.xml" -q
node --test autonomy_tests/test_live_console.cjs
```

不依赖API Key、不读取或配置Key、不发外部API请求。本轮新增费用0，无训练/校准/依赖安装。测试中的UI传输替身只验证JS状态，不计作真实工业运行。

## 10. 未解决问题和下一阶段建议

- 新LIVE分布报警性能未验证；180秒网格与1800秒暖机限制保留，不能声称秒级安全联锁。
- 单机单生产Episode、固定原默认种子；没有跨服务重启恢复内存会话、自动续跑死进程或持久化快照。网络短断线可游标续读；服务重启后安全拒绝旧会话，原账本可离线核验。
- 原算法评分本身很快，但状态API在大游标缺口时需核验较长JSONL，长期运行的分页/索引和高负载延迟仍需优化；当前单次运行限14400秒。
- 15秒心跳超时分支已实现，尚未单独做冻结进程压力测试；真正被杀进程退出路径已测。
- 默认PI与原引擎停机保护继续存在，不代表新增工业安全认证、未知故障诊断或控制权限。
- S4若获批准，优先验证未知起点诊断窗口和同Episode证据，不把现有事件直接称为故障根因。当前未开始S4。

本阶段到S3监控与验收封存为止。提交审核，等待用户批准下一阶段。
