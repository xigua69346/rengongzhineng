# CausalVerse S2收尾优化、验收与版本封存报告

日期：2026-11-16（Asia/Hong_Kong）。本轮只完成S2展示收尾与备份，不进入S3。没有再次调用真实DeepSeek，没有修改后端验证逻辑或原数值算法。

## 1. 本轮结果

修复“DeepSeek尚未接入”过时文案，新增独立的当前API配置与结果来源说明；将5类分析改为可读卡片，原JSON和哈希放入折叠详情。原84项S2测试通过，新增10项展示测试通过。三个指定视口完成成功/拒绝/未配置状态以及证据交互、长文本、导航检查，最终完整截图已取得，首次截图失败仍保留。

独立备份已建立在用户指定公开仓库：https://github.com/xigua69346/rengongzhineng 。原S2分支和标签已推送并回读；收尾界面提交为fd1c236fc7160de4fa0cdf8c2785ac39d2b18843，收尾发布的最终提交与标签回读见同目录git_publication.json。未改远程main、未强制推送、未改变公开权限。

本轮只修改4个8769展示文件，12194项累积保护集合中其余12190项未变。原始实验数据、模型、校准、P0源码、S1.1验证器、DeepSeek验证器、七页、frontend/dist、旧报告及验收证据均未修改。

## 2. 已阅读依据与现状

已阅读真实API报告artifacts/ai_s2/real_20261116_162851/AI_PHASE3_S2_REPORT.md、根目录准备版AI_PHASE3_S2_REPORT.md及AI_PHASE3_S1_1_REPORT.md。真实验收以real批次为准，根目录“等待Key”报告未改写。

DeepSeek原功能保持：真实PCA/Threshold检测→同context事实→官方模型结构化证据选择→S1.1及解释合同验证→后端数值/中文释义回填。中文不是未经验证的模型自由叙述，评分不是概率，候选不是确定根因，optimization_allowed=false。本次不重新开发API接入或改变这些边界。

## 3. 展示修改清单

|文件|修改原因|
|---|---|
|src/causalverse/evidence_s2/console/index.html|“DeepSeek已接入”文案；配置状态与结果来源分开；历史选择及当前模式；增加同页证据/AI锚点导航|
|src/causalverse/evidence_s2/console/ai.js|5类可读卡片；真实历史成功/拒绝/未配置记录回放；保留原请求时间、原耗时；详情折叠；不将缓存或历史成功宣称为本次新增成功|
|src/causalverse/evidence_s2/console/app.js|本地模型就绪文案不再错误声称无Key；仅增加页面就绪事件供AI配置状态检查|
|src/causalverse/evidence_s2/console/style.css|工业风卡片、两列/单列断点、长文本与JSON换行、状态徽标、折叠详情及导航样式|

修改前原字节保存于before/，原SHA256见ui_before.json；4项完整前后摘要见protection_after.json和Git backup_metadata/closeout_changes.json。没有修改任何后台Python业务文件。

新增s2_closeout_tests/test_view.cjs为无依赖Node展示测试；network_guard.py仅在本次pytest进程中阻止外部socket连接。验收辅助脚本和全部新报告位于artifacts/ai_s2/closeout_20261116_173046/。完整文件清单及SHA256见new_files_inventory.json。

## 4. 接入、配置、调用与历史状态

主视觉明确：DeepSeek已接入，负责证据选择与结构化分析，数值及中文释义由后端验证回填。当前API配置从原后端/api/ai/session读取，能显示已配置、未配置或无法确认；配置状态不等于调用成功。

默认进入“已保存真实结果（历史回放，不产生费用）”，来源栏明确标记历史，并显示原请求时间与原请求耗时。历史VALIDATED不代表当前实时调用成功。用户当前会话模式仍保留，但必须有匹配的D3快照、配置完成且非dirty才可显式请求；本轮没有使用该按钮发起付费调用。

原用户8769进程在验收期间已退出，刷新得到连接拒绝。为保证不产生费用，本轮启动不携带Key的8769预览进程，所以“当前API未配置”是真实状态，不是拿旧失败记录推断当前配置，也不代表删除用户终端中的Key。后续需实际调用时，由用户在配置环境的终端启动原S2入口即可；本轮预览无需Key。

后台缓存返回记录可能包含api_call_made=true和原耗时。新展示不据此默认声称新增实时调用；时间旧/缺失时标为已有记录，近期返回也仅称“本次获取的后端记录”，提示核对原请求ID及时间。

## 5. 五类卡片与证据详情

