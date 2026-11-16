# D4 变量物理意义与输入权限

已对照固定commit的constants.py、python_backend.py、原Fortran teprob.f及D2 adapter.py核查。名称采用上游原名，物理作用按该TEP定义，不按PCA贡献猜测。kscmh为千标准m³/h；压力为表压。

|变量|物理名称|单位|属性|更新/采样|物理作用|来源|在线输入|
|---|---|---|---|---|---|---|---|
|XMEAS(1)|A Feed (stream 1)|kscmh|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(2)|D Feed (stream 2)|kg/hr|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(3)|E Feed (stream 3)|kg/hr|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(4)|A and C Feed (stream 4)|kscmh|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(5)|Recycle Flow (stream 8)|kscmh|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(6)|Reactor Feed Rate (stream 6)|kscmh|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(7)|Reactor Pressure|kPa|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(8)|Reactor Level|%|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(9)|Reactor Temperature|deg C|测量|1s求值/含测量噪声|反应釜热状态观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(10)|Purge Rate (stream 9)|kscmh|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(11)|Product Sep Temp|deg C|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(12)|Product Sep Level|%|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(13)|Prod Sep Pressure|kPa|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(14)|Prod Sep Underflow (stream 10)|m3/hr|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(15)|Stripper Level|%|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(16)|Stripper Pressure|kPa|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(17)|Stripper Underflow (stream 11)|m3/hr|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(18)|Stripper Temperature|deg C|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(19)|Stripper Steam Flow|kg/hr|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(20)|Compressor Work|kW|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(21)|Reactor Cooling Water Outlet Temp|deg C|测量|1s求值/含测量噪声|冷却回路温度观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(22)|Separator Cooling Water Outlet Temp|deg C|测量|1s求值/含测量噪声|过程流量/温压/液位/能耗观测，具体对象见名称|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(23)|Reactor Feed Component A|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(24)|Reactor Feed Component B|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(25)|Reactor Feed Component C|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(26)|Reactor Feed Component D|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(27)|Reactor Feed Component E|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(28)|Reactor Feed Component F|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(29)|Purge Gas Component A|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(30)|Purge Gas Component B|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(31)|Purge Gas Component C|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(32)|Purge Gas Component D|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(33)|Purge Gas Component E|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(34)|Purge Gas Component F|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(35)|Purge Gas Component G|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(36)|Purge Gas Component H|mol%|测量|360s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(37)|Product Component D|mol%|测量|900s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(38)|Product Component E|mol%|测量|900s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(39)|Product Component F|mol%|测量|900s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(40)|Product Component G|mol%|测量|900s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMEAS(41)|Product Component H|mol%|测量|900s采样保持+一周期分析延迟|物料组成观测，不能重复保持值作新观测|constants+teprob方程|允许；本模型仅用6/7/8/9/21|
|XMV(1)|D Feed Flow (stream 2)|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(2)|E Feed Flow (stream 3)|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(3)|A Feed Flow (stream 1)|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(4)|A and C Feed Flow (stream 4)|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(5)|Compressor Recycle Valve|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(6)|Purge Valve (stream 9)|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(7)|Separator Pot Liquid Flow|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(8)|Stripper Liquid Product Flow|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(9)|Stripper Steam Valve|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(10)|Reactor Cooling Water Flow|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(11)|Condenser Cooling Water Flow|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|
|XMV(12)|Agitator Speed|0–100%归一化命令|控制|1s记录；主要PI每3s，串级360/900s；12通常恒定|执行器请求，非实际流量/转速|controllers+python_backend|允许已发生的控制历史；本模型用4/10|

## 故障入口及潜在量

|对象|实际注入位置|在线权限|
|---|---|---|
|IDV4|tcwr=tesub8(5,time)+5*idv[3]；入口温度+5°C|标签仅离线，入口温度内部真值不得输入|
|IDV11|wlk.idvwlk[4]=idv[10]，冷却入口温度随机游走|同上|
|IDV14|ivst[9]=idv[13]，命令距已接受目标大于2百分点才更新vcv[9]|IDV及阀门目标/位置仅离线校验|
|实际阀位|yy[47]；命令XMV10经死区与时间常数形成实际位置|不可当标准传感器|
|冷却水流量|fwr=vpos[9]*vrng[9]/100|内部量，不是XMV10本身|
|换热|qur=uar*(twr-tcr)*(...)；冷却水与釜体能量平衡耦合|内部量仅作物理依据|

## 采样与闭环核查

XMEAS9=tcr，XMEAS21=twr。D3高贡献变量XMEAS2为D进料kg/h，25为反应进料C组成，27为反应进料E组成，31/33/36为放空气C/E/H组成。它们是观测响应，不直接代表故障入口。

23..36的tgas每0.1h推进，37..41的tprod每0.25h推进，并以xdel输出上周期组成。真实正常日志中23/36更新秒为360、721、1081…，37/41为901、1801、2700…；浮点时钟产生约1s偏移。当前只用连续5路测量+2路命令，避免把采样保持值误当新证据。

ctrl10按XMEAS21更新XMV10，ctrl18按XMEAS9串级更新ctrl10设定点；ctrl17按XMEAS8更新A+C进料设定点再由ctrl4输出XMV4。下发命令与实际阀门位置不同。所有合法控制特征都使用历史值，不输入未来控制、RNG、IDV、内部状态。

来源：[固定后端方程](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/9a6c8e5fcef4a2850778704e7793c87b0a187005/src/tep/python_backend.py)、[变量定义](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/9a6c8e5fcef4a2850778704e7793c87b0a187005/src/tep/constants.py)、[原Fortran](https://github.com/jkitchin/tennessee-eastman-profbraatz/blob/9a6c8e5fcef4a2850778704e7793c87b0a187005/teprob.f)。
