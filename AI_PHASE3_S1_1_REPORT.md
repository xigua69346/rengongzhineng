# S1.1 小范围完善交付报告

日期：2026-11-16（Asia/Hong_Kong）。仅实施S1.1；没有调用DeepSeek、读取或配置Key，没有进入S2，没有训练、校准、仿真或控制调用。8768、P0-01至P0-04、原七页和frontend/dist未修改。

## 1. 实施结果

完成三个展示修复和引用型Claim合同/后端验证器。完整自动化回归 **53通过、0失败、0跳过**；三个真实浏览器视口完成D3/D511实际计算与dirty检查，保存17张独立截图及DOM记录。原8992项基线全部匹配；原572条封存记录中567项匹配、5项为本次明确授权的S1源码变更，原清单未改，旧文件字节另存备份并核对原SHA256。上次补充验收封存的53项全部匹配。

本阶段已完成，停止并等待审核，不接入LLM。

## 2. 修改和新增清单

仅修改 `src/causalverse/evidence_s1/` 内以下5个文件：

|文件|修改原因|
|---|---|
|console/style.css|长原因码/摘要断行；dirty提示；窄屏布局；状态徽标禁止拆字|
|console/app.js|数据链、案例、时间、窗口dirty；保存提交条件以防异步返回误标；中文范围说明与原机器码并存|
|console/index.html|显式同源SVG favicon引用|
|gateway.py|favicon.svg和兼容favicon.ico路由；事实目录和Claim解析接口；S1.1保护检查入口|
|service.py|fact_catalog与resolve_claims适配，复用原身份、不可变快照和运行时|

新增实现：`claims.py`、`claim_schema_v11.json`、`protection_v11.py`、`release_v11.json`、`console/favicon.svg`。新增测试：`s1_1_tests/test_claims.py`。没有改原S1测试、历史报告、旧快照或验收截图。

独立验收批次：`artifacts/ai_s1_1/s1_1_20261116/`。包含before原文件副本、授权前后摘要、preflight、完整测试日志/JUnit、真实Claim回填样本、浏览器17张截图、最终保护结果和验证脚本。启动的新运行批次为 `artifacts/ai_s1_runs/fc4ca95faa3ac802a4028c8b949b6fa6/`，仅追加本次真实推理产物。

新增和修改后文件的完整逐项SHA256见本批次 `new_files_inventory.json`；其自身摘要及报告摘要见 `inventory_seal.json`。原8992、572及上次补充清单均保留原内容。清单封存之后，控制台新请求仍只追加运行证据，不覆盖此次清单。

## 3. 三个界面问题修复

### 长原因文本

摘要采用overflow-wrap:anywhere，保留完整原始机器原因码，同时增加“当前数据链未注册此功能”的中文说明。原evidence.data.reason未变，展开详情仍可核对。不是把拒绝原因删掉或改成通过。

### favicon

新增本地SVG图标，HTML显式引用/favicon.svg，同时/favicon.ico返回同一SVG及正确Content-Type。没有引入远程资源。HTTP测试两路径200；本次实际浏览器warning/error记录为空。

### dirty

完成过一次快照后，改变数据链、案例、as_of或窗口，显示“待更新：当前显示上一份快照，请重新计算”，卡片左侧增加提示边框。旧快照身份和内容保留，不改写历史快照。恢复与原快照相同的条件会解除dirty。

点击计算时先保存实际提交条件，响应返回后以该条件和当前选择比较；如果计算途中用户再次改变选择，返回快照仍保持dirty。请求失败保留错误提示与旧快照，不把失败当作已更新。所有渲染继续用textContent，不引入未验证HTML。

## 4. Claim合同和后端事实回填

新版本 `s1.1-claims-1`。后端从当前会话拥有的、SHA256重新核验的实际快照建立事实白名单；不会接受客户端上传数值、路径、标签或伪造观测。

新增API：

- `GET /api/facts/{context_id}`：同会话事实目录。
- `POST /api/claims/resolve`：引用验证及后端回填，沿用CSRF、Host/Origin、4KB请求体、单并发限制。
- `GET /api/contracts`：返回原知识目录及新Claim JSON Schema。原knowledge.json本身不覆盖。

请求信封仅包含schema_version、context_id、snapshot_sha256、claims。每条声明仅允许claim_id、claim_type、evidence_refs，以及按类型允许的comparison_basis或relation_level；拒绝额外value、explanation、probability、optimization_allowed等字段。每个引用必须给出evidence_id、fact_id、payload_sha256，逐项匹配同一context的后端目录。

事实目录由后端给出：