展示异常指标分析、报警证据分析、检测器分歧分析、时间变化分析、根因证据不足说明5类卡片。每张包括：标题、原后端回填结论、引用观测时刻、原始标量/Boolean、独立来源证据数与事实引用数、原Claim验证状态。

数值保留原精度，例如T²=57.86709703253733；Boolean保留True/False并加报警说明。没有将两次事实引用误标为两个独立来源。根因不足卡片保持INSUFFICIENT_EVIDENCE，不能因为整个返回VALIDATED就改成根因已验证。

fact_id、evidence_id、pointer、SHA256/payload_sha256及原JSON全部放在“查看完整证据”。调用审计、请求ID、上下文、usage、来源文件哈希等另置可展开区。界面使用textContent，未引入未经验证HTML或修改任何Claim内容。

回放数据是已封存真实API审计的公开字段投影，分别绑定源文件SHA256：

- 成功：c2a0ac1ae0fdadfba8a9d5c5a729a936，原VALIDATED、5项发现。
- 拒绝：9115b6fe6d5804e14ed0101aaf4afc25，原REJECTED/AI_REFERENCE_LIMIT，不显示为AI结论。
- 未配置：准备阶段missing_key_live.json中的原NOT_CONFIGURED，未调用API。

没有采用模拟分析文本，未上传私有运行映射、Cookie owner或Key。历史上下文与当前所选实验没有被拼成同一身份；回放与当前会话通过来源选择明确区分。新回放只是展示已保存记录，不替代后端对新增返回的验证。

## 6. 浏览器验收

使用真实in-app Chromium，设置CSS视口1920×1080、1366×768、390×844。修改前截图before_*.png，修改后9组状态截图after_*_VALIDATED/REJECTED/NOT_CONFIGURED.png，最终完整截图final_ready_*.png，最终展开截图expanded_ready_*.png及同名/相关DOM、JSON检查记录均在browser/。

|检查|1920×1080|1366×768|390×844|
|---|---|---|---|
|真实历史成功5卡、拒绝、未配置|通过|通过|通过|
|原数值、时间、证据数量及状态|通过|通过|通过|
|JSON展开/收起|通过|通过|通过|
|长文本和哈希无横向溢出|通过|通过|通过|
|根因不足及授权false|保留|保留|保留|
|锚点导航和页面滚动|通过|通过|通过|
|最终完整截图和展开截图|已保存|已保存|已保存|

最终DOM中AI卡片数均为5，JSON横向溢出false，文档scrollWidth分别1905、1351、375，不超过对应视口；锚点跳转后AI区域距视口顶部约16px。JSON在自身滚动区内，原始值未裁剪成省略数据。console warning/error=[]。

注意：after_results.json早期cards字段使用页面全部三级标题计数，不能当成AI卡片数量；实际AI卡片数以final_interactions.json中的aiCardCount=5为准。

截图工具曾在页面重载未完成、整页或大裁切区域时返回Unable to capture screenshot，失败原记录保留。等待页面初始化完成后，三个final_ready和expanded_ready均成功取得；没有把失败写成通过，亦未用HTML/JS静态检查代替浏览器。截图是CSS视口/真实浏览器全页捕获，不宣称手机真机验收。

## 7. 测试与零新增API调用

原84项S2回归：84通过、0失败、0跳过，见tests_original.log/xml。测试进程Key置空，额外network_guard只允许回环socket；未改变用户服务环境或原测试源码。

新增Node测试10项全部通过：真实档案与源SHA/analysis一致；5类标题；数值/时刻无舍入；事实数与来源数分开；根因不足状态；历史与缓存不冒充实时；近期返回也不直接宣称新增调用；拒绝/不可用不展示有效卡片；历史、dirty、忙、D511、未配置均不能触发实时调用。早期9项日志和最终10项日志分别保留。

本轮新增真实API调用为0。api_set_integrity.json对比写前封存和写后实际官方审计集合：5条→5条，new_calls=[]、changed_records=[]。最初核验脚本误把旧报告中4次人工验收样本当成所有历史记录，触发断言；额外第5条在写前清单中已封存且哈希相同，发生于此前阶段，并非本轮调用。旧报告与审计不改写。本轮不重新核算或制造费用。

## 8. 文件保护与敏感信息

累积读取原8992、S1 572、S1.1 717、补充53、S2准备1013、S2真实854等原清单，以验收后的版本顺序合并现有预期，去重12194项。保留全部原清单，不从当前内容重造旧预期。

