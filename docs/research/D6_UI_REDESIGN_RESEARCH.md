# D6 工业HMI重构选型 · 2026-11-15

## 结论先行：方案B，复用动画SVG/HMI组件并改造

保留Svelte/Vite与Python只读接口，采用FUXA的标签绑定、分层管线及状态动画方法，局部复用FUXA-SVG-Widgets经逐文件审核的SVG结构。重做完整反应釜冷却画面，不保留原草图。没有理由为一个画面迁移整套后端；也不能把制冷或水箱示例冒充完整TEP工艺。

## 实际核查

|候选|技术栈/实际许可证|动画和流程适用性|本系统接入方式/结论|
|---|---|---|---|
|[FUXA](https://github.com/frangoteam/FUXA)|Angular/Node，已查看[真实MIT LICENSE](https://github.com/frangoteam/FUXA/blob/master/LICENSE)|[管道动画](https://frangoteam.github.io/FUXA/HowTo-animate-Pipe/)、SVG设备、颜色/报警状态、组态编辑器；最贴近真正SCADA|可经JSON/WebSocket适配Python，但整套服务还包含采集/控制和编辑器。当前无需迁入；复用其可视化组织方法，不部署完整FUXA，不声称完成其本机运行验证|
|[FUXA-SVG-Widgets](https://github.com/frangoteam/FUXA-SVG-Widgets)|纯SVG+JS；实际下载并阅读根MIT LICENSE，frangoteam 2019–2025；固定70e7c4a656d111c0428c77eb4b0409fc3670b8d5，2026-06-14提交|实际检查Tanks、controls、dynamicSVG；有水箱填充、颜色切换、阀门、3D管道和仪表；[官方接口](https://frangoteam.github.io/FUXA/HowTo-Widgets/)为putValue/postValue|只移植展示结构和单向属性绑定，移除脚本定时器、控制事件和postValue。不能用img加载SVG后假定内部脚本会自动绑定Svelte。优先选Tanks结构；dynamicSVG多个文件含Opto22版权，不能把根MIT当所有第三方图形的自动授权，不复制这些来源尚需额外确认的图形|
|[SCADA-LTS](https://github.com/SCADA-LTS/Scada-LTS)|Java/Tomcat/Vue，[LICENSE为GPLv2](https://github.com/SCADA-LTS/Scada-LTS/blob/develop/LICENSE)|完整组态/数据点平台，可做过程画面；不是轻量SVG库|需另搭Java服务与数据源，许可及发布义务须另评估；对已有只读工作台成本过高，不采用、不复制代码|

FUXA官方Live Demo链接已访问，演示索引没有提供可供本次工具验证的交互画面，不写为运行通过。仓库下载在Windows遇到无关液压符号超长文件名，clone对象成功但完整checkout失败；所检查Tanks/dynamicSVG/LICENSE均已落盘，后续只提取需要的文件，不隐藏此兼容问题。没有进行整个平台部署或完整依赖安全审计。

## 具体改造

反应釜区域采用夹套容器、进/出口独立管路、冷却水供回水、执行阀、测点引线、工业标签和报警带。管道粒子仅表示路径/方向，固定动画速率，不表示真实流量；播放暂停时动画同步暂停。阀门指示条绑定XMV10命令，明确不是实际阀位；不虚构开关状态。T9/C21/P7来自原档案，报警来自已保存检测器，不把PCA报警等同某个温度/压力越过工程限值。反应釜介质装饰区无量化液位，避免暗示没有接入的液位测量。支持减少动态效果的系统偏好。

品牌统一配置管理名称、英文副标题、logo、页签、页头、简介和页脚；新名称待用户确认时使用中性暂定名，不沿用CausalVerse可见品牌。侧栏去掉来源提示，版权和第三方原文保留在THIRD_PARTY.md/public/licenses，法律声明不删除。

研究结论完成后才开始修改前端。采用frontend-design技能组织深色工业HMI版式；后端和D2至D5算法、数据保持不变，不新增控制接口。交付截图、构建/浏览器结果、实际复用范围见D6_UI_REDESIGN_DELIVERY.md。
