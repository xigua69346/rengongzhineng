# D6 第三方组件

Dash-Template: https://github.com/Naufaldo/Dash-Template
固定提交59498e5c3f977e3ce5395ad0337528f842370670，Copyright (c) 2026 Naufaldo，MIT。
原样复用src/lib/components/ScadaGauge.svelte、ScadaPilotLed.svelte及src/lib/types/iot.ts。
原始完整审计仓库保留在.research/d6/Dash-Template，没有修改上游。
工业色彩体系参考其DESIGN.md，界面布局、数据连接与TEP局部图由本项目实现。
未复制随机设备store、控制开关、制冷管线图。

Svelte runtime：MIT，版权Svelte Contributors；Plotly.js 4.1.1来自现有Plotly7.1.0安装，MIT，版权Plotly Inc。
以上原文在public/licenses并随dist分发。Plotly bundle还包含其内置依赖声明，不移除bundle内注释。
NPM开发依赖的原始许可保留于node_modules和锁文件对应包；没有采用Multidash/TailAdmin的代码或素材；FUXA组件复用见下文。
TEP及Python后端继续适用项目原有THIRD_PARTY_NOTICES.md。

FUXA-SVG-Widgets: https://github.com/frangoteam/FUXA-SVG-Widgets
固定70e7c4a656d111c0428c77eb4b0409fc3670b8d5，MIT，Copyright (c) 2019-2025 frangoteam info@frangoteam.org。
ProcessHMI.svelte局部适配Tanks/circularTankLevel-v3.svg的previewWater路径及裁切组织，介质仅为装饰、不显示液位；未移植脚本/定时器/控制接口。原始所选文件保留public/vendor/fuxa，许可证保留public/licenses/FUXA-SVG-Widgets-MIT.txt。未复制带Opto22版权的dynamicSVG图形。
