# S2第一阶段：真实DeepSeek API最小闭环验收报告

日期：2026-11-16（Asia/Hong_Kong）。本报告为配置Key后的真实验收版。根目录原AI_PHASE3_S2_REPORT.md为已封存的“等待Key准备报告”，保持原样；真实调用结论以本报告为准。仅完成D3异常检测解释，不进入S3。

## 1. 结论

**一个真实D3案例的端到端最小闭环已完成。** 用户在本机终端配置Key，后端真实调用官方deepseek-flash，返回结构化分析；后端重新验证同context事实引用、哈希与解释依据，回填数值后在8769展示VALIDATED。没有模拟回复或预设模型输出替代真实调用。

同一注册案例共4次真实调用：前三次严格拒绝，第四次验证通过。失败截图、usage和审计保留，未删除失败样本，未修改验证器或数值容差。最终成功耗时3695.5601ms，6041 tokens，产生5条发现。

DeepSeek真实参与的是证据选择、解释类型与对照组织。中文释义和所有数值由后端受控渲染，UI明确标记；不能宣称DeepSeek自由撰写了全部中文文本。此为S1.1严格合同下的结构化解释闭环，不是开放聊天或确定根因识别。

## 2. 实施架构及本轮修改

流程：8769选D3 → 原冻结PCA/Threshold实际重算 → 原S1.1身份/快照/事实目录校验 → 发送筛选后的检测事实 → 官方DeepSeek JSON调用 → 原S1.1引用校验与独立解释规则校验 → 后端数值/释义回填 → 独立蓝色AI区域展示。

P0-01至P0-04、原七页面、frontend/dist、8768、模型、实验数据和校准记录均未修改。没有训练、校准、启动仿真、安装依赖或提供控制接口。Key仅由用户启动的后端进程持有，没有发到聊天、前端或报告。

准备版实现清单、81项原回归及缺Key验收见已封存准备报告和清单。本轮为定位真实返回的拒绝原因，修改了两个S2文件：

|文件|修改|保护方式|
|---|---|---|
|src/causalverse/evidence_s2/runtime.py|增加私有、Key脱敏的未验证输出记录；精确校验错误码；prompt版本/哈希审计|修改前及中间版本完整备份，原/新SHA256逐项登记|
|src/causalverse/evidence_s2/explanation.py|提示词明确每项引用数量，发送原JSON Schema，将findings下限与原合同对齐为2|validate函数AST完全一致；原maxItems=2及拒绝逻辑未改变|

新增测试：s2_tests/test_diagnostic.py、s2_tests/test_prompt_alignment.py。新增验收脚本verify.py、replay_acceptance.py均在本独立批次。没有为了通过而扩大引用上限、修剪失败返回、放宽容差或绕过S1.1。

独立批次：artifacts/ai_s2/real_20261116_162851/。完整新增/修改文件SHA256见本批次new_files_inventory.json，清单摘要见inventory_seal.json。包含本报告、源码前后副本、测试、真实调用产物与截图。原准备清单及所有旧证据不覆盖。

## 3. 真实API记录

以下是实际provider返回及本地审计，所有调用均为OFFICIAL_API，非测试替身，attempts均为1：

|序号|本地request_id|provider request ID|状态|输入/输出/总tokens|耗时ms|
|---|---|---|---|---|---|
|1|68fca11e2a2848937f9cfabbaca8d5cb|d5371736-137d-49f9-aa9e-009aaa3d8423|REJECTED|4662 / 1109 / 5771|4483.2171|
|2|530cfe1c92f555388be12b4d2442987e|54b0a93a-b509-47b5-93d2-16537855f751|REJECTED|4662 / 1131 / 5793|4561.9932|
|3|9115b6fe6d5804e14ed0101aaf4afc25|1d4f51bb-ec1b-4d24-9370-cc4ba5330ab2|REJECTED / AI_REFERENCE_LIMIT|4699 / 1144 / 5843|4360.2484|
|4|c2a0ac1ae0fdadfba8a9d5c5a729a936|7dcc5ec2-2a87-4c26-b6e6-eaba0eaf57f0|VALIDATED|5097 / 944 / 6041|3695.5601|

第四次调用时间2026-11-16 16:51:43（香港时间）；模型deepseek-flash，prompt_version=d3-explanation-policy-2。request_id是本地标识，provider_request_id是上游响应ID，不把两者混为一谈。模型别名不等于冻结LLM权重版本。

真实成功运行批次：artifacts/ai_s2_runs/84ab6af148e1eb0a16eb7f5345248b60/。其ai目录保存原输入、已验证模型JSON、审计及私有未验证输出副本；evidence目录保存P0实际计算、快照和私有身份映射。失败运行批次5619d6906fc68302c4080c1486324389及077b17de4b22171a3a3bae9a5916e9bd保留原文件。

