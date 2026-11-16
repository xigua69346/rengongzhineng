# D6 开源模板选型（2026-11-14）

## 工程检查

现有项目没有package.json、前端工程或HTTP服务。后端为CPython3.12、NumPy2.4.6，SciPy用于研究拟合；TEP Python固定提交、D2控制/快照接口已存在；检测、因果模型及机制识别分别在detection/causal/decision。现有数据接口是NPZ/JSON/CSV和Python函数，不是可直接连接的REST接口。已有Plotly离线实验图，包括D3检测和D5.1.2分析。已阅读D2适配、D3检测、D4模型、D5.1不确定性、D5.1.1干预模型和D5.1.2机制报告；优化尚未授权，D6只整合监控、研究结果和历史回放。

## 搜索与实际核查

按SCADA/HMI、工业数字孪生、P&ID、IoT遥测、React/Vue后台方向搜索。以下前三个仓库已实际浅克隆至.research/d6，核查源码、package文件、真实LICENSE和最新git提交，未只依赖README。第四个FUXA补充检查官方文档与LICENSE。演示网站访问只代表本次访问，不证明项目永远可用。Issues为公开页面检查，未进行完整漏洞审计；没有报告的issue不等于没有缺陷。

|项目/源码|官方演示/文档|技术栈/许可证实际文件|维护证据与问题|兼容性/取舍|
|---|---|---|---|---|
|[Naufaldo/Dash-Template](https://github.com/Naufaldo/Dash-Template)|[GitHub Pages](https://naufaldo.github.io/Dash-Template/)，另有本地源码可运行；未依赖在线演示可用性|Svelte5、SvelteKit2、Vite6、TypeScript；根LICENSE为MIT，版权2026 Naufaldo|固定59498e5c3f977e3ce5395ad0337528f842370670，最近提交2026-09-10；仅少量提交，公开Issues页面未提供成熟维护保证|暗色、SVG仪表、状态灯、罐位、PID面板、管线图、趋势齐全；默认每4秒随机模拟必须排除。可通过fetch接Python，无需搬入原设备store；最适合复用展示组件，尚不能称成熟工业生产平台|
|[Multidash](https://github.com/hasralgana/multidash)|[demo.dashral.com](https://demo.dashral.com)，本次网页工具访问失败，不写为运行通过|Next16、React19、Tailwind4、Radix、Recharts、Turborepo/pnpm；根LICENSE为MIT，版权2026 Hasral Techno|固定8533d52e069fdfabace1aba8eac5f4c43e516a57，2026-11-04提交转向新名Dashral；旧README/搜索存在旧地址，需注意迁移|源码完整，暗色、卡片/表格/图表可用，无工业P&ID；monorepo和Next运行时增加本项目部署成本，不采用|
|[TailAdmin免费React版](https://github.com/TailAdmin/free-react-tailwind-admin-dashboard)|[免费演示](https://free-react-demo.tailadmin.com/)，返回HTML但网页工具无可读内容|React19、Vite8、TS6、Tailwind4；真实文件为LICENSE.md（不是LICENSE），MIT|固定df1e9f37e56e0bf83030e8063f5353da2e0ecf18，2026-10-29；有提交和Issues；依赖包括ApexCharts等，不能将模板MIT泛化成每个依赖同许可|暗色、导航、曲线、表格成熟，但非工业模板，无设备/管线语义；免费与Pro分开，未下载Pro；不为通用后台引入大量无关依赖|
|[FUXA](https://github.com/frangoteam/FUXA)|[官方文档](https://frangoteam.github.io/FUXA/)含Live Demo入口|Angular、Node.js、完整SCADA服务；[实际MIT LICENSE](https://github.com/frangoteam/FUXA/blob/master/LICENSE)|官方提交/发布及安全公告可查，支持MQTT/OPC-UA等；完整平台的鉴权、驱动和升级成本需另评估|工业设备、实时曲线、编辑器/管线最全，但引入另一套采集/控制服务，与本任务只读研究整合不匹配；本次不部署、不宣称本地运行验证通过|

以上MIT许可允许保留版权/许可后修改、展示和分发；比赛本身的提交规则另行适用。实际复用的组件及MIT原文将随前端保存，不能以“开源”省略署名。非采用项目只保留调研源码，不复制其商业素材。

## 功能逐项结论

三者均有完整公开源码及暗色主题、曲线基础；Dash直接具备设备状态与工业管线组件，Multidash/TailAdmin需要自行补充。三者均可通过JSON接入TEP，不自带本项目算法。Windows理论上支持Node，但Multidash脚本出现rm -rf，原样命令不是PowerShell原生命令；TailAdmin依赖面较大。只有本次选用的最小组件工程将在本机实际安装、检查和构建，其它候选不标“运行通过”。公开Issues入口：[Dash](https://github.com/Naufaldo/Dash-Template/issues)、[Multidash](https://github.com/hasralgana/multidash/issues)、[TailAdmin](https://github.com/TailAdmin/free-react-tailwind-admin-dashboard/issues)。依赖风险需以锁文件、实际安装和npm audit结果补充记录，未安装的候选不声称无依赖问题。

补充核查：Multidash当前README明确宣布归档，后续开发转移至Dashral，因此不把旧仓库的迁移提交当持续功能维护。Dash的GitHub Pages本次访问失败；TailAdmin演示只获取到HTML，未据此宣称交互验证通过。实际本地组件验证结果见D6_SYSTEM_REPORT.md。

## 最终方案：B，组合复用组件

采用Dash的ScadaGauge/ScadaPilotLed及相关类型和工业色彩体系，结合现有Plotly本地脚本；新增薄层只读Python HTTP API和Svelte/Vite七页应用。Python算法架构不变，不引入React/Next或完整SCADA平台，不复制上游随机store、制冷工艺图或可写控制面板。

选择依据是工业组件实际契合、MIT许可和部署体积，而不是成熟度宣传。TEP冷却回路简图需按已核对物理关系自绘，明确为局部示意，不能把制冷P&ID冒充TEP。流程图不显示未经计算的流量。所有数值来自已有TEP仿真档案；默认明确“历史仿真回放”，播放不是实时工业采集。没有优化或控制写入端点。选型至此完成，后续安装/构建/界面测试记录在D6系统交付报告中，若失败保留失败记录。
