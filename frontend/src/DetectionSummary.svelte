<script>
 export let detection;export let cursor;export let detector;export let fault;
 $: t=detection.t_seconds.filter(x=>x<=cursor);
 $: pred=detection['pred_'+detector].slice(0,t.length);
 $: first=t.find((x,i)=>x>=3600&&pred[i]);
 $: intervals=[];
 $: {let out=[],start=null;t.forEach((x,i)=>{if(pred[i]&&start===null)start=x;if(start!==null&&(!pred[i]||i===t.length-1)){out.push([start,Math.min(cursor,pred[i]?x+180:x)]);start=null}});intervals=out}
</script>
<div class="event-timeline"><div><b>故障计划</b><strong>{fault?'3600 s':'无注入'}</strong><span>{fault?(cursor<3600?'尚未到达':'实验已启用'):'正常对照'}</span></div><div><b>首次报警</b><strong>{first===undefined?'未检出':first+' s'}</strong><span>当前所选检测器</span></div><div><b>当前回放</b><strong>{cursor} s</strong><span>截至此时刻的证据</span></div></div><div class="summary-grid"><div class="summary-card"><small>截至当前回放的检测样本</small><strong>{t.length}</strong><span>180秒采样，非逐秒判定</span></div><div class="summary-card"><small>{fault?'故障注入后首次报警':'3600秒后首次报警'}</small><strong>{first===undefined?'尚未检出':first+' s'}</strong><span>{first===undefined?'不将漏检记作零延迟':fault?'距计划注入 '+(first-3600)+' 秒':'正常运行：此项不是故障检出'}</span></div><div class="summary-card"><small>报警持续区段</small><strong>{intervals.length}</strong><span>离散180秒网格下的区段</span></div></div>
<section class="panel"><div class="panel-title">如何理解这些信号</div><div class="explain-grid"><p><b>T²</b>：在正常主成分空间中的偏离程度。</p><p><b>SPE</b>：正常子空间无法重构的残差能量。</p><p><b>Threshold</b>：单变量超出正常统计基准的最大分数。</p></div><p>竖向米色虚线：故障计划时刻（仅故障实验）；黄色虚线：首次报警；水平虚线：控制限1。</p><p>图中均除以原控制限，超过1表示统计报警；PCA联合判定为T²或SPE越界。贡献大不等于故障根因。</p><details open><summary>查看报警持续区间（截至当前时刻）</summary>{#each intervals as pair}<span class="interval-chip">{pair[0]}–{pair[1]} s</span>{/each}{#if !intervals.length}<p>尚无报警区段</p>{/if}</details><p class="source">{fault?'已知实验计划：故障3600秒注入（离线标签，不参与检测）':'正常实验，无故障注入；3600秒仅为统一评估起点'}。首次报警为采样网格记录，不推断亚采样延迟。</p></section>
