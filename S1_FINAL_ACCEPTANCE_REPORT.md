# S1补充验收最终报告

日期：2026-11-16，Asia/Hong_Kong。仅执行S1补充验收；没有接入DeepSeek、读取或配置API Key，没有进入S2。原有源码、模型、数据、校准、前端七页、frontend/dist和8768均未修改。

## 1. 结论

真实Chrome浏览器的1920×1080、1366×768、390×844三个CSS视口已实际操作D3和D511，保存21张原始浏览器截图及对应可访问性树、时间记录。完成8个新上下文的后台追溯，共44项证据归属、公开载荷哈希和快照哈希匹配。

原8992项保护记录与572条封存记录均逐文件复核通过，没有重新生成或替换基线。8768只读GET仍被目标拒绝连接，记录UNAVAILABLE，在线兼容性验收移交S4。

**本次补充验收执行完毕，但不是全部项目通过；暂不建议将S1判为无条件满足S2前置验收。** 移动端长原因文本溢出、favicon 404和选择条件变化后旧快照未提示待更新的问题均保留，未擅自修复。当前Claim Schema只支持计算可用/证据不足两类声明，尚不足以安全承载后续完整诊断解释；本报告仅提交补充设计。是否接受这些遗留项及批准后续工作，由用户审核决定。

## 2. 证据目录与验收方法

独立批次：`artifacts/ai_s1_supplement/s1_final_20261116_133423/`。上次受工具终止的记录和核验结果保留；本次重试追加在 `retry/`，没有覆盖正式S1证据。

- `verification_before.json`：上次已完成的原基线及封存记录检查，结果本轮重新读取确认。
- `retry/verification_after.json`：本次浏览器操作后的全量逐文件复查。
- `retry/01_*.png`至`retry/21_*.png`：21张真实Chrome窗口原始截图，无合成、无重绘、无裁切替代。
- 对应同名`.txt`：当时实际可访问性树；部分动作后树更新晚于截图，最终结果以完成后的截图、上下文及后台验证联合判断。
- `retry/operations.json`：截图时间和原始像素尺寸，时间使用UTC，换算香港时间为13:38—13:49。
- `retry/operation_log.md`：人工操作步骤、首次失败及恢复说明。
- `retry/provenance_verification.json`及`retry/provenance_verification_network.json`：后台快照、证据、P0元数据/数值产物追溯。
- `retry/8768_read_only.json`：首次沙箱网络拒绝记录；`retry/8768_read_only_network.json`：允许回环访问后的真实连接拒绝记录。
- `verify.py`：读取原正式保护文件进行验证的独立脚本；`retry/read_only_checks.py`：只读HTTP和既有快照追溯脚本。
- `supplement_inventory.json`：本次新增验收文件与本报告的SHA256清单；清单自身摘要见`supplement_seal.json`。

使用现有Chrome和已提供的computer-use工具，通过真实下拉、输入框、按钮、详情展开和滚动操作，不新增依赖、不注入模拟模型数据、不以HTML或JS语法检查代替浏览器验收。

三个尺寸由Chrome开发者工具Responsive视口的Width/Height明确设定。显示采用Fit to window，截图保留尺寸工具栏。**截图文件本身为1429×1039的浏览器窗口捕获，内含按比例显示的指定CSS视口，不是1920×1080物理屏幕截图，也不是手机真机测试。** 对布局的判断基于实际浏览器渲染与人工观察，没有声称覆盖所有浏览器和移动硬件。

## 3. 浏览器实际操作结果

|CSS视口|D3实际操作|D511实际操作|界面观察|
|---|---|---|---|
|1920×1080|5400秒、1800秒窗口，检测及三种识别INFERRED；展开检测详情|选择D511并重新计算；三种识别及Action/Delta INFERRED；滚动并展开Action|双列正常；结果、哈希、候选及预测门控可见；旧快照保留行为单独记录|
|1366×768|5400秒真实计算；再改5399秒，检测20时刻可用，三种识别WAITING|实际打开案例列表并选择第二个匿名案例，重新创建上下文|纵向滚动可访问内容；未见桌面卡片遮挡；数值详情原始JSON形式，交互仍偏研究控制台|
|390×844|5400秒真实计算；滚动查看检测及识别卡片、展开检测详情|5400秒计算、查看识别与两路线预测、展开Action；5399秒重算并检查五项WAITING|单列正常，长哈希换行，JSON在自身区域滚动；UNAVAILABLE长原因存在横向越界，布局项不完全通过|