写前12194项匹配、未知文件0。写后12194项已检查：只出现4项明确授权的S2展示修改，其他12190项原样；意外变化、缺失、不可读、验证错误及未知文件均为0。见protection_before.json、protection_after.json。校验脚本末尾固定4次API的断言失败与文件哈希结果分开记录；以verify_api_set.py的集合比较作为无新增调用证明。

Git备份采用用户确认范围：源码、测试、18份冻结模型/校准参数、报告、脱敏成功/失败证据和完整历史哈希。大型原始轨迹、私有映射、虚拟环境、node_modules、.env、凭证和私钥不上传。明确允许列表逐文件核对原SHA256，再扫描凭证模式，结果0项；没有读取环境Key或导出Git凭据。

备份复制283个允许列表文件；既有.gitignore排除5个可再生成egg-info文件。原始备份提交实际281个Git文件（278个原文件及3份备份元数据）。verify_git_backup.py直接读取Git blob，确认278份原文件提交字节与原SHA完全一致，18个模型参数均入版本。5个egg-info的本机副本仍保留，未冒充已上传。

## 9. Git与GitHub版本信息

原工作目录没有.git，因此没有可读的本地分支或未提交diff；封存哈希检查没有发现未知归属修改。没有擅自将整个目录初始化并上传13.5GB数据，而在本批次version_repo/建立独立、可审查的备份仓库。原项目工作目录结构不变。

指定仓库为公开仓库xigua69346/rengongzhineng。连接器属于yeziheng586-jpg且无写权限；本机GCM最终缓存两个账号，Git远程明确使用xigua69346。用户启用7890代理后本机Git推送成功。没有删除其他账号、修改全局代理或仓库权限。

|版本|分支/标签|提交|
|---|---|---|
|原S2备份|backup/s2-real-deepseek-20261116 / s2-real-deepseek-20261116|9e828050399eff3506c5806638eca2e67d7c4765|
|收尾界面实现|s2-closeout-20261116|fd1c236fc7160de4fa0cdf8c2785ac39d2b18843|
|收尾验收封存|同分支，另标记s2-closeout-20261116标签|最终文档提交及远程回读见git_publication.json|
|用户原main|main|c3439f36ea3de6b37e3ab4f9992e4f7970aa4c14，保持不变|

原备份先提交、建标签并推送，再进行界面修改。收尾实现为单独提交，后续验收材料另一个提交；不覆盖历史。原项目没有可恢复的既有Git历史，备份为独立根提交，未伪造其与main的祖先关系。

可在GitHub按标签查看原版与收尾版：

- https://github.com/xigua69346/rengongzhineng/tree/s2-real-deepseek-20261116
- https://github.com/xigua69346/rengongzhineng/tree/s2-closeout-20261116

本地另交付s2-closeout.bundle（SHA256在最终清单中），可离线克隆源代码版本。大型数据和私有映射依然是本机保护数据；这不是含全部13.5GB原轨迹的异地灾备，不宣称离线克隆后无需原数据就能重新运行实验。

## 10. 使用与回退

当前无Key预览在http://127.0.0.1:8769/，默认历史回放可直接查看三种真实状态，不花费Token。后续需要实时功能时，只在用户配置Key的终端启动原S2后端；本轮不进行该操作。不要修改或启动8768。

复核本次展示测试：`node --test s2_closeout_tests/test_view.cjs`。原84项测试需新唯一S1_ACCEPTANCE目录，命令与本次日志一致，建议继续启用`-p s2_closeout_tests.network_guard`并清空该测试进程Key，不覆盖正式测试目录。

回退请先在新目录克隆指定仓库或本地bundle，checkout `s2-real-deepseek-20261116`，核对清单后再将所需展示文件恢复到项目；不要对当前项目执行git reset --hard，也不要覆盖原始数据/模型/历史证据。原目录本身仍无.git，Git操作应针对version_repo或新克隆目录。

## 11. 限制与停止

本轮验证历史回放展示及原84项回归，没有重测或重新调用付费API。当前预览未携带Key，因此“API已配置”的实时分支由原后端配置接口和新增状态逻辑保留，未拿模拟配置冒充新的真实已配置调用。当前回放档案是允许列表、源哈希绑定的历史样本，不是新用户任意上传结果，也不是新的后端可信度判定。

现有单机会话、持久预算、自由自然语言验证等研究边界保持；不修改原不确定性门控，不输出优化优势、动作排序或控制建议。源码回退不替代原始数据离线备份。

本轮到版本封存与报告交付为止，不进入S3，等待审核。
