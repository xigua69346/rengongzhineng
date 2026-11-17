<script>
 import {onMount,tick} from 'svelte';
 import Gauge from './lib/components/ScadaGauge.svelte';
 import Pilot from './lib/components/ScadaPilotLed.svelte';
 import Chart from './Chart.svelte';
 import PredictionPanels from './PredictionPanels.svelte';
 import HistoryCompare from './HistoryCompare.svelte';
 import TrustMetrics from './TrustMetrics.svelte';
 import CausalGraph from './CausalGraph.svelte';
 import DetectionSummary from './DetectionSummary.svelte';
 import ProcessHMI from './ProcessHMI.svelte';
 import LiveWorkspace from './LiveWorkspace.svelte';
 import branding from './branding.json';
 const playbackSpeeds=[0.5,1,2,4,8,16,32,64,128];
 const pages=['系统总览','工业过程监控','异常检测','故障诊断','动态因果图','模型可信度','历史实验回放'];
 const subtitles=['以观测为起点，以证据为边界','TEP反应釜与冷却回路 · 局部监视','正常基准之外的信号','保留候选，不强行给出根因','工艺约束与动态反馈','精度改善，不等于决策可信','让每一项判断回到原始实验'];
 const names=['反应釜温度','冷却水出口温度','反应釜压力','冷却水阀命令'];
 const tags=['T9 · XMEAS(9)','C21 · XMEAS(21)','P7 · XMEAS(7)','U10 · XMV(10)'];
 const units=['°C','°C','kPa','%'];const ranges=[[110,135],[70,130],[2500,3000],[0,100]];
 let page=0,runs=[],run='test_f14_00',trajectory=null,detection=null,diagnosis=null,research=null;
 let cursor=5400,playing=false,speed=1,loading=true,error='',kind='VAR',windowSize=1800,detector='PCA',truthVisible=false;
 let intervalData=null,ikind='delta',seed=631000,mechanism=14,dose=1,request=0,intervalRequest=0;
 $: activeStage=cursor<3600?0:readyDiagnosis?2:1;
 let selectedNode=0;let playbackTime=5400;
 let liveMode=true,liveTime=0,liveStatus='未启动';
 $: displayTime=liveMode?liveTime:cursor;
 async function showArchive(){liveMode=false;playing=false;if(!trajectory){await Promise.all([load(),loadInterval()])}}
 async function get(url){let r=await fetch(url);if(!r.ok)throw new Error(`数据接口返回 ${r.status}，请检查本地档案与服务`);return r.json()}
 async function load(){const token=++request;loading=true;error='';playing=false;try{let [t,d,z]=await Promise.all([get('/api/trajectory?run='+run),get('/api/detection?run='+run),get(`/api/diagnosis?run=${run}&kind=${kind}&window=${windowSize}`)]);if(token!==request)return;trajectory=t;detection=d;diagnosis=z;cursor=Math.min(cursor,t.time.length-1);playbackTime=cursor}catch(e){if(token===request){error=e.message;trajectory=null;detection=null;diagnosis=null}}finally{if(token===request)loading=false}}
 async function diagnose(){const selected=[run,kind,Number(windowSize)];diagnosis=null;try{let z=await get(`/api/diagnosis?run=${run}&kind=${kind}&window=${windowSize}`);if(selected[0]===run&&selected[1]===kind&&selected[2]===Number(windowSize))diagnosis=z}catch(e){error=e.message}}
 async function loadInterval(){const token=++intervalRequest;intervalData=null;try{let z=await get(`/api/uncertainty?kind=${ikind}&seed=${seed}&mechanism=${mechanism}&dose=${dose}`);if(token===intervalRequest)intervalData=z}catch(e){if(token===intervalRequest){error=e.message;intervalData=null}}}
 onMount(()=>{Promise.all([get('/api/runs'),get('/api/research')]).then(async([r,s])=>{runs=r;research=s;if(!liveMode)await Promise.all([load(),loadInterval()])}).catch(e=>{error=e.message;loading=false});let frame,last=performance.now();const animate=(now)=>{const dt=Math.min((now-last)/1000,.2);last=now;if(playing&&trajectory&&!loading){playbackTime=Math.min(playbackTime+dt*Number(speed),trajectory.time.length-1);cursor=Math.floor(playbackTime);if(cursor===trajectory.time.length-1)playing=false}frame=requestAnimationFrame(animate)};frame=requestAnimationFrame(animate);return ()=>cancelAnimationFrame(frame)});
 $: current=trajectory?.values[cursor] || [null,null,null,null];
 $: asof=detection?detection.t_seconds.filter(t=>t<=cursor).length-1:-1;
 $: alarm=asof>=0?Boolean(detection['pred_'+detector][asof]):null;
 $: sensorFlags=asof>=0&&detection?.variable_threshold_scores?[8,20,6].map(i=>detection.variable_threshold_scores[asof][i]>detection.limits.Threshold):[null,null,null];
 $: readyDiagnosis=diagnosis&&diagnosis.run_id===run&&diagnosis.kind===kind&&diagnosis.window===Number(windowSize)&&cursor>=3600+Number(windowSize);
 $: visible=trajectory?trajectory.time.filter(t=>t<=cursor&&t%10===0):[];
 $: marker=trajectory?.run.fault_id?[{type:'line',x0:3600,x1:3600,y0:0,y1:1,yref:'paper',line:{color:'#b9a07a',dash:'dot'}}]:[];
 $: firstAlarm=asof>=0?detection.t_seconds.slice(0,asof+1).find((t,i)=>t>=3600&&detection['pred_'+detector][i]):undefined;
 $: detectionMarkers=[{type:'line',x0:cursor,x1:cursor,y0:0,y1:1,yref:'paper',line:{color:'#8ebcde',dash:'solid'}},...marker,...(firstAlarm===undefined?[]:[{type:'line',x0:firstAlarm,x1:firstAlarm,y0:0,y1:1,yref:'paper',line:{color:'#f2d879',dash:'dash'}}]),{type:'line',xref:'paper',x0:0,x1:1,y0:1,y1:1,line:{color:'#e9b76c',dash:'dot'}}];
 $: topContributions=asof>=0?detection.contributions[asof].map((v,i)=>({v,i})).sort((a,b)=>b.v-a.v).slice(0,6):[];
 function series(j){return [{x:visible,y:visible.map(t=>trajectory.values[t][j]),name:tags[j],mode:'lines',line:{width:1.7}}]}
 function label(m){return Number(m)===0?'正常工况':'IDV('+m+')'}
 $: group=research?.graph;
 const positions=[[390,165],[670,165],[390,325],[140,165],[140,325],[670,325],[140,435]];
 $: edges=group?group.parents.flatMap((parents,j)=>parents.filter(i=>i!==j).map(i=>({i,j}))):[];
 function selectPage(i){page=i;location.hash=String(i);if(i===6)showArchive()}
