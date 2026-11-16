# S2 D3解释：等待配置Key

本地准备与降级测试已完成；没有真实DeepSeek调用验收。禁止把tests中的SYNTHETIC_TEST_FIXTURE当成API结果。

启动：项目根目录、原Python环境：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.\.research\venv-tep\Scripts\python.exe -B -m causalverse.evidence_s2.gateway
```

默认8769，只绑定127.0.0.1。若端口占用直接拒绝，不终止其他进程。S1和S2不能同时绑定8769；不要改8768。启动先完整读取原基线与封存清单，出现URL后使用。

Key仅从后端进程的DEEPSEEK_API_KEY读取。模型DEEPSEEK_MODEL默认deepseek-flash；DEEPSEEK_BASE_URL默认https://api.deepseek.com，支持官方/v1兼容路径，拒绝把Key发给任意其他域名、HTTP或重定向目标。模型名配置失败不会自动换模型。部署到自定义代理需单独设计可信域授权。

安全配置示例（在本机PowerShell操作，不把Key发到聊天，不把Key字符串写进脚本）：

```powershell
$deepseekSecret = Read-Host 'DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekSecret).Password
$env:PYTHONPATH=(Resolve-Path src).Path
.\.research\venv-tep\Scripts\python.exe -B -m causalverse.evidence_s2.gateway
```

终端环境不会自动传给已经启动的后端。配置后必须让旧预览进程退出并重新启动；不要重复启动而忽略端口占用错误。若当前8769是本任务启动的预览进程，可告知助手先停止该进程，再在已配置Key的终端启动。配置就绪后告知助手继续真实验收，不要粘贴Key。

UI先选D3并创建快照，再使用独立蓝色DeepSeek区域。缺Key禁用调用；D511和dirty状态禁用。用户不能上传prompt、指定文件路径或改写上下文。按需点击才调用API，未调用时没有AI文本。请求为非流式JSON，完整验证后才展示，不把未验证token直接输出。

后端30秒socket超时，只有明确429/503最多重试一次（0.5秒间隔）；超时/认证/余额/格式/引用拒绝不重试。每进程最多10次上游逻辑请求，间隔30秒，单并发；同会话同context成功结果复用。自动重试可能导致额外计费，跨进程不是持久预算。没有部署全站长时任务取消或流式UI。

原始ML证据与AI记录分开。AI输入是经验证的首/末/峰及首报警相邻指标事实，不是全部原始轨迹。API只返回结构化rule+证据引用；引用走S1.1验证，中文释义和所有数值由后端渲染。UI明确标记这点，不把后端模板冒充模型自由文本。当前不接受自由诊断文字、未知关系等级或控制建议。

API：先GET /api/session建立原会话，GET /api/ai/session获取S2 CSRF/config；POST /api/ai/explain只接受context_id，携带S2的X-CSRF-Token。上下文必须同会话且为D3 INFERRED检测。服务不提供聊天、上传或执行控制路由。

复现自动化测试，使用新目录保留首次失败：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$batch=Join-Path (Get-Location) ('artifacts/ai_s2/replay_'+[guid]::NewGuid().ToString('N'))
$env:S1_ACCEPTANCE=$batch
.\.research\venv-tep\Scripts\python.exe -B -m pytest s1_tests s1_1_tests s2_tests -v -p no:cacheprovider --basetemp "$batch/tmp" --junitxml "$batch/tests.xml"
```

测试不调用DeepSeek，用显式标记的替身验证传输路径；真实模型验收必须另行产生官方API请求ID、usage、已验证模型输出和浏览器截图，不能拿测试通过数替代。