|字段|含义|
|---|---|
|fact_id|绑定context、evidence、载荷哈希及具体事实位置的SHA256标识|
|pointer|后端生成的事实位置，调用方不能自行提供任意JSON Pointer|
|value、unit、dimensions|从真实证据回填；包含指标/时刻、方法、窗口、动作、目标、预测时域等相应维度|
|semantic|DETECTION_METRIC、SCORE_NOT_PROBABILITY、CANDIDATE_NOT_ROOT_CAUSE、CONDITIONAL_PREDICTION_NOT_OBSERVATION、BACKEND_GATE、AUDIT_ONLY等语义|
|source_kind、evidence_status、method|区分原始审计引用与重新计算事实，结合原状态限制可用性|

直接事实返回原值和不可改变的语义标签，评分仍是评分、候选仍是候选、预测仍是条件预测。不接受“80%概率”“已确定根因”或自由生成叙述。所有数值均从目录回填；用于定位的ID不等于自由数值输出。

COMPARISON当前只允许DIFFERENCE，两个引用必须是有限标量、相同语义、单位和维度；支持例如同一动作/时域/目标的Action与Delta均值比较。差值由后端计算。不支持不可比时间/变量混算、评分向量冒充概率、客户端提交差值或最优动作排序。

RELATION必须区分VALIDATED_PATH、STATISTICAL_ASSOCIATION、CANDIDATE_RELATION、HYPOTHESIS。当前S1快照没有注册关系事实，所以这四类请求都保留所请求等级并返回INSUFFICIENT_EVIDENCE及NO_REGISTERED_RELATION_EVIDENCE；不虚构“已验证因果路径”。未来如需正向关系声明，必须另行接入经过核验的关系证据，此阶段没有做。

WAITING、UNAVAILABLE等事实不能支持正向FACT结论，只能以INSUFFICIENT_EVIDENCE引用。无法匹配的ID/哈希、类型或比较拒绝；缺少关系证据明确降级。所有输出optimization_allowed由后端固定false，预测原computation_status、contract_valid、support_status、uncertainty_status及拒绝原因作为后端事实保留。SUPPORTED不会变成优化授权。

原validate_claim最小状态检查保留为内部兼容入口，只支持原两种可用性声明；新HTTP解析不调用该旧入口，使用严格的resolve_claims。没有把旧入口包装成自然语言事实校验器。

## 5. 自动化验收

正式日志 `tests_network.log`、JUnit `tests_network.xml`：原S1回归27项与S1.1新增26项，共53项通过。

新增验证包括：

1. 真实D3评分事实回填与原证据值相同；保存resolved_real_claim.json。
2. 伪造evidence_id、fact_id、载荷哈希、snapshot哈希拒绝。
3. 跨context、跨会话拒绝。
4. 虚构value、自由解释、任意pointer等额外字段拒绝。
5. 评分冒充概率、候选冒充确定根因、预测冒充真实观测拒绝。
6. 客户端修改optimization_allowed及SUPPORTED冒充授权拒绝。
7. 重复claim_id、非法关系等级、不可比较向量拒绝。
8. 四种关系等级均在无关系证据时降级，而非强行给结论。
9. 预测、后端门控、原AUDIT_ONLY事实语义保留。
10. WAITING不能支持FACT，证据不足请求可返回明确不足状态。
11. Action/Delta同维度标量差值由后端计算。
12. HTTP事实目录、Claim解析、非法数值请求400、两种favicon路径200、新Schema版本返回正常。

原S1真实P0调用、禁止训练/校准/控制监视、未来扰动隔离、输入/身份/哈希、跨链拒绝、快照篡改、会话/CSRF/Origin和端口独占测试全部回归通过，没有改容差或旧测试。

首次测试结果为51通过、1项本机HTTP被沙箱WinError10013阻止，保留tests_first.log/xml；允许本机回环后，增加新HTTP测试并在独立目录重新执行，53通过。不是删去首次失败。浏览器最初在服务尚未启动时出现连接拒绝、错误页绑定被工具拒绝；服务完成校验启动后使用正常新页面验收成功，没有规避浏览器安全屏障。

## 6. 真实浏览器验收

使用现有ChatGPT in-app Chromium浏览器，通过正式browser viewport能力设置1920×1080、1366×768、390×844，不安装依赖、不用HTML静态检查代替浏览器。每个尺寸均实际执行D3和D511计算，保留完整状态、候选分歧和Action/Delta区间/支持门控。完整截图及DOM、时间记录在browser目录。

