<script>
 import Chart from './Chart.svelte';export let intervalData;
</script>
<div class="prediction-panels">{#each ['T9 · 反应釜温度 / °C','C21 · 冷却水出口温度 / °C','P7 · 反应釜压力 / kPa'] as target,j}<section class="panel prediction-panel"><Chart title={target} xTitle="预测起点5400秒之后的时域 / 秒" xRange={[0,600]} height={330} data={[
 {x:intervalData.horizons,y:intervalData.joint_lower.map(r=>r[j]),name:'区间下界',legendrank:3,line:{color:'#789bb3',width:1.4,dash:'dot'}},
 {x:intervalData.horizons,y:intervalData.joint_upper.map(r=>r[j]),name:'区间上界',legendrank:4,fill:'tonexty',fillcolor:'rgba(120,155,179,.14)',line:{color:'#789bb3',width:1.4,dash:'dot'}},
 {x:intervalData.horizons,y:intervalData.prediction.map(r=>r[j]),name:'模型预测',legendrank:2,mode:'lines+markers',line:{color:'#77d5c1',width:2}},
 {x:intervalData.horizons,y:intervalData.truth.map(r=>r[j]),name:'实际观测（仿真）',legendrank:1,mode:'lines+markers',line:{color:'#efbd79',width:2}}]}/><p class="source">固定检查点10/30/60/120/300/600秒；上下界来自原始联合校准区间，宽度未更改。</p></section>{/each}</div>
