# D6 工业诊断工作台交付

## 选型先于开发

先检查原有Python工程和D2至D5.1.2报告，再下载三个候选仓库、检查LICENSE/源码/依赖，并生成D6_TEMPLATE_RESEARCH.md，然后开始开发。最终方案B：Dash-Template的MIT工业仪表组件 + 现有Plotly + 新只读接口。没有迁移Python算法框架，没有复制模板假数据引擎。

## 已实现

七页：系统总览、工业过程监控、异常检测、故障诊断、动态因果图、模型可信度、历史实验回放。深色工业主题，桌面侧栏/手机横向导航，加载/错误/重试状态。

D3全部80条测试运行可切换：1秒真实仿真读数、10秒曲线、播放/暂停、倍速、时间拖动、重置、离线真值开关、原始manifest下载。回放不是现场实时采集，页面始终明确标注。没有随机波动占位，没有重新生成数据。

异常页复用D3已保存的T²/SPE/传统阈值与PCA判定、原控制限、逐时刻SPE贡献，严格显示截至当前回放时刻的结果。检测为180秒网格，不能伪装成每秒新检测。贡献度不等于根因。

诊断复用D5.1.2 static/VAR/logistic及180/600/1800秒窗口，显示排名、未校准分数、候选/拒绝和完整测试统计。观测窗口未结束时不提前显示该窗口结论；单候选也不是确定的因果根因。使用已知实验时钟，未宣称未知故障起点在线验证成功。

动态图读取D4候选父节点及滞后结构，自回归边在表中列出；说明工艺约束、闭环混杂和局部约化模型性质，不把每条边当已干预验证。TEP冷却图自绘，明确非完整P&ID；没有编造入口温度、实际流量或阀位。

可信度页读取D5.1.1四模型×20种子×四背景×三历史动作的显式区间，逐T9/C21/P7显示预测、真值、上下界；另列误差、联合覆盖和保守审计拒绝率。该页实验选择与顶部D3回放明确分开，不同数据不拼接，历史背景标签不作为在线预测输入。所有优化授权均关闭，未缩窄区间或删去不稳定模型。

## 技术结构及只读接口

frontend：Svelte5、Vite6、TypeScript工具链，复用两个工业组件，不引入SvelteKit/Next服务；Plotly脚本来自现有安装，打包本地运行，无CDN依赖。固定版本以frontend/package-lock.json为准。生产构建是静态文件。

src/causalverse/dashboard/server.py：Python标准库ThreadingHTTPServer，仅监听127.0.0.1:8766，薄层读取档案，不修改原算法。GET /api/runs、trajectory、detection、diagnosis、research、uncertainty。运行/模型/窗口/种子/动作均白名单；静态目录限制在frontend/dist。POST/PUT/PATCH/DELETE均405，没有set_control/inject_fault等写入端点。不存在真实设备连接或自动推荐。

算法整合采用已有模型的保存输出，适合验证研究和回放；本阶段没有任意新数据流推理、现场PLC接入、持久化多用户服务、生产鉴权或大并发部署。七页功能完成不意味着工业生产认证或D5.2优化获准。

## 实际验证与失败记录

Python完整测试37 passed。Svelte检查0 errors/0 warnings，Vite生产构建通过。Edge无头浏览器验证七页、80个运行选项、播放时钟、窗口门控、方法/窗口/种子/历史动作切换、错误与重试、禁止写入、390px手机无横向溢出，页面运行错误0。证据artifacts/d6/tests.xml、browser-qa.json、overview.png、mobile.png、uncertainty.png。

实际发现上游声明Svelte插件4只接受Vite5，与声明的Vite6冲突，首次npm安装ERESOLVE失败；新工程改用插件5，未使用force/legacy-peer-deps，原仓库保留不动。npm audit记录3个low（同一deepmerge原型污染公告及关联开发依赖链），无moderate/high/critical，当前audit无自动修复。不能宣称依赖零漏洞；生产服务使用静态构建，不运行Vite开发服务器，服务限定本机。详见artifacts/d6/npm-audit.json。

浏览器首次在沙箱启动失败；在批准的沙箱外运行Edge后又因服务网络隔离超时，最终将只读本机服务也置于批准环境，复测通过。没有把这些启动失败当成页面测试通过。

历史输入保护复用D5.1.2的547个受保护文件清单，交付时另行核对并保存artifacts/d6/history-audit.json；未写入D2至D5.1.2实验目录。

## Windows启动与复现

已在本机Windows11、Node24.20.0、npm11.19.0、CPython3.12验证。首次安装与构建：

```powershell
Set-Location -LiteralPath 'D:\广西人工智能大赛\frontend'
npm ci --ignore-scripts
npm run check
npm run build
Set-Location ..
.\scripts\start_d6.ps1
```

浏览器打开 http://127.0.0.1:8766 。已有dist时直接运行start_d6.ps1，不需npm或联网。

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
& .\.research\venv-tep\Scripts\python.exe -m pytest tests -q
# 浏览器验收需本机Edge与Playwright，模块路径按安装位置设置
$env:CAUSALVERSE_PLAYWRIGHT_MODULE='C:\Users\叶子恒\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
node scripts/qa_d6.cjs
```

第三方许可原文位于frontend/public/licenses（随dist分发），源码和来源说明见frontend/THIRD_PARTY.md。本阶段不修改历史训练/校准结果，不重新训练算法，不开发任何控制推荐。