|检查|结果|
|---|---|
|三个视口D3/D511实际计算|通过，原始运行时重新计算|
|数据链切换dirty|通过，1920_dirty.png|
|案例变化dirty|1366与390通过，*_dirty_case.png|
|窗口、时间变化dirty|通过，390_dirty_window/time.png|
|重新计算后清除dirty|通过，等待“已封存 / SHA256 校验”后保存|
|5399秒识别与预测WAITING|通过，五项WAITING；不补齐未来窗口|
|UNSUPPORTED、INTERVAL_TOO_WIDE、优化未授权|完整保留；SUPPORTED分支也没有获得授权|
|长原因码断行|通过，原机器码完整保留，无摘要横向溢出|
|状态徽标窄屏拆字|验收中补充nowrap修复，最终不拆字|
|favicon、控制台|HTTP两路径200；实际浏览器console warning/error为[]|
|详情展开与来源|保存390_reason_expanded.png，原原因及证据ID可见|

最终DOM几何：三个视口innerWidth分别1920、1366、390，innerHeight分别1080、768、844；文档scrollWidth分别1905、1351、375（留有滚动条），均不超出视口；summaryOverflow均false，badgeWrapped均false。见final_geometry.json。截图使用真实浏览器全页捕获，截图高度可超过视口；不是手机真机或物理屏幕分辨率验收。完成后已恢复临时视口设置。

## 7. 文件保护与授权差异

写前原8992与572均全部匹配，结果preflight.json，未重新生成预期值。原protection_final.json摘要仍为`d55a4089a89e0472ed9b87e7e13248e07488bb1ff80982b8bda75847cfbf6923`，原572清单摘要仍为`08f8c1b002173b0000aa193bfd22f9df4fc45ee6142e0506f99f05508db728f4`。

最终 `protection_final_v11.json` 实测：

|集合|expected/checked|原SHA匹配|本次授权变化|意外变化/缺失/不可读/验证错误|
|---|---|---|---|---|
|原基线|8992/8992|8992|0|全部0|
|S1封存记录|572/572|567|5|全部0|
|上次补充封存|53/53|53|0|全部0|

unknown_files=[]。本次5项授权变更的原摘要和新摘要逐项记录于authorized_before.json、release_v11.json及最终保护结果；before副本逐项匹配原封存摘要。**不能声称572项当前内容全部未改变，也没有把原清单改成新值以掩盖差异。** 历史截图、测试、日志、快照和清单均未覆盖。

原S1保护函数保留不改；新增protection_v11读取原8992、572锚，并仅允许5个明确S1源文件匹配记录的新摘要，其余差异停止。最终独立脚本还检查上次53项补充封存及业务目录未知文件。新运行追加文件与本轮验收范围单独登记，不合并成旧572条。

release_v11是本机发布记录，不是第三方数字签名。与原S1相同，具备项目磁盘写权限的主体仍能破坏文件，不能宣称WORM或抵御本机管理员。

## 8. 复现命令

项目根目录PowerShell，仍使用现有Python环境：

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.\.research\venv-tep\Scripts\python.exe -B -m causalverse.evidence_s1.gateway
```

本次8769已启动，重复启动应因端口占用拒绝。不要启动或修改8768。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$batch=Join-Path (Get-Location) ('artifacts/ai_s1_1/replay_'+[guid]::NewGuid().ToString('N'))
$env:S1_ACCEPTANCE=$batch
.\.research\venv-tep\Scripts\python.exe -B -m pytest s1_tests s1_1_tests -v -p no:cacheprovider --basetemp "$batch/tmp" --junitxml "$batch/tests.xml"
```

需允许127.0.0.1测试网络；不需要外网或Key。测试输出必须取新批次，不能覆盖此次证据。新API使用与S1相同会话/CSRF，先取得现有context的facts目录，将其schema_version/context_id/snapshot_sha256及fact引用组合成Claim请求；请求不允许value或自由叙述。

## 9. 未实现与剩余边界

没有LLM调用、流式生成、自由文本解释、生成式报告或前端七页集成。当前采取封闭引用合同，而不是宣称能够验证任意自然语言；未知/无法验证的类型拒绝，关系证据不足降级。事实目录是有限白名单，不覆盖全部矩阵元素或所有未来研究指标；比较仅DIFFERENCE，不支持动作优化或自动排序。

无关系事实时不提供正向因果结论；现有支持不足、候选分歧和长时域宽区间未被解决。没有重新检查8768在线兼容性，仍留S4；本轮保护保证未改原站文件，不等于证明原站在线可用。

单机服务仍没有生产账户体系、TLS、持久会话恢复或生产级签名审计。S2仍需明确批准，不能将本次Schema/事实接口交付当作API接入授权。

本阶段工作到此停止，提交审核。
