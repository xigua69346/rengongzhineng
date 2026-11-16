# D6 工业HMI界面重构交付 · 2026-11-15

## 调研与最终方案

先完成[D6_UI_REDESIGN_RESEARCH.md](D6_UI_REDESIGN_RESEARCH.md)，然后开始前端改造。选择方案B：借鉴FUXA的工业组态表现方式，局部移植FUXA-SVG-Widgets已审核的Tanks SVG结构，保留Svelte与Python只读接口。没有整套迁移FUXA，也没有仅给旧草图增加装饰。

实际复用Tanks/circularTankLevel-v3.svg的previewWater路径和裁切组织，仅用于容器介质装饰，不显示虚构液位。新建夹套容器、独立供回水、测点引线、执行阀和仪表卡片。未复制含Opto22版权的dynamicSVG图形。原始选中素材、固定提交、SHA256、MIT原文及改造说明保留于public/vendor/fuxa、public/licenses、frontend/THIRD_PARTY.md和artifacts/d6-redesign/provenance.json。

## 品牌与七页风格

按用户确认：工业过程智能诊断平台 / Industrial Process Intelligence & Diagnostics。frontend/src/branding.json统一管理项目名、副标题、logo、favicon、页签名、页头、简介和页脚。新增原创容器/诊断标志brand.svg。七页共享工业蓝灰背景、冷却青色/回水暖色、仪表字体和状态语义。可见界面不再使用CausalVerse品牌；内部Python包名不改，避免破坏既有接口。

侧栏左下角不再出现模板或开源来源链接。法律原文完整保留在frontend/THIRD_PARTY.md与frontend/public/licenses，并随dist分发；没有删除版权文件。

## 工业画面与真实数据边界

- 夹套反应釜、支撑、搅拌轴、冷却入口/回水、阀门执行机构和过程管道可直观看出设备关系；这是局部功能HMI，不是经认证的完整TEP P&ID。
- 供回水流向有独立颜色、箭头和路径动画；仅表示方向，固定速度不代表实测流量。暂停回放时动画暂停，系统偏好减少动画时停用。
- XMV(10)动态指示条绑定原始命令记录，不将命令当实际阀位，更不称冷却水流量；没有阀门开关控制按钮。
- T9、C21、P7原样绑定已有1秒轨迹；报警带与播放中的闪烁来自已保存的统计检测结果，非设备联锁。没有额外编造工程温压阈值，画面明确“工程温压限值：未配置”。
- 介质填充仅为装饰、非液位测量；未画有虚构流量值的泵或额外换热设备。
- 仍是TEP历史仿真回放/只读研究工作台，原有诊断候选、拒绝、区间不可信提示与窗口门控保持。没有修改D2–D5.1.2算法或实验结果，没有新增控制推荐。

## 验证与截图

完整Python测试37 passed；Svelte检查0 errors/0 warnings；Vite生产构建通过。Edge浏览器验证七页、80条运行、品牌/页签、移除侧栏来源、回放、动画启动/暂停、诊断窗口门控、错误/重试、只读写入拦截、390px移动端无页面横向溢出，运行错误0。手机HMI画面可在面板内横向查看，保留仪表文字可读性。

证据均写新目录artifacts/d6-redesign，不覆盖旧D6截图和测试报告：

- overview.png：新品牌与系统总览。
- process.png：冷却回路HMI局部。
- mobile.png：手机布局。
- uncertainty.png：七页统一样式中的可信度页。
- browser-qa.json、tests.xml：浏览器与Python验证记录。
- history-audit.json：547个历史受保护输入/报告逐项SHA256核验。

保留的实际失败：Windows clone有三个无关液压素材路径过长导致完整checkout失败，所用SVG及LICENSE均成功取得；验收脚本第一次默认GBK读取UTF-8失败，显式UTF-8修复；本机服务未启动时首次浏览器请求被拒绝，启动原只读服务后复测通过。没有将这些失败计作通过。

## 运行与维护

现有服务地址：http://127.0.0.1:8766 ，浏览器刷新即可读取新dist。

```powershell
Set-Location -LiteralPath 'D:\广西人工智能大赛'
# 已有构建时
.\scripts\start_d6.ps1
# 修改branding.json或前端后重新构建
npm --prefix frontend run check
npm --prefix frontend run build
```

后端沿用.research/venv-tep的Python环境；不需要新增库、Node后台或现场设备。原D6依赖与锁文件保持，原npm审计的3项低风险开发依赖告警并未因本次UI改造消除，详见原D6交付报告。素材原文可单独审计，所有动画均是声明式SVG/CSS，没有执行上游嵌入脚本或postValue。
