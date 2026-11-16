# CausalVerse 第三阶段 P0-04：Action / Delta真实预测、联合区间与支持审计

日期：2026-11-15（Asia/Hong_Kong）。唯一实施范围为P0-04，P0-03已由用户验收通过。

## 交付结论与研究失败

本阶段已恢复两套冻结20成员集成，实际调用原ConditionalPredictor.predict，并恢复原联合校准区间、原ActionSupport及全部四候选机制分歧审计。实际新增测试 **178 passed in85.30s**，JUnit178项、0失败、0错误、0跳过。

Action240条件、Delta240条件，共480组；全部六时域、三个目标的均值、联合上下界及四候选均值与原档案最大绝对误差均为 **0**，成员分歧及候选标准化极差误差也为 **0**。保留每条件20×6×3主成员输出及4×20×6×3候选输出，未删成员或按识别候选加权。

屏蔽预测档案和支持审计档案、截去5400秒之后的公开轨迹数组并禁止未来truth/values等键后，另外480组预测仍独立完成、与主计算逐元素完全一致；比较全部UNAVAILABLE，没有补用其他结果。

**计算重放通过，不代表干预可信：** Action保守支持审计仅2/240通过、238/240拒绝；Delta仅12/240通过、228/240拒绝。两条路线全部240/240联合区间超出原宽度门槛。所有480组优化授权恒false，可靠性失败完整保留。没有生成最优动作排序、建议或控制接口。

累积保护7509项最终全部匹配，原有业务源码修改数量为0。没有实施P0-05、修改前端/server或启动/重启网站。**完成P0-04后停止，提交本报告等待审核。**

## 新增文件及逐项交付入口

|新增路径|实现说明|
|---|---|
|src/causalverse/ai_runtime/prediction_runtime.py|固定合同准入、Action/Delta三动作真实预测、全部成员输出、独立状态、结果追踪落盘、计算后专用原档案对照|
|src/causalverse/ai_runtime/calibration_loader.py|注册表只读加载对应原joint/actionwise半径和协议尺度，调用原intervals，在线只输出joint界限|
|src/causalverse/ai_runtime/support_runtime.py|严格恢复全部成员及Base；恢复原ActionSupport支持参数；真实成员std及四类候选完整预测/极差审计|
|tests/test_ai_prediction_replay.py|160个同历史三动作批次主/屏蔽双重计算，以及损坏临时参数、合同/命令、支持域、分歧、Base及校准专项测试，共178项|
|AI_PHASE3_P0_04_REPORT.md|本报告|
|artifacts/ai_p0_acceptance/p0_04_20261115_223237_9b309664/|本阶段唯一证据目录，所有新结果及负例仅写此处|

完整新增文件路径、大小、SHA256见本批次 `new_files_inventory.json`，该清单自身不作递归哈希。没有修改P0-01至P0-03模块、测试、报告或证据，也没有提前新增P0-05通用网关、展示或工作流文件。

主要证据文件：

- `parameter_structure.json`：Action61、Delta121、support3、candidate880数组的实际键、shape、dtype、有限性、参数SHA256、版本和原校准值；另含实际intervals参考结构。不是凭报告推断参数结构。
- `prediction_index.json`：160份主计算NPZ的实际路径、SHA256、主成员/候选成员shape，与每条模型路线和同历史输入对应。
- `replay/<inference_id>/result.npz`：主members(3,20,6,3)、mean/lower/upper/std(3,6,3)、candidate_members(3,4,20,6,3)、candidate_means(3,4,6,3)。普通及屏蔽两次计算均完整保留。
- 同目录 `result.json`：对应三个条件的五类状态、真实命令/时刻/父谱系、模型版本、参数/校准/支持哈希、数值输入/源摘要/推理身份、Bootstrap种子、实际耗时及NPZ哈希。
- `all_condition_results.json`：480个主验收条件的计算/合同/支持/宽度/授权状态、全部拒绝原因、分歧、joint和actionwise审计值。
- `comparisons/`、`masked_comparisons/`、`guards/`：160批次逐动作误差、支持一致性、UNAVAILABLE证据、未来数组屏蔽键访问及禁止调用记录。
- `identity_evidence.json`：80个规范父历史的真实run/split/parent/snapshot、六个观测时刻、动作前command、源摘要和输入哈希；三臂谱系和完整公开前史由原读取器交叉验证。
- `retained_reliability_failures.json`：全部480条支持或宽度失败，不将它们从交付中删掉。
- `tests_attempt1.xml`、`pytest_attempt1.log`：完整178项实际运行日志，无失败轮次被覆盖。
- `tmp_attempt1/`：损坏参数副本的拒绝文本、非法合同、早期历史尖峰/成员分歧、候选审计、Delta Base独立数组与20个Base调用证明、原始joint参数及SHA256。所有负例保留。
- `acceptance_summary.json`、`summary.log`、`summarize_acceptance.py`：实际480条件汇总、原函数调用、结构核验及完整环境。
- `precheck_initial.json`、`protected_expected.json`、`hash_diff_delivery.json`、`audit_protection.py`：本阶段写前实测摘要、7509项固定期望、交付全量复查及独立核对代码。

