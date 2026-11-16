<script>
 import {onMount} from 'svelte';
 let reduced=false;
 onMount(()=>{const m=matchMedia('(prefers-reduced-motion: reduce)');const update=()=>reduced=m.matches;update();m.addEventListener('change',update);return ()=>m.removeEventListener('change',update)});
 export let sensorFlags=[null,null,null];
 export let values=[null,null,null,null];export let playing=false;export let alarm=null;export let timestamp=0;
 $: phase=reduced?0:timestamp;
 $: mixerScale=Math.cos(phase*Math.PI/60);
 const fmt=(n,d=2)=>Number.isFinite(n)?n.toFixed(d):'—';
 $: command=Number.isFinite(values[3])?Math.max(0,Math.min(100,values[3])):0;
</script>
<section class="hmi-panel panel" class:running={playing} class:alarm-active={alarm} aria-label="反应釜冷却回路工业HMI">
 <div class="hmi-top"><div><span class="section-no">UNIT 01</span><strong>反应釜与冷却水系统</strong><small>REACTOR / COOLING WATER CIRCUIT</small></div><span class="hmi-status"><i></i>{playing?'历史回放中':'回放已暂停'} · {Math.floor(timestamp)} s</span></div>
 <div class="hmi-annunciator" class:raised={alarm}><span class="alarm-light" style:opacity={alarm&&!reduced&&Math.floor(timestamp*2)%2?0.25:1}></span><b>{alarm===null?'尚无检测样本':alarm?'异常统计量报警':'当前检测未报警'}</b><span>算法信号 · 非设备联锁</span><code>R-101</code></div>
 <svg viewBox="0 0 1040 600" role="img" aria-label="夹套反应釜、冷却供回水、执行阀及过程测点">
  <defs>
   <pattern id="hmi-grid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="#253641" stroke-width=".55"/></pattern>
   <linearGradient id="steel" x1="0" x2="1"><stop stop-color="#354a57"/><stop offset=".35" stop-color="#718b97"/><stop offset=".65" stop-color="#3e5664"/><stop offset="1" stop-color="#253b49"/></linearGradient>
   <linearGradient id="vessel" x1="0" x2="1"><stop stop-color="#1a303c"/><stop offset=".4" stop-color="#304c5b"/><stop offset="1" stop-color="#142833"/></linearGradient>
   <linearGradient id="jacket" x1="0" x2="1"><stop stop-color="#123c4d"/><stop offset=".5" stop-color="#246179"/><stop offset="1" stop-color="#123c4d"/></linearGradient>
   <clipPath id="medium-clip"><rect x="362" y="206" width="208" height="220" rx="65"/></clipPath>
   <marker id="cold-arrow" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto"><path d="M0 0L7 4L0 8" fill="none" stroke="#71d5e8" stroke-width="1.8"/></marker>
   <marker id="warm-arrow" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto"><path d="M0 0L7 4L0 8" fill="none" stroke="#e8b879" stroke-width="1.8"/></marker>
  </defs>
  <rect width="1040" height="600" fill="url(#hmi-grid)"/>
  <text class="zone-label" x="34" y="35">PROCESS AREA</text><text class="zone-label" x="712" y="35">COOLING WATER</text>
  <!-- Dedicated supply enters jacket below; return exits above. No pump or exchanger is invented. -->
  <path class="pipe-base" d="M978 436H592V386"/><path class="pipe-cold" d="M978 436H592V386"/>
  <path style:stroke-dashoffset={-(phase*.35)%27} class="flow cold" d="M978 436H592V386"/>
  <path class="pipe-base" d="M592 252V167H978"/><path class:point-alert={sensorFlags[1]} class="pipe-warm" d="M592 252V167H978"/>
  <path style:stroke-dashoffset={-(phase*.35)%27} class="flow warm" d="M592 252V167H978"/>
  <path d="M940 436H910" stroke="#71d5e8" stroke-width="2" marker-end="url(#cold-arrow)"/>
  <path d="M922 167H952" stroke="#e8b879" stroke-width="2" marker-end="url(#warm-arrow)"/>
  <path d="M704 167H735" stroke="#e8b879" stroke-width="2" marker-end="url(#warm-arrow)"/>
  <path class="pipe-base" d="M45 274H350M465 190V112H620"/><path class="process-pipe" d="M45 274H350M465 190V112H620"/>
  <text x="43" y="246" class="label">过程进料</text><text x="514" y="89" class="label">过程出口 / 下游系统</text>
  <path d="M115 274H146" stroke="#a7b9c4" stroke-width="2" marker-end="url(#cold-arrow)"/>
  <!-- Cylindrical pressure vessel and cooling jacket. -->
  <rect x="330" y="196" width="273" height="255" rx="88" fill="url(#jacket)" stroke="#53889a" stroke-width="2"/>
  <path style:stroke-dashoffset={-(phase*.25)%18} class="jacket-flow" d="M589 386V310Q589 211 478 211H458Q345 211 345 310V372" fill="none" stroke="#6bb4c8" stroke-width="2"/>
  <rect class:point-alert={sensorFlags[0]||sensorFlags[2]} x="354" y="180" width="224" height="265" rx="80" fill="url(#vessel)" stroke="#9db4be" stroke-width="2.5"/>
  <ellipse cx="466" cy="225" rx="103" ry="36" fill="url(#steel)" opacity=".6"/>
  <!-- Adapted from FUXA Tanks/circularTankLevel-v3.svg previewWater.
       Decorative medium only: not a measured or calculated liquid level. -->
  <g clip-path="url(#medium-clip)" opacity=".28"><path class="medium" fill="#69aaa5" d="M 10 101.0 Q 26.25 97.00, 42.50 101.00 Q 58.75 105.00, 75.00 101.00 Q 91.25 97.00, 107.50 101.00 Q 123.75 105.00, 140.00 101.00 V 140 H 10 Z" transform="translate(344 170) scale(1.72 1.9)"/></g>
  <path d="M378 441L367 496H392L404 443M528 443L540 496H565L554 439" fill="url(#steel)" stroke="#6f8996"/>
  <rect x="357" y="495" width="48" height="9" rx="2" fill="#3a515f"/><rect x="531" y="495" width="48" height="9" rx="2" fill="#3a515f"/>
  <rect x="444" y="136" width="44" height="53" rx="6" fill="url(#steel)" stroke="#8caab6"/><path d="M466 189V394" stroke="#a5b7bf" stroke-width="5"/><g class="agitator" transform={'translate(466 394) scale('+mixerScale+',1)'}><path d="M-49-12L49 12M-49 12L49-12" stroke="#c7dbe3" stroke-width="6"/><ellipse rx="18" ry="5" fill="#829fac"/></g>
  <rect x="391" y="277" width="150" height="71" rx="7" fill="#102631" stroke="#486875"/><text x="466" y="303" text-anchor="middle" class="vessel-tag">R-101</text><text x="466" y="328" text-anchor="middle" class="label">夹套反应釜</text>
  <text x="377" y="536" class="small-label">介质仅为图形示意 · 非液位测量</text>
  <!-- Command-driven valve indicator: never label as actual stem position. -->
  <g class="valve" transform="translate(770 436)"><path d="M-36-23L0 0L-36 23Z M36-23L0 0L36 23Z" fill="#183d4c" stroke="#73c9dc" stroke-width="2"/><path d="M0 0V-45" stroke="#88aab8" stroke-width="4"/><rect x="-25" y="-73" width="50" height="29" rx="5" fill="url(#steel)" stroke="#9cb6c1"/><circle r="11" fill="#71d5e8"/><path class="command-pointer" d="M0 0V-19" stroke="#effaff" stroke-width="3" transform={'rotate('+(command*1.8-90)+')'}/></g>
  <rect x="680" y="484" width="185" height="66" rx="6" fill="#112731" stroke="#375d70"/><text x="693" y="504" class="instrument-tag">XMV(10) · 控制命令</text><rect x="694" y="518" width="110" height="7" rx="3" fill="#2c424e"/><rect x="694" y="518" width={command*1.1} height="7" rx="3" fill="#71d5e8"/><text x="816" y="527" class="command-value">{fmt(values[3],1)}%</text><text x="694" y="541" class="micro">不是实际阀位 / 流量</text>
  <text x="861" y="397" class="cold-label">冷却水供水</text><text x="861" y="418" class="small-label">入口温度未观测</text><text x="863" y="130" class="warm-label">冷却水回水</text>
  <!-- Instrument lead lines and displays, bound only to recorded observable channels. -->
  <path d="M363 240H300V142H245M352 362H283V371H245M805 167V231" fill="none" stroke="#708e9e" stroke-width="1.4" stroke-dasharray="4 4"/>
  <g class:point-alert={sensorFlags[0]} class="instrument-card" transform="translate(35 92)"><rect width="210" height="97" rx="7" fill="#10232c" stroke="#456674"/><text x="15" y="24" class="instrument-tag">TI-009 / 反应釜温度</text><text x="15" y="63" class="instrument-value">{fmt(values[0])}<tspan class="unit"> °C</tspan></text><text x="15" y="84" class="micro">XMEAS(9) · {sensorFlags[0]===null?'未采样':sensorFlags[0]?'统计越界':'阈值内'}</text></g>
  <g class:point-alert={sensorFlags[2]} class="instrument-card" transform="translate(35 327)"><rect width="210" height="97" rx="7" fill="#10232c" stroke="#456674"/><text x="15" y="24" class="instrument-tag">PI-007 / 反应釜压力</text><text x="15" y="63" class="instrument-value">{fmt(values[2],1)}<tspan class="unit"> kPa</tspan></text><text x="15" y="84" class="micro">XMEAS(7) · {sensorFlags[2]===null?'未采样':sensorFlags[2]?'统计越界':'阈值内'}</text></g>
  <g class:point-alert={sensorFlags[1]} class="instrument-card" transform="translate(708 231)"><rect width="225" height="97" rx="7" fill="#2a2822" stroke="#7b6950"/><text x="15" y="24" class="instrument-tag">TI-021 / 冷却水出口</text><text x="15" y="63" class="instrument-value warm-label">{fmt(values[1])}<tspan class="unit"> °C</tspan></text><text x="15" y="84" class="micro">XMEAS(21) · {sensorFlags[1]===null?'未采样':sensorFlags[1]?'统计越界':'阈值内'}</text></g>
  <text x="35" y="574" class="small-label">局部功能画面 / 非完整P&amp;ID · 未接入现场设备</text>
 </svg>
 <div class="hmi-legend"><span><i class="cold-key"></i>冷却供水</span><span><i class="warm-key"></i>冷却回水</span><span>动画相位跟随历史时间 · 暂停/拖动同步</span><span>搅拌/流动为原理示意 · 无实测转速或流量</span></div>