本次浏览器产生并核验的上下文：

|视口/场景|数据链、as_of|context_id|
|---|---|---|
|1920完整|D3，5400|843509e9aa8a677f231a63e6770fdc53|
|1920完整|D511，5400|51527ce312e0fbfafa0eeb4458d796f8|
|1366新案例|D511，5400|f3e7a237a7b71f51b880593f354d3414|
|1366完整|D3，5400|b2707d7a6f0bdaddcf8885166b3e78dd|
|1366等待|D3，5399|83a2cb69ea27702dc1dae574f1962a15|
|390完整|D3，5400|3ef0169ed304d134ec0cad0be7ef84db|
|390完整|D511，5400|3af5ba23d6a7b69cf85848dfc8585439|
|390等待|D511，5399|924ce8b29e86ffb83868910396e79f14|

截图索引重点：02/03为桌面D3计算和展开；04为切换数据链后仍显示旧快照；05—07为桌面D511识别、预测及展开；08为控制台首次错误；09—13为1366操作；14—16为移动D3；17—19为移动D511及长原因溢出；20—21为移动WAITING。

### 3.1 状态和授权

- D3 as_of=5400真实显示21个检测时刻；5399时仅20个，没有补齐到5400。
- 三个识别方法在5399、W=1800时均WAITING；D511两条预测路线也WAITING，不显示补造结果。
- D511没有注册D3检测，检测卡片UNAVAILABLE；D3没有注册D511预测配对，预测UNAVAILABLE。不是把两条链拼成同一运行。
- 两路线的UNSUPPORTED、INTERVAL_TOO_WIDE、优化未授权均实际可见。1366第二个D511案例的Delta在Δ0出现SUPPORTED，但仍为INTERVAL_TOO_WIDE且optimization_allowed=false；支持通过没有被显示为干预授权。
- 单一候选显示“模型内单一候选”，保留“评分不是概率”和“候选不是确定物理根因”。本轮未找到/遍历全部候选歧义场景，不能把这次浏览器样本当作全部P0数值验收的重跑。

### 3.2 来源追溯

浏览器详情能展开evidence_id、context_id、model_id、model_hash、模型版本和数值/审计。公开页面没有原始运行名、原始文件路径或真实标签。后台只读检查进一步核对8个快照与私有映射的SHA256、44项证据载荷哈希、证据context归属、身份所属数据链、P0结果状态及有数值产物时的NPZ哈希。

完整预测的历史比较为MATCHED，原审计匹配为true；候选分歧仍为AUDIT_ONLY。这里验证的是浏览器这8个上下文的来源，不冒充重新验收80个D3运行或480个P0-04条件。

## 4. 未通过项与首次失败

### F01：移动端长原因文本越界

390×844，D511检测UNAVAILABLE原因`D3_41_XMEAS_DETECTOR_NOT_REGISTERED_FOR_D511`在摘要中没有适当断行，越过卡片右边界并在视口边缘被裁切。证据：17、20截图。中文正文、哈希、预测状态行及展开JSON总体能够换行或在内部滚动；不能据此把整个移动布局判为无溢出。

建议后续经批准，对原因摘要增加断行并提供面向用户的中文说明；保留原机器原因码供展开审计。不在本轮改CSS/JS。

### F02：控制台存在favicon 404

实际Console显示：`Failed to load resource: the server responded with a status of 404 (Not Found)`，来源`http://127.0.0.1:8769/favicon.ico`，错误计数1。08截图及对应树保留。后续实际计算没有观察到新增脚本异常；这不是“控制台零错误”通过，也不是冻结模型计算失败。没有清空控制台掩盖首次失败。

### F03：选择条件改变后旧快照缺少待更新提示

1920尺寸切换到D511时，选择区已是D511和新案例，右侧仍显示上一D3快照及其D3身份，直到点击重算。改变案例、as_of也有类似行为。旧快照自身context和身份没有被改写，没有观察到后端错误配对；但没有醒目的“选择已变更，当前结果为上一快照”提示，容易误读。04截图明确保存该状态。

建议后续经批准，对选择条件变化增加dirty标记、提示或清空旧结果。不要通过修改已封存快照解决此问题。

### 工具/环境失败，已保留

上一次computer-use因无法可靠识别浏览器URL而终止。本次收到用户重试授权后重置会话、重新识别当前已打开的8769页面，成功继续。两次原生下拉关闭后截图工具短暂返回`no monitor found for window`，均重新枚举现有Chrome窗口、重取状态后确认选择已生效，没有以失败截图当成通过。初次UIA按钮点击在缩放视口中未触发请求，重新观察后用真实截图坐标点击，并以新context和后台记录确认实际成功。

