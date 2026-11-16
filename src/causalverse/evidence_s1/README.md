# S1 独立证据服务

仅使用现有Python环境；不需要Key，不连接DeepSeek，不提供控制接口。

在项目根目录PowerShell执行：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.\.research\venv-tep\Scripts\python.exe -B -m causalverse.evidence_s1.gateway
```

默认独占127.0.0.1:8769。已占用直接失败，不终止占用进程。首次启动核对8992项保护文件，可能等待数分钟；出现启动URL后再访问。每次启动在artifacts/ai_s1_runs生成随机新批次。Ctrl+C仅停止此旁路。不要改8768。

复现测试（新目录，不覆盖历史）：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$batch=Join-Path (Get-Location) ('artifacts/ai_s1_acceptance/replay_'+[guid]::NewGuid().ToString('N'))
$env:S1_ACCEPTANCE=$batch
.\.research\venv-tep\Scripts\python.exe -B -m pytest s1_tests -v -p no:cacheprovider --basetemp "$batch/tmp" --junitxml "$batch/tests.xml"
```

测试需要允许本机回环网络。批次test_runtime、additional_runtime均使用排他新建，复跑必须更换batch。

HTTP：GET /api/session取得HttpOnly会话及CSRF；GET /api/catalog选随机selection_id；POST /api/contexts仅接收selection_id、as_of整数、window（180/600/1800），并携带X-CSRF-Token。GET /api/contexts/{id}及/api/evidence/{id}仅限创建会话。GET /api/contracts为知识和Claim合同。禁止路径、标签、自由观测、Key、控制等输入。没有上传/删除/改写/聊天路由。

snapshots仅新增，_private存真实运行身份和原始推理产物，HTTP从不挂载该目录。证据payload_sha256绑定公开内容；私有映射保存完整快照SHA256及P0推理ID。读取快照重新核对SHA256。此为应用层不可变，不是磁盘WORM；拥有操作系统写权限的人仍可改文件，读取时会检测快照变化。会话和索引内存保存，重启不会把旧快照恢复为在线会话，但旧文件全部保留。

仅本机个人开发控制台，不提供多用户部署、TLS、长期会话管理或生产级审计签名。限制128会话/128上下文、单并发计算、4KB请求体、10秒socket超时。无自动模型推理超时取消；数值计算占用的资源受单并发限制。S2须另行批准。
