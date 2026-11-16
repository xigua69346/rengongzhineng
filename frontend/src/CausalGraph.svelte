<script>
 import {initialPoints,edgeGeometry} from './graphGeometry.js';
 export let group;export let runId='';
 function reset(){points=initialPoints();selected=5;all=false;zoom=1;pan=[0,0];detail=null;drag=null}
 let points=initialPoints();let viewport;
 let selected=5,all=false,zoom=1,pan=[0,0],drag=null,svg,detail=null;
 $: candidates=group.parents.flatMap((p,j)=>p.map(i=>({i,j,type:i===j?'uncertain':'candidate'})));
 $: effects=[0,1,2].map(j=>({i:5,j,type:'effect'}));
 $: shown=[...candidates,...effects].filter(e=>all||e.i===selected||e.j===selected);
 $: geometries=shown.map(e=>({...e,...edgeGeometry(e,points)}));
 $: if(runId){reset()}
 function xy(e,model=false){const p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform((model?viewport:svg).getScreenCTM().inverse())}
 function start(e,i){e.preventDefault();e.stopPropagation();let p=xy(e,i!==null);drag={i,p,last:points.map(a=>[...a]),pan:[...pan]};svg.setPointerCapture(e.pointerId);if(i!==null)selected=i}
 function move(e){if(!drag)return;const p=xy(e,drag.i!==null),dx=p.x-drag.p.x,dy=p.y-drag.p.y;if(drag.i===null)pan=[drag.pan[0]+dx,drag.pan[1]+dy];else points=drag.last.map((a,i)=>i===drag.i?[a[0]+dx,a[1]+dy]:a)}
</script>
<section class="panel graph-panel">
 <div class="panel-title"><strong>局部动态结构与实验证据</strong><div class="graph-tools"><button onclick={()=>zoom=Math.min(2,zoom+.15)} aria-label="放大因果图">＋</button><button onclick={()=>zoom=Math.max(.5,zoom-.15)} aria-label="缩小因果图">−</button><button onclick={reset}>复位视图</button><label><input type="checkbox" bind:checked={all}/>全部关系</label></div></div>
 <p class="graph-key"><span>━━ 配对支持的总效应</span><span>┄┄ 模型候选</span><span class="muted">弱线：自回归/未独立验证</span></p>
 <div class="graph-workspace"><svg role="group" bind:this={svg} viewBox="-30 -20 1100 700" onpointermove={move} onpointerup={()=>drag=null} onpointercancel={()=>drag=null} aria-label="交互动态因果图">
  <defs><marker id="candidate-arrow" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" refX="8" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="context-stroke" stroke-width="2"/></marker></defs>
  <rect x="-30" y="-20" width="1100" height="700" role="presentation" fill="transparent" onpointerdown={e=>start(e,null)}/>
  <g bind:this={viewport} class="graph-viewport" transform={`translate(${pan}) scale(${zoom})`}>
  {#each geometries as e,k}<path data-source={e.i} data-target={e.j} data-start={e.start.join(',')} data-end={e.end.join(',')} class={'causal-edge '+e.type} d={e.d} marker-end="url(#candidate-arrow)" role="button" tabindex="0" aria-label={group.nodes[e.i]+'到'+group.nodes[e.j]+(e.type==='effect'?'总效应':'候选边')} onclick={()=>detail=e} onkeydown={ev=>{if(ev.key==='Enter')detail=e}}><title>{group.nodes[e.i]} → {group.nodes[e.j]} · {e.type==='effect'?'配对总效应':'模型候选'}</title></path>{/each}
  {#each group.nodes as n,i}<g data-node={i} class:chosen={selected===i} class="causal-node" transform={`translate(${points[i]})`} role="button" tabindex="0" aria-label={'节点 '+n} onpointerdown={e=>start(e,i)} onclick={()=>{selected=i;detail=null}} onkeydown={e=>{if(e.key==='Enter'){selected=i;detail=null}}}><rect x="-102" y="-34" width="204" height="68" rx="10"/><text text-anchor="middle" y="-4">{n}</text><text class="node-caption" text-anchor="middle" y="20">{['反应釜温度','冷却水出口温度','反应釜压力','反应釜液位','反应釜进料流量','冷却水控制命令','A/C进料控制命令'][i]}</text></g>{/each}
  </g>
 </svg><aside class="graph-inspector"><p class="source">当前档案 {runId} · D4固定研究结构</p><h3>{detail?group.nodes[detail.i]+' → '+group.nodes[detail.j]:group.nodes[selected]+' · 相关关系'}</h3>
 {#if detail}<p class="evidence-label">{detail.type==='effect'?'配对实验支持 · 总效应':detail.type==='candidate'?'工艺约束候选边':'自回归 / 未独立干预验证'}</p><p>{detail.type==='effect'?'D4在+1/+5个百分点、120秒命令动作范围内比较配对TEP分支，提供温度/压力响应的总路径证据。不能认作直接边或任意工况的因果定理。':'D4局部线性动态结构的候选父节点，训练拟合未消除闭环反馈或潜在混杂。没有逐边配对干预证明。'}</p><p>时间：{detail.type==='effect'?'实验动作120秒；未识别独立传播时延':'候选滞后10–60秒；非已验证传播时延'}</p>{:else}<p>拖动节点调整布局，拖动空白平移；点击关系线查看模型依据。默认仅突出所选节点，减少交叉。</p><p>父节点：{group.parents[selected].map(i=>group.nodes[i]).join('、')}</p>{/if}<p class="source">来源：D4 protocol.json、D4_INTERVENTION_VALIDATION.md。实线为额外总效应层，不替换候选结构。</p></aside></div>
</section>
<style>
 .graph-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.graph-key{display:flex;gap:20px;font-size:13px}.graph-workspace{display:grid;grid-template-columns:minmax(0,1fr) 280px}.graph-workspace svg{width:100%;touch-action:none;user-select:none;height:510px;min-height:320px}.graph-inspector{position:static;width:auto;padding:20px;background:#0d1c26;z-index:auto;border:1px solid #304956;display:block}.graph-inspector{align-self:start}.graph-inspector p{font-size:14px}.causal-edge{fill:none;stroke:#8ba6b5;stroke-width:2.5;stroke-dasharray:9 6;cursor:pointer;pointer-events:stroke}.causal-edge:hover,.causal-edge:focus{stroke:#fff;stroke-width:5}.causal-edge.effect{stroke:#7cd6be;stroke-dasharray:none;stroke-width:3.5}.causal-edge.uncertain{stroke:#627782;opacity:.5;stroke-width:1.8}.causal-node{cursor:grab}.causal-node rect{fill:#1a303d;stroke:#587989;stroke-width:2}.causal-node.chosen rect{stroke:#87dfd6;fill:#20434c}.causal-node text{font:22px Consolas;fill:#e0f1f2}.causal-node .node-caption{font:14px 'Microsoft YaHei';fill:#9fbac8}.evidence-label{color:#92d8c7}@media(max-width:1100px){.graph-workspace{grid-template-columns:1fr}.graph-inspector{padding:14px}}@media(max-width:650px){.graph-key{flex-wrap:wrap}.graph-workspace svg{min-height:320px}}
</style>