首次8768只读请求被沙箱WinError10013阻止，保留首次日志后申请允许本机回环访问；复查得到目标连接拒绝10061。没有以沙箱网络错误推断服务停机。

## 5. 原有文件保护复核

直接读取正式目录 `artifacts/ai_s1_acceptance/s1_20261116_102936_452b6431/protection_final.json` 的expected映射，不调用S1的基线重建流程，不从当前文件重新生成预期值。572条封存预期直接来自原new_files_inventory.json。还核对inventory_seal.json和交付时已记录摘要。

原protection_final.json SHA256：

`d55a4089a89e0472ed9b87e7e13248e07488bb1ff80982b8bda75847cfbf6923`

与原inventory_seal.json的protection_final_sha256一致，且该文件也属于原572条封存记录。原new_files_inventory.json SHA256：

`08f8c1b002173b0000aa193bfd22f9df4fc45ee6142e0506f99f05508db728f4`

与交付封存一致。原inventory_seal.json自身SHA256：`90191aca4c3833d805e229cbbb72cf78c231d89cff067aa6b64196909640112f`。

本次操作后实测输出：

```json
{
  "original_8992": {
    "expected_count": 8992,
    "checked_count": 8992,
    "changed_hashes": [],
    "missing_files": [],
    "unknown_files": [],
    "unreadable_files": [],
    "verification_errors": []
  },
  "sealed_572": {
    "expected_count": 572,
    "checked_count": 572,
    "changed_hashes": [],
    "missing_files": [],
    "unknown_files": [],
    "unreadable_files": [],
    "verification_errors": []
  }
}
```

原572条的含义是封存时文件，不把之后的新运行文件强行加入旧清单。补充验收前已出现34个封存后运行文件；本次浏览器后共150个，其中新增116个。这些均在原批准的随机运行批次目录下，逐文件路径、大小、SHA256另列post_seal_runtime_files；不覆盖原清单，不作为unknown_files静默丢弃。当前验收目录是本轮明确授权新增范围，单独登记current_acceptance_files。本报告与补充清单也属于新交付文件，不回写旧基线。

unknown扫描覆盖项目业务目录及根文件，并排除node_modules、虚拟环境、缓存等非业务生成目录；8992和572项预期文件则无论是否在隐藏目录中都逐项核对。没有将整台机器的未知文件统计成项目异常。

## 6. 8768只读检查

只GET `http://127.0.0.1:8768/`、`/api/runs`、`/api/research`。允许回环访问后的三条结果全部UNAVAILABLE，具体错误ConnectionRefusedError/WinError10061。没有启动、修改、替换、停止或重新绑定8768。

原站源码、构建文件及历史产物的SHA256仍通过；**原站在线响应兼容性尚未验证，按本次授权保留至S4**。不能把文件一致性等同于原站在线可用性。

## 7. S2前置Claim Schema设计检查：仅设计

当前knowledge.json中Claim仅有context_id、evidence_id、claim_type，claim_type只有COMPUTATION_AVAILABLE/INSUFFICIENT_EVIDENCE。validate_claim可验证会话归属、同context引用及INFERRED状态，但不能表达比较依据、数值定位、知识版本、关系证据等级或自然语言中的事实声明。它可用于S1最小状态声明，**不足以支撑完整DeepSeek诊断结构化输出**。

建议下一阶段经批准补充以下合同；本轮未修改Schema、验证器或提示词实现。

