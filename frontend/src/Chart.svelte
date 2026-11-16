<script>
 import {onMount} from 'svelte';
 export let data=[];export let title='';export let shapes=[];export let height=310;export let xTitle='仿真时间 / 秒';export let xRange=undefined;
 $: axisTitle=title.includes('预测起点')?'预测起点后时域 / 秒':xTitle;
 let element;let ready=false;
 onMount(()=>{ready=true;return ()=>window.Plotly?.purge(element)});
 $: if(ready && element) window.Plotly.react(element,data.map(trace=>({...trace,hovertemplate:'%{x}<br>%{y:.3f}<extra>%{fullData.name}</extra>'})),{height,paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{size:13,color:'#afc0cc',family:'Consolas,Microsoft YaHei'},margin:{l:65,r:26,t:80,b:55},xaxis:{gridcolor:'#25313b',title:{text:axisTitle},range:xRange},yaxis:{gridcolor:'#25313b',automargin:true},legend:{orientation:'h',y:1.12,yanchor:'bottom',font:{size:13}},shapes,hovermode:'x unified',colorway:['#72d4b2','#e9b76c','#8ab4e8','#d3a6b5']},{responsive:true,displaylogo:false});
</script>
<div class="chart-frame"><h3 class="chart-heading">{title}</h3><div bind:this={element} class="chart" aria-label={title}></div></div>
<style>.chart-heading{font-size:17px;line-height:1.6;margin:12px 0 2px;color:#d4e4ea}.chart-frame{min-width:0}</style>