## 原始输入、身份和时间合同

复用原Registry、IdentityStore、ObservationReader、ObservationContext、InferenceRequest/validate_request、validate_observations、trace_admission、确定性序列化/哈希及P0-02数值输入hash函数，没有重写既有注册或数据身份功能。

从原数据日志选择test的80个a0规范历史，每个20种子×4背景，对同一合法历史分别计算delta=0/1/5，持续120秒。240条件不是240独立种子。两模型各覆盖全部240条件；并没有根据背景、真实IDV或P0-03 Top1选择模型权重。

历史只能是5340/5350/5360/5370/5380/5390秒的6×7，顺序T9/C21/P7/L8/F6/U10/U4；固定起点5400，目标T9/C21/P7，horizons=10/30/60/120/300/600。as_of<5400返回WAITING，不补齐未来。非法动作/起点/时长/时域均拒绝。

原读取器每次从manifest、data_log、protocol和实际raw/observed校验真实身份、split、snapshot_id、parent_run_id、源文件SHA256，比较同snapshot三动作的完整0..5399秒公开观测/控制摘要及原command，不仅凭seed或文件名推断相同历史。

command必须显式存在，并与data_log.command_before、observed.command、raw.command_before[5400,9]一致；不能退回ConditionalPredictor的可选命令默认值。5390秒U10不是5400秒原动作前command，未用其替代。command+delta须位于[0,100]。

原读取器物化的公开原始观测先按服务器as_of截断，再选固定六行；只索引动作前command，不读取隐藏阀位/RNG/未来a0值作为特征。文件整字节SHA256可以覆盖完整档案，但这不是将其未来数值输入模型。专项测试进一步将公开原始t/XMEAS/XMV/command_before数组限制到5400秒及以前，完全屏蔽observed.values/delta_values/truth，预测不变。

## 参数恢复及真实调用

Action原参数61数组：bootstrap_seeds(20,20)，每成员model_mean/scale(104)、model_coef(105,18)。Delta原121数组，除上述字段外，每成员另有base_mean/scale(33)、base_coef(34,18)。support的lower/upper/scale各(7)。candidate_support原880数组，覆盖Action/Delta×[0,4,11,14]×20成员，Delta候选同样保留自己的Base。

每项均通过原Registry的固定SHA256、依赖、精确键/shape/dtype/有限性/正尺度检查；恢复函数再逐一检查0..19全部必要键和真实shape。每成员构造自己的ConditionalPredictor/Ridge并赋冻结参数，不共享Action与Delta回归器，不重新fit。原Bootstrap种子完整记录，不用其重新采样或删成员。

实际执行原ConditionalPredictor.predict(history,delta,command)，按原np.array收集20成员并做原mean(0)/std(0)。Action保持相对末历史值的响应定义；Delta保持学习到的不动作Base加配对增量，delta=0沿原逻辑只调用Base。

Delta独立专项测试记录全部20个不同Base回归器被调用、增量回归器调用0次；输出与直接Base.predict(history_features)+末历史目标值逐元素完全相等。该证明不读取未来a0真实轨迹。

参数对象只读加载后可复用，每次请求仍校验相关正式参数文件字节；没有结果缓存，cache_hit=false。复用参数对象不等于用历史预测替代本次计算。

## 原joint校准恢复

尺度来自原protocol.mae_limits并要求精确为[0.25,0.5,5]。只读原calibration_action/calibration_delta注册项，调用原intervals函数；输出始终使用其joint返回值。actionwise仅作为审计元数据保留，不按动作选择更窄区间，不使用PI半径。