|字段组|建议字段|校验条件|
|---|---|---|
|整体响应|schema_version、context_id、snapshot_sha256、as_of、answer_status、claims、limitations|context/as_of/快照哈希必须与后端固定上下文相同；拒绝额外字段；限制长度、声明数量和嵌套深度|
|声明身份|claim_id、claim_type、evidence_refs|claim_id在响应内唯一；claim_type封闭枚举；事实声明至少一条有效引用|
|证据定位|evidence_id、payload_sha256、fact_id或后端允许的JSON Pointer、source_kind|同会话同context；哈希匹配；定位字段白名单；禁止任意文件路径及跨链证据；区分RECOMPUTED_FROZEN、HISTORICAL_ARCHIVE、KNOWLEDGE|
|数值表达|fact_ref、target/metric、unit、method、window、action/horizon等维度引用|LLM只返回事实引用，所有数值由后端回填；不得接受LLM新造数值、概率、区间或单位；索引需存在且shape/维度一致|
|解释与比较|explanation、comparison_refs、comparison_basis、relation_level|解释必须关联证据；比较对象需可比，不能跨D3/D511误配；派生差值/排序仅后端允许的确定性算子计算|
|不确定性|computation_status、contract_valid、support_status、uncertainty_status、optimization_allowed及reason_refs|这些字段应由后端绑定，不能让LLM自行裁决；optimization_allowed始终false；所有拒绝和AUDIT_ONLY标签保留|
|关系证据|relation_level、scope、knowledge_refs|VALIDATED_PATH、STATISTICAL_ASSOCIATION、CANDIDATE_RELATION、HYPOTHESIS严格区分；静态研究图不能声称当前运行重新识别；必须有相应证据等级|
|不足及冲突|missing_evidence_refs、conflict_refs、refusal_reason|WAITING/UNAVAILABLE/FAILED/REJECTED只能用于解释不足，不能支持正向数值结论；模型候选分歧应显式列出，禁止强制Top1唯一结论|
|版本追踪|prompt_version、knowledge_version及hash、model_name、request_id、validation_status|后端生成审计，不信任LLM自报模型、版本和来源；不要把未验证草稿当成最终诊断|

建议claim_type覆盖“直接证据事实、可比结果比较、候选歧义、局限性、证据不足、关系证据说明、动作未授权”，不引入可执行控制建议。claim_type允许出现某类名称不代表自动拥有相应证据。

必须增加的后续负面验证：伪造ID/哈希/来源、跨context或跨数据链引用、指向不存在的数组项、重复声明ID、无引用数字、评分改写成概率、候选改写成确定根因、把历史仿真说成现场、把预测说成未来实测、用WAITING推结论、把SUPPORTED说成已获优化授权、覆盖或缩小原区间、把AUDIT_ONLY说成前瞻校准可信度、提示注入和控制指令输出。

合法JSON与JSON Schema通过仅为格式检查，还需证据语义与自然语言一致性校验。遇到未知字段、证据冲突或语义验证失败应拒绝该声明并降级为证据不足，不能用LLM修补原数值。上述均为设计要求，没有在S1中提前实施LLM功能。

## 8. 已通过、未通过、尚未验证及风险

**已通过：** 三尺寸真实浏览器操作；D3/D511案例选择、上下文创建、检测/识别/预测展示；卡片展开；WAITING与预测门控状态；后台8快照/44证据追溯；8992+572文件完整性及原保护文件SHA256锚核对；无Key、无DeepSeek调用、无训练/校准/仿真/业务源码修改。

**未通过：** 移动端长原因无溢出要求；控制台零错误要求（favicon404）；选择条件与当前已显示快照间的明确待更新提示。当前最小Claim Schema对完整LLM结构化解释的充分性不通过，补充设计已提交但未实施。

**尚未验证：** 8768在线兼容性（UNAVAILABLE，移至S4）；真实手机触摸/软键盘与多浏览器；全量80/480研究数值重放（本轮不重复）；长时间会话、并发压力及生产安全；LLM实调、流式输出、费用和生成事实校验（未授权，不执行）。

**遗留风险：** 既有支持不足、宽区间和候选分歧全部保持；单机文件哈希不是WORM；快照索引和会话重启后不恢复；源码展示问题可能使操作者误读当前选择与上一快照；现Schema不能独立阻止所有自然语言歪曲。未见本轮模型数值或身份配对失败。

**S2条件判断：** 当前真实推理证据基础和保护核验达到本轮检查要求；S1完整无缺陷验收尚不成立。建议先审核并明确授权上述S1展示修复范围、确定S2 Claim合同及语义拒绝条件，再决定是否批准S2。未把该建议当作授权，本轮到报告交付即停止。

## 9. 复核命令

项目根目录，现有环境；输出文件必须取新名字以保留首次记录：

```powershell
.\.research\venv-tep\Scripts\python.exe -B artifacts/ai_s1_supplement/s1_final_20261116_133423/verify.py retry/verification_recheck_unique.json
.\.research\venv-tep\Scripts\python.exe -B artifacts/ai_s1_supplement/s1_final_20261116_133423/retry/read_only_checks.py _recheck_unique
```

第二条仅GET本机8768并读取已存在的8个浏览器快照，不调用新的推理、DeepSeek、训练或仿真；需要允许本机回环访问。浏览器步骤按operation_log.md手动复现，界面会追加新的S1推理证据，不覆盖旧快照。不要重建8992项预期值或更新572条封存清单。