## 4. 同案例和事实来源证明

用户重启后会话、随机案例别名、context_id会改变。后台只用原私有注册身份查找同一案例，再在公开下拉选择相应随机别名，未用真实故障标签选择模型或替换输入。

独立只读复核replay_acceptance.py证明：4次调用的私有data_ref一致，4份检测数值数组逐元素序列化一致。每份context快照SHA256与私有映射/调用审计一致，公开检测payload_sha256重算一致，原模型ID/参数哈希仍来自冻结P0运行时。

成功context_id：d90db5c70ba32cea3cfdccce3ffc3abf。

成功检测evidence_id：5015ff0bfde1407a03b44b0ac59bd391。

检测payload_sha256：d777c3b3a67b58383f61bb211d05e7393d7b579b3da3e6cc0d1bc8bf266040ca。

snapshot_sha256：de82643cda64fedade0a4d23baf82b9e8c48ae229a9972d5d1276b4643926732。

as_of=5400，实际使用1800至5400秒的21个检测网格时刻，没有补足未来70个点。DeepSeek只接收筛选后的检测分数和Boolean报警事实；未发送历史真值、故障标签、RNG、隐藏执行器、原始文件路径、未来分支或全部原始数据。分类结果虽在原证据台可见，但没有进入本次DeepSeek上下文。

## 5. 实际分析内容及引用校验

DeepSeek成功返回的原始结构化输出保存在real_model_output.json，后端回填结果为real_verified_analysis.json：

1. METRIC_EVIDENCE：选择4860秒T²=57.86709703253733，事实位置/data/arrays/T2/17；释义明确统计量不是故障概率。
2. ALARM_EVIDENCE：选择5040秒Threshold报警True，事实位置/data/arrays/pred_Threshold/18；保留原控制限和原报警规则。
3. DETECTOR_AGREEMENT：选择4860秒的PCA=True、Threshold=False，同一时刻存在检测分歧，不宣称确定物理根因。
4. TEMPORAL_CHANGE：选择T²在1800秒25.996666956458284与5400秒35.40702446769979的有限观测对照；不把两点对照说成完整单调过程或因果关系。
5. INSUFFICIENT_ROOT_CAUSE：明确现有统计检测不足以确定物理根因，没有验证因果路径或干预授权，历史仿真不是现场实时观测。

5条发现共引用7次事实，数值全部来自原事实目录。独立进程从实际快照和已验证模型JSON重新运行同一验证器，得到与原审计analysis完全相同的结果，不再调用API、不重跑数值模型。optimization_allowed全部false。模型输出不能添加概率、根因标签或授权状态。

另对这份真实成功输出的副本执行8项负面回放：伪造fact_id、跨context、虚构value、评分改成概率、候选/检测改成确定根因、预测冒充观测、修改优化授权、3条引用。全部拒绝。见real_output_negative_replay.json。没有改写原始成功输出或故意失败输出。

当前不生成统计因果关联、候选物理关系或自由假设；缺少相应证据时不输出正向关系结论。DIRECT_OBSERVATION_OF_MODEL_OUTPUT指对真实模型输出的观测，不是声称统计量是物理测量或因果真值。

## 6. 三次失败和修正经过

前两次API正常返回，但只记录通用AI_EVIDENCE_VALIDATION_FAILED，未保存原始结构化输出，所以不能事后断言其具体原因与第三次完全相同。这是首版诊断可追溯性的缺口。其provider ID、usage、审计、输入及拒绝截图均保留，没有伪造缺失的返回正文。

增加脱敏的私有未验证输出后，第三次明确定位为AI_REFERENCE_LIMIT：模型在INSUFFICIENT_ROOT_CAUSE项引用了3条事实，而原合同maxItems=2。原提示词没有明确这一引用上限，且findings下限文案与合同不一致。修正只将数量限制和原JSON Schema加入模型提示，不调整验证器。新增测试证明3条引用仍拒绝，alignment_change.json记录validate函数AST不变。

第四次在相同合同和相同注册案例下产生符合约束的真实返回，才显示VALIDATED。没有在后端剪掉第三条引用以“修复”失败，没有展示未验证内容，也没有把前三次说成通过。

用户两次重启过程中出现的PowerShell路径缺分隔符报错为启动操作问题，与上游API故障无关；改用正斜杠绝对路径后正常启动。Key始终留在用户原终端环境，助手未复制或接管该Key。

## 7. 浏览器交付

实际在8769点击“调用真实DeepSeek分析”，不是只调用测试函数。成功页面显示DeepSeek模型、VALIDATED、3695.6ms、本地请求ID、实际分析、原事实位置/哈希、usage和根因局限。AI区域与原ML结果视觉分开，拒绝的内容没有显示为解释。

截图及DOM：