</script>

<svelte:head><title>{branding.pageTitle} / {pages[page]}</title><link rel="icon" href={branding.favicon}/><meta name="description" content={branding.introduction}/></svelte:head>
<div class="shell">
 <aside>
  <div class="brand"><img src={branding.logo} alt="项目标志"/><div>{branding.name}<small>{branding.subtitle}</small></div></div>
  <div class="rail-title">诊断工作空间 <span>01</span></div>
  <nav aria-label="主导航">{#each pages as name,i}<button class:active={page===i} onclick={()=>selectPage(i)}><span class="nav-number">0{i+1}</span>{name}<span class="nav-arrow">↗</span></button>{/each}</nav>
  <div class="rail-note"><span class="dot"></span> {liveMode?'实时自主监控':'历史研究档案'}<p>{liveMode?'真实TEP持续运行':'TEP历史仿真回放'}<br>原模型 / 可追溯证据</p></div>
 </aside>
 <main>
  <header><div class="breadcrumb">{branding.header} <span>/</span> {liveMode?'LIVE / S3':'D6 / ARCHIVE'} <span>/</span> {pages[page]}</div><div class="mode"><span class="dot amber"></span> {liveMode?'TEP实时仿真 · '+liveStatus:'TEP历史仿真回放'} <span class="pill">{liveMode?'LIVE':'ARCHIVE'}</span></div></header>
  <section class="heading"><div><div class="eyebrow">INDUSTRIAL PROCESS / DIAGNOSTICS</div><h1>{pages[page]}</h1><p>{page===0?branding.introduction:subtitles[page]}</p></div><div class="clock" data-playback-time={liveMode?liveTime:playbackTime}><small>SIMULATION CLOCK</small><strong>{String(Math.floor(displayTime/3600)).padStart(2,'0')}:{String(Math.floor(displayTime%3600/60)).padStart(2,'0')}:{String(displayTime%60).padStart(2,'0')}</strong><span>t = {displayTime.toLocaleString()} s</span></div></section>
  <div class="toolbar"><button class:primary={liveMode} aria-pressed={liveMode} onclick={()=>{liveMode=true;playing=false}}>实时监控</button><button class:primary={!liveMode} aria-pressed={!liveMode} onclick={showArchive}>历史档案</button><span class="source">同一主平台 · 实时观测与历史结果严格分开</span></div>
  <LiveWorkspace {page} active={liveMode} bind:clock={liveTime} bind:status={liveStatus}/>
  {#if !liveMode}
  <div class="toolbar"><label>实验运行<select bind:value={run} onchange={load}>{#each runs as r}<option value={r.dataset_run_id}>{r.dataset_run_id} · seed {r.seed}</option>{/each}</select></label><button onclick={()=>{cursor=0;playbackTime=0;playing=false}}>回到起点</button><button class="primary" disabled={!trajectory||loading} onclick={()=>playing=!playing}>{playing?'暂停回放':'播放回放'} {playing?'Ⅱ':'▷'}</button><label>倍速<select aria-label="倍速" bind:value={speed}>{#each playbackSpeeds as rate}<option value={rate}>{rate}×</option>{/each}</select></label><button class="text-button" onclick={()=>truthVisible=!truthVisible}>{truthVisible?'隐藏':'显示'}离线真值</button></div>
  <div class="scrubber"><span>0 s</span><input aria-label="历史回放时间" type="range" min="0" max={trajectory?trajectory.time.length-1:14399} step="1" bind:value={cursor} oninput={()=>{cursor=Number(cursor);playbackTime=cursor;playing=false}}/><span>14,399 s</span></div>
  {#if truthVisible&&trajectory}<div class="notice">离线实验真值：{label(trajectory.run.fault_id)} · 故障计划启用 3600 s。此标签仅供核验，不作为诊断输入。</div>{/if}
  {#if loading}<div class="empty">正在读取原始实验轨迹…</div>{:else if error}<div class="empty error" role="alert">{error}<button onclick={load}>重新读取</button></div>{:else if trajectory}
  {#if page===0}<div class="technical-chain">{#each ['工业仿真观测','异常检测','候选故障诊断','动态关系分析','可信度评估'] as stage,i}<button class:current-stage={activeStage===i} aria-current={activeStage===i?'step':undefined} onclick={()=>selectPage([1,2,3,4,5][i])}><span>0{i+1}</span><strong>{stage}</strong><small>{i>=3?'离线研究证据':activeStage===i?'当前实验阶段':i<activeStage?'观测已具备':'等待前序证据'}</small></button>{/each}</div><p class="source">共享可追溯档案的研究流程；关系分析与可信度页为离线模型证据，不宣称当前诊断已完成因果识别。</p>{/if}
  {#if page===0 || page===1}
   <div class="metrics">{#each names as name,j}<section class="metric"><div class="metric-top">{tags[j]}<span class="dot"></span></div><h3>{name}</h3><div class="reading">{current[j]?.toFixed(j===2?1:2)??'—'}<span>{units[j]}</span></div><div class="metric-foot">已记录测量 / 命令 <span>1 s 原始数据</span></div></section>{/each}</div>
   {#if page===0}<div class="summary-grid"><div class="summary-card"><small>实验 / 随机种子</small><strong>{trajectory.run.seed}</strong><span>{run} · {playing?'回放中':'暂停'} / {cursor}秒</span></div><div class="summary-card"><small>当前异常事件</small><strong>{alarm===null?'待采样':alarm?'统计报警':'未报警'}</strong><span>{detector} · 证据时间{asof>=0?detection.t_seconds[asof]:'—'}秒</span></div><div class="summary-card"><small>候选故障诊断</small><strong>{readyDiagnosis?(diagnosis.refused?'拒绝单一判断':label(diagnosis.candidates[0])):'窗口未齐'}</strong><span>{readyDiagnosis?diagnosis.candidates.map(label).join(' / '):'需要到'+(3600+Number(windowSize))+'秒'}</span></div></div>{/if}
   {#if page===1}   <div class="two-col"><ProcessHMI values={current} {playing} {alarm} timestamp={playbackTime} sensorFlags={sensorFlags}/>
   <section class="panel"><div class="panel-title"><span>当前证据</span><span class="pill">OBSERVED</span></div><div class="evidence"><div class="event-list"><p>运行：{playing?'历史回放中':'已暂停'} · seed {trajectory.run.seed}</p><p>记录：{cursor} s / {trajectory.time.length-1} s</p><p>关键事件：{cursor<3600?'评估窗口尚未开始':'已进入3600秒后的评估阶段'}</p></div><small>异常检测 / {detector}</small><h2 class:warning={alarm}>{alarm===null?'尚无检测样本':alarm?'超出正常统计基准':'当前未报警'}</h2><p>检测采样180秒；最新结果 {asof>=0?detection.t_seconds[asof]+' s':'不可用'}。</p><hr/><small>机制识别 / {kind}</small><h3>{readyDiagnosis?(diagnosis.refused?'当前观测不足以区分故障原因':label(diagnosis.candidates[0])):'等待完整观测窗口'}</h3><p>{readyDiagnosis?'候选：'+diagnosis.candidates.map(label).join('、'):'3600 s 起 '+windowSize+' s 的观测未收齐'}</p><div class="warning-note">模型尚未获得干预优化授权。所有结果仅用于研究诊断。</div></div></section></div>
   {/if}
   {#if page===1}<div class="summary-grid">{#each ['T9','C21','P7'] as tag,j}<div class="summary-card"><small>{tag} · {['反应釜温度 / °C','冷却水出口温度 / °C','反应釜压力 / kPa'][j]}</small><strong>{asof>=0?(detection.variable_threshold_scores[asof][[8,20,6][j]]/detection.limits.Threshold).toFixed(2):'—'}</strong><span>上值为无量纲阈值比，大于1统计越界。采样时刻{asof>=0?detection.t_seconds[asof]:'—'}秒，180秒采样保持；非工程安全限值。</span></div>{/each}</div>{/if}
   <section class="panel"><div class="panel-title"><span>过程趋势</span><select aria-label="趋势变量" bind:value={selectedNode}>{#each names as n,j}<option value={j}>{n} / {units[j]}</option>{/each}</select></div><Chart data={series(Number(selectedNode))} title={names[selectedNode]+' / '+units[selectedNode]} shapes={marker}/><div class="source">来源 {trajectory.source} · 曲线抽取10秒点，读数保留1秒分辨率</div></section>
  {:else if page===2}
   <DetectionSummary {detection} {cursor} {detector} fault={trajectory.run.fault_id}/>
   <div class="notice">PCA贡献度不等于根因。以下展示D3已保存的测试输出，阈值保持原值。</div><section class="panel"><div class="panel-title"><span>异常统计量 / 控制限归一化</span><select bind:value={detector}><option>PCA</option><option>Threshold</option><option>T2</option><option>SPE</option></select></div><Chart title="T²、SPE、传统阈值 · 大于1报警" shapes={detectionMarkers} data={['T2','SPE','Threshold'].map(k=>({x:detection.t_seconds.slice(0,asof+1),y:(k==='Threshold'?detection.threshold_score:detection[k]).slice(0,asof+1).map(v=>v/detection.limits[k]),name:k,mode:'lines'}))}/></section>
   <div class="two-col"><section class="panel"><Chart height={200} title="报警时间段" data={[{x:detection.t_seconds.slice(0,asof+1),y:detection['pred_'+detector].slice(0,asof+1).map(Number),name:'算法报警',line:{shape:'hv'}},...(truthVisible?[{x:detection.t_seconds.slice(0,asof+1),y:detection.y.slice(0,asof+1),name:'离线真值',line:{shape:'hv',dash:'dot'}}]:[])]}/></section><section class="panel"><div class="panel-title">当前SPE残差贡献</div>{#each topContributions as c}<div class="bar-row"><span>{c.i===20?'冷却水出口温度':c.i===8?'反应釜温度':c.i===6?'反应釜压力':'测量变量'}<br/>XMEAS({c.i+1})</span><meter value={c.v} max={topContributions[0]?.v||1}></meter><code>{c.v.toFixed(3)}</code></div>{/each}<p class="source">{detection.source} · 仅使用截至回放时刻的样本</p></section></div>
  {:else if page===3}
   <div class="toolbar"><label>识别方法<select bind:value={kind} onchange={diagnose}><option>static</option><option>VAR</option><option>logistic</option></select></label><label>观测窗口<select bind:value={windowSize} onchange={diagnose}><option value={180}>180秒</option><option value={600}>600秒</option><option value={1800}>1800秒</option></select></label></div>
   <section class="panel diagnosis"><div class="eyebrow">MECHANISM EVIDENCE</div><h2>{readyDiagnosis?(diagnosis.refused?'当前观测不足以区分故障原因':'模型内单一候选：'+label(diagnosis.candidates[0])):'观测窗口尚未完整'}</h2><p class="notice">候选排序分数 ≠ 故障概率。多个候选、空候选或窗口未齐时拒绝单一诊断；分类结果也不等于确定的因果根因。</p>{#if readyDiagnosis}{#each diagnosis.ranking as m,i}<div class="candidate"><span class="rank">0{i+1}</span><strong>{label(m)}</strong><span class="candidate-flag">{diagnosis.candidates.includes(m)?'保留候选':'未入候选'}</span><meter value={diagnosis.scores[[0,4,11,14].indexOf(m)]} max="1"></meter><code>{diagnosis.scores[[0,4,11,14].indexOf(m)].toFixed(4)}</code></div>{/each}{:else}<p>需要到 t={3600+Number(windowSize)} s；当前 t={cursor} s，不提前展示后续窗口结论。</p>{/if}<div class="source">artifacts/d5_1_2/diagnoses.json · 输入仅T9、C21、P7、U10</div></section>
   <section class="panel"><div class="panel-title">模型评价 · 与本次候选排序分开</div><p>Macro-F1：各类F1的平均，越高越好。Top-2：真值进入前两名的比例。拒绝率：模型未给出单一候选的比例，不是故障概率。</p><Chart title="同一窗口三种方法的独立测试结果" xTitle="方法 / 窗口" data={['macro_f1','top2','refusal'].map((key,j)=>({type:'bar',x:research.metrics.filter(m=>m.split==='test'&&m.window===Number(windowSize)).map(m=>m.kind),y:research.metrics.filter(m=>m.split==='test'&&m.window===Number(windowSize)).map(m=>m[key]),name:['Macro-F1','Top-2','拒绝率'][j]}))}/><details><summary>查看全部窗口原始评价表（不隐藏失败）</summary><table><thead><tr><th>窗口</th><th>方法</th><th>Macro-F1</th><th>Top-2</th><th>拒绝率</th></tr></thead><tbody>{#each research.metrics.filter(m=>m.split==='test') as m}<tr><td>{m.window}s</td><td>{m.kind}</td><td>{m.macro_f1.toFixed(4)}</td><td>{(m.top2*100).toFixed(1)}%</td><td>{(m.refusal*100).toFixed(1)}%</td></tr>{/each}</tbody></table></details><p class="source">D3测试80条完整运行；未按测试结果选择最佳模型</p></section>
  {:else if page===4}
   <CausalGraph {group} runId={run}/>
  {:else if page===5}
   <div class="warning-note">所有模型均未获得优化授权。覆盖率高不等于区间可用；支持域失败和宽度超限必须保留。</div>
   <section class="panel"><div class="toolbar"><label>模型<select bind:value={ikind} onchange={loadInterval}><option>delta</option><option>action</option><option>PI</option><option>PI_stable</option></select></label><label>独立测试种子<select bind:value={seed} onchange={loadInterval}>{#each Array.from({length:20},(_,i)=>631000+i) as s}<option value={s}>{s}</option>{/each}</select></label><label>离线实验背景<select bind:value={mechanism} onchange={loadInterval}>{#each [0,4,11,14] as m}<option value={m}>{label(m)}</option>{/each}</select></label><label>已执行历史动作<select bind:value={dose} onchange={loadInterval}>{#each [0,1,5] as d}<option value={d}>+{d}个百分点</option>{/each}</select></label></div><p class="source">此处独立选择D5.1.1已保存实验，与上方D3回放是不同运行；不生成、不推荐新动作。区间为固定5400秒起点的历史预测。</p>
   {#if intervalData}<TrustMetrics {intervalData} summary={research.uncertainty[ikind]}/><PredictionPanels {intervalData}/>{/if}</section>
   <section class="panel"><table><thead><tr><th>模型</th><th>MAE T9/C21/P7</th><th>联合覆盖</th><th>保守拒绝率</th><th>优化授权</th></tr></thead><tbody>{#each Object.entries(research.uncertainty) as [k,v]}<tr><td>{k}</td><td>{v.MAE.map(n=>n.toFixed(3)).join(' / ')}</td><td>{v.joint_coverage*100}%（20种子）</td><td>{(v.rejection_rate*100).toFixed(1)}%</td><td class="warning">未授权</td></tr>{/each}</tbody></table><p class="source">候选分歧拒绝率来自事后保守审计；联合覆盖20/20的精确95%区间为83.2%–100%。不据此声称总体必然覆盖。</p></section>
  {:else if page===6}
   <HistoryCompare {runs} {trajectory} {cursor}/>
   <div class="two-col"><section class="panel"><div class="panel-title">实验档案</div><dl><dt>Run ID</dt><dd>{run}</dd><dt>随机种子</dt><dd>{trajectory.run.seed}</dd><dt>引擎</dt><dd>TEP / Python</dd><dt>采样</dt><dd>原始1秒 / 检测180秒</dd><dt>分区</dt><dd>独立测试集</dd><dt>数据来源</dt><dd>{trajectory.source}</dd></dl><button onclick={()=>{const b=new Blob([JSON.stringify(trajectory.manifest,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=run+'_manifest.json';a.click();URL.revokeObjectURL(a.href)}}>下载原始 Manifest ↓</button></section><section class="panel"><Chart title="历史过程 · 反应釜温度 / °C" data={series(0)} shapes={marker}/></section></div><section class="panel"><div class="panel-title">数据与研究边界</div><p>全部80条D3测试运行可通过顶部选择器回放，正常和三种故障各20条。没有最佳种子筛选。</p><p>原始轨迹只读；播放控制仅移动展示时钟。模型依据窗口完整性展示已存诊断，未连接现场设备，也不执行仿真器控制写入。</p><p>故障在3600秒启用；诊断使用已知实验时钟，不代表未知起始时刻下的在线系统已经验证。</p></section>
  {/if}
  <footer><span>{branding.footer}</span><span>{branding.footerNote}</span></footer>
  {/if}
  {/if}
 </main>
</div>