</section>
<style>
 .hmi-panel{padding:0!important;background:#101e27!important}.hmi-top{padding:20px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #314653}.hmi-top strong{font-size:15px;font-weight:500}.hmi-top small{display:block;font:9px Consolas;letter-spacing:.15em;color:#6e93a5;margin-top:8px}.hmi-status{font:10px Consolas;color:#97b6c5}.hmi-status i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#7f9cab;margin-right:7px}.running .hmi-status i{background:#71d5d0}.hmi-annunciator{display:flex;align-items:center;gap:10px;padding:10px 24px;background:#162c33;color:#9ab8bf;font-size:10px;border-bottom:1px solid #2b434e}.hmi-annunciator code{margin-left:auto}.hmi-annunciator b{font-weight:500}.hmi-annunciator.raised{background:#382d20;color:#ebbc72}.alarm-light{width:7px;height:7px;border-radius:50%;background:#6e928d}.raised .alarm-light{background:#ebbc72}.hmi-panel svg{display:block;width:100%;height:auto}svg text{font-family:'Microsoft YaHei',sans-serif}.zone-label{font:10px Consolas;letter-spacing:.18em;fill:#4e7184}.pipe-base{fill:none;stroke:#263d4c;stroke-width:17;stroke-linejoin:round}.pipe-cold{fill:none;stroke:#457f94;stroke-width:9;stroke-linejoin:round}.pipe-warm{fill:none;stroke:#8b7050;stroke-width:9;stroke-linejoin:round}.process-pipe{fill:none;stroke:#6d818c;stroke-width:7}.flow{fill:none;stroke-width:3;stroke-dasharray:7 20;stroke-linecap:round;animation:flow 2s linear infinite;animation-play-state:paused}.cold{stroke:#a8ecff}.warm{stroke:#ffe0aa}.jacket-flow{stroke-dasharray:6 12;animation:flow 3s linear infinite;animation-play-state:paused}.running .flow,.running .jacket-flow{animation-play-state:running}.vessel-tag{font:26px Consolas;letter-spacing:.1em;fill:#e5f0f4}.label{font-size:14px;fill:#b4cbd6}.small-label{font-size:11px;fill:#7193a4}.instrument-tag{font-size:15px;fill:#a4bfcb}.instrument-value{font:34px Consolas;fill:#d3e9f1}.unit{font:12px Consolas;fill:#8daeba}.micro{font-size:10px;fill:#7896a5}.cold-label{font-size:14px;fill:#8fdaeb}.warm-label{fill:#e6bc87;font-size:14px}.instrument-value.warm-label{font:34px Consolas}.command-value{font:13px Consolas;fill:#bcdae4}.hmi-legend{padding:15px 23px;display:flex;gap:20px;flex-wrap:wrap;border-top:1px solid #2a414e;color:#7d9cac;font-size:9px}.hmi-legend i{display:inline-block;width:15px;height:3px;margin:0 6px 2px 0}.cold-key{background:#71d5e8}.warm-key{background:#e8b879}@keyframes flow{to{stroke-dashoffset:-54}}@keyframes blink{to{opacity:.25}}@media(prefers-reduced-motion:reduce){.flow,.jacket-flow,.alarm-light{animation:none!important}}@media(max-width:750px){.hmi-top{padding:16px;gap:10px}.hmi-top strong{font-size:12px}.hmi-top small{font-size:7px}.hmi-status{font-size:8px}.hmi-annunciator{padding:10px 15px}.hmi-annunciator>span:not(.alarm-light){display:none}.hmi-legend{padding:12px;gap:10px}}
.point-alert{stroke:#ffc46d!important;filter:drop-shadow(0 0 4px #b77735)}.instrument-card.point-alert rect{stroke:#ffc46d;stroke-width:3;fill:#392a1f}.instrument-card.point-alert .instrument-value{fill:#ffd59a}
.instrument-card.point-alert{stroke:none!important;filter:none}.instrument-card.point-alert rect{filter:drop-shadow(0 0 4px #b77735)}
</style>