- 01_ready：真实调用前状态。
- 02_api_result：第一次校验拒绝。
- 03_retry_observation：第二次拒绝。
- 04_diagnostic_rejection：第三次引用上限拒绝。
- 05_validated_full、05_validated_dom：真实成功整页和DOM。
- 06_validated_ai_panel：浏览器直接截取成功AI区域，便于评委查看；不是合成图或手改DOM。

浏览器console warning/error=[]，结果页面保持VALIDATED。成功整页及AI面板截图以1920×1080视口完成。额外尝试1366/390成功内容截图时工具连续报告Unable to capture screenshot，未将这些未取得的截图写成验收通过；恢复默认视口并保留错误说明。前期缺Key三视口截图仍完整保存，不冒充真实调用成功截图。

既有主视觉静态文案仍含“DeepSeek尚未接入”，这是从S1复制的过时展示文案，与下方实际VALIDATED区不一致，列为展示遗留项。此次没有通过临时DOM改写截图掩盖它。评审应以下方独立AI区域及真实审计为准；后续界面整理需修正文案。

## 8. Token与成本

4次均计入真实用量，包括3次被拒绝的返回：

|统计|实际provider usage|
|---|---:|
|输入prompt_tokens|19120|
|输出completion_tokens|4328|
|合计total_tokens|23448|
|输入缓存命中|4736|
|输入缓存未命中|14384|

按本轮核实的[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，Flash每百万tokens高峰缓存命中0.04元、未命中2元、输出8元，空闲单价为其一半。本次用量的价格估算为高峰0.06358144元、空闲0.03179072元，即约0.032—0.064元。**只是按公开单价估算，未读取账户余额或核对扣费账单，不是实际已核销金额。** 原审计cost_cny=null及INVOICE_NOT_VERIFIED状态保持不改。测试替身数字不计入以上统计。

## 9. 自动化和真实回放结果

准备阶段81项回归保持历史日志。本轮增加Key脱敏失败记录测试后82项通过；补齐提示词数量约束及“3条仍拒绝”回归后，全套84项通过，见alignment_tests.log/xml。首次诊断测试有一项本机HTTP被沙箱权限阻止，原日志保留，允许回环后重跑成功。

真实验收回放独立确认：1个注册案例、4次官方调用、1次完整验证成功、3次拒绝；成功5条发现逐项重放一致、8项篡改负例拒绝。真实回放不使用测试替身，不产生新的上游调用或训练。

验证器、原S1.1证据检查、原P0报警条件和容差均未放宽。没有因为真实返回失败而删除负例或将失败统计为通过。

## 10. 文件完整性

原8992基线、S1 572（包含已验收S1.1的5个历史授权迁移）、S1.1 717、补充53项均重新核验，意外变化/缺失/验证错误为0，unknown_files=[]。见before/final_historical.json。

准备阶段S2封存1013条全部检查：除本轮两个明确登记的S2源文件更新外，其余匹配，意外变化/缺失/验证错误为0。runtime.py和explanation.py的原始字节及中间诊断版本已备份；alignment_change.json记录原/新SHA256及validator_ast_identical=true。原1013清单及封存seal没有改写。

本轮新增测试、诊断记录、真实调用快照和报告使用独立文件清单。P0、模型/校准、原实验数据、七页、frontend/dist、8768及旧报告未改。本报告存放在新批次内，根目录准备报告保持原封存内容。

## 11. 复现与停止

当前用户启动的8769后端已正常运行，保留终端即可。再次点击同一会话同一context成功分析会复用原成功结果；该响应显示原请求耗时，不应当作一次新的网络延迟测量。重启或创建新context会产生新请求，需注意费用和限流。

仅本地重放本报告真实产物（无网络、无新模型推理）可运行：

```powershell
$env:PYTHONPATH = 'D:/广西人工智能大赛/src'
$replay = Join-Path (Get-Location) ('artifacts/ai_s2/replay_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $replay
Copy-Item -LiteralPath 'artifacts/ai_s2/real_20261116_162851/replay_acceptance.py' -Destination (Join-Path $replay 'replay_acceptance.py')
& 'D:/广西人工智能大赛/.research/venv-tep/Scripts/python.exe' -B (Join-Path $replay 'replay_acceptance.py')
```

完整自动化复现沿用新唯一S1_ACCEPTANCE目录运行pytest s1_tests s1_1_tests s2_tests，不使用真实Key调用；具体环境命令见准备版README。不要为复现删除旧证据或重建原保护基线。

本次只证明单个D3案例、当前官方模型及该严格结构化合同的真实闭环。不能据此宣称所有运行、所有模型版本或自由自然语言输出均可信。仍未提供流式生成、现场控制、动作推荐、确定根因或多功能自动闭环；8768在线兼容性不在本轮范围，保持未触及。

阶段到此停止，提交审核，不自动进入S3。