|模型|原joint半径|全宽T9 / C21 / P7|原宽度门槛|宽度结果|
|---|---:|---|---|---|
|Action|5.787873695670726|2.8939368478 / 5.7878736957 / 57.8787369567|1 / 2 / 20|全部超限|
|Delta|5.971070267917241|2.9855351340 / 5.9710702679 / 59.7107026792|1 / 2 / 20|全部超限|

lower=mean−q×scale、upper=mean+q×scale、full_width=2q×scale。480条件的上下界均与intervals_action_test.npz或intervals_delta_test.npz原显式joint数组相等，误差0。joint和校准文件SHA256前后不变；三个动作的joint半径/全宽不因选择动作而改变。没有重新calibrate、计算新校准分数或修改覆盖/宽度历史指标。

## Support与AUDIT_ONLY候选分歧

恢复原ActionSupport及lower/upper/scale，调用原check检查完整六行七变量、支持范围（原3×scale扩展规则）、command饱和、动作/时长和六个时域。分歧真实计算为max(std(20成员预测)/[.25,.5,5])，不硬填0。每个时域都有检查记录。

候选审计对四候选全部20成员实际调用同kind原predict，先求每候选均值，再调用原candidate_disagreement计算跨候选、六时域、三目标的最大标准化极差；>1继续保守拒绝。没有用真实IDV或诊断Top1挑选候选。完整候选成员、均值、极差和拒绝原因全部保存。

candidate_audit_status恒AUDIT_ONLY。直接有限时域回归不传PI递归radius，不计算或虚构谱半径“通过”，其标记为NOT_APPLICABLE_DIRECT_FINITE_HORIZON。IDV14原PI递推稳定性问题仍是原研究限制，不能因为直接预测重放一致就宣称已解决。

五类状态按每动作独立输出：

|概念|本次含义与结果|
|---|---|
|computation_status|480/480 COMPLETED，仅指模型算出了数值|
|contract_valid|480/480 true，仅指原固定输入/身份/动作合同合法|
|support_status|Action2通过/238拒绝；Delta12通过/228拒绝，含成员及事后候选分歧|
|uncertainty_status|480/480 INTERVAL_TOO_WIDE；在线coverage_status=NOT_EVALUATED_ONLINE，不伪造当前覆盖保证|
|optimization_allowed|480/480 false，包括支持通过的14条件，均未获动作授权|

原始主成员分歧导致Action28、Delta2条件拒绝；加入候选审计后最终拒绝率分别238/240=99.17%、228/240=95%。原因计数可以重叠，不能相加当独立条件。支持通过不抵消宽度失败，可靠性失败也不是数值重放失败。

## 480条件数值与独立计算验收

固定测试20种子×4背景×3动作，每路线240条件、两路线480。主计算共有9600个成员预测（每个6×3）、38400个候选成员预测；集成均值8640个标量，两个界限各8640个标量。480份完整mean(6,3)、member(20,6,3)均保留，没有挑选时域、目标或稳定成员。

|对照项|Action最大绝对误差|Delta最大绝对误差|结果|
|---|---:|---:|---|
|集成mean|0|0|全部匹配|
|joint_lower|0|0|全部匹配|
|joint_upper|0|0|全部匹配|
|四候选均值|0|0|全部匹配|
|主成员标准化分歧|0|0|全部匹配|
|候选标准化极差|0|0|全部匹配|
|原主支持判断/原因|逐项相同|逐项相同|全部匹配|
|最终保守支持判断/原因|逐项相同|逐项相同|全部匹配|

容差固定rtol=atol=1e-12；实际所有差均为0。比较器依据服务器日志中的seed/背景/动作标识定位原参考，标识仅用于计算后离线对照，不参与模型特征或成员选择。只请求参考prediction/joint界限/分歧等必要键，不把intervals.truth、真实分支结果输入模型。没有重新计算或宣传新的独立性能指标。

原档案没有逐成员预测参考，因此不能声称“逐成员与历史成员数组已比对”；本次明确保存所有成员结果，以原predict调用、完整性/实际调用次数、原集成均值一致及Base专项测试证明成员恢复。

160个同父历史/模型批次均再次屏蔽intervals_*/predictions_*及support_results/candidate_disagreement参考文件，同时限制未来公开数组、禁止truth/values/delta_values/rng/阀位等键。第二次真实预测对冻结输出的读取尝试为0，之后单独比较才UNAVAILABLE；额外480组所有主成员、均值、上下界、std、候选成员和均值与普通计算完全相等。没有移动、修改正式参考或使用其他文件fallback。

两轮主/屏蔽重放的原函数调用实测为ConditionalPredictor.predict96000次、Ridge.predict128000次、ActionSupport.check5760次；记录见guards，包含主模型和所有候选。fit/fit_transform/calibrate/conformal_radius/控制/TEP/simulation拦截覆盖参数对象初始化和实际计算，禁止调用列表为空。

## 专项测试、失败保存和命令

178项包括160个完整三动作批次与18个专项：Action/Delta缺成员、错误shape、非有限参数；非法delta/duration/origin/horizons；command越界/缺失；完整历史早期尖峰、成员分歧、候选分歧；Delta Base独立计算；两模型joint半径不变及动作无关；提前时钟与非法动作持久化拒绝。损坏参数只作用于内存临时副本，尖峰/分歧只作用于测试数组，不改正式NPZ/原始数据。

所有负例有拒绝或审计JSON；Base还保存20×6×3直接计算数组。没有删失败测试、隐去不支持条件或放宽支持域。retained_reliability_failures.json保留480条当前支持或宽度失败，与首轮178项测试通过的工程结论分别表达。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$env:CAUSALVERSE_P004_EVIDENCE=(Resolve-Path artifacts/ai_p0_acceptance/p0_04_20261115_223237_9b309664).Path
& .\.research\venv-tep\Scripts\python.exe -B -m pytest tests/test_ai_prediction_replay.py -p no:cacheprovider --basetemp artifacts/ai_p0_acceptance/p0_04_20261115_223237_9b309664/tmp_attempt1 --junitxml artifacts/ai_p0_acceptance/p0_04_20261115_223237_9b309664/tests_attempt1.xml -q
```

实际首轮178 passed in85.30s，没有失败轮次。复现须使用另一个唯一批次，不能重用本目录覆盖证据。未运行整个历史tests、原仿真测试或正式实验生成脚本。

环境为原Python3.12.14、NumPy2.4.6、pytest9.2.0，无安装/升级依赖。 elapsed_ms是单调时钟记录的准入/读取/模型计算/支持审计耗时，不是播放假进度；不承诺现场实时性能。没有请求或重启8768，没有改数据库、控制参数、前端或历史报告。

## 累积保护与来源限制

本阶段保护范围为M06418 + M0报告1 + P0-01全部77 + P0-02全部785 + 用户保留副本1 + P0-03全部227 = **7509**。P0-03清单226条与清单自身均纳入，实际清单SHA256为用户提供的b271f1dd7a10a4b5fdaa1233c600a83135d688e147860baa58b3c72d975ea8a1。

P0-03报告SHA256核对为 `10b3293b9453258349e04f9eb71fd9be89450c6db64856788c4c230a1fd99043`。保留副本沿用P0-03已确认身份和原摘要相同的SHA256，未删除、改写或当作本阶段新增。

写前实测7509项，差异0，耗时10.15秒；开发/测试后交付逐项完整复查7509项，差异0、缺失0、读取期间变化0，M0机器清单摘要有效，耗时13.62秒。所有期望值从原清单交叉合并，保存在本批次protected_expected.json，不更新任何旧基线掩盖变化。原参数、校准、协议、所有正式数据及P0-01/02/03源码/报告/证据均保持字节不变。

原638重建范围中30项缺早期历史逐文件哈希的证据缺口仍然存在；当前累积匹配不补造过去的内容证明。文件校验不等于新现场泛化、概率保证或因果识别证书。

## 未解决事项与停止边界

本阶段没有未通过的关键计算重放、joint恢复、支持审计一致性、独立性或保护验收项。原可靠决策问题仍未通过：区间全部过宽、候选分歧导致高拒绝，原IDV14问题未被本阶段解决。即使14条件支持审计通过，也不获得优化或执行资格。

本地入口只接受已注册历史和原固定条件，不支持任意动作/时长/起点、滚动预测或分类加权。coverage没有在线重新评价，不把20种子历史覆盖包装为当前概率。真正改善宽度、支持和现场迁移仍需独立新研究协议与授权，不能靠本次接口实现改变研究门槛。

若后续明确授权P0-05，再处理统一跨阶段追踪、计算后档案对照编排和独立附加证据展示；原8768/七页保持不变，除非另行授权。**本次未创建P0-05文件、未启动任何页面或服务，到此停止等待审核。**
