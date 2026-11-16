<script>
 import {onMount} from 'svelte';import Chart from './Chart.svelte';
 export let runs;export let trajectory;export let cursor;
 let other='test_f04_00',second=null,error='',node=0,token=0;
 function stats(rows){let n=Math.min(cursor+1,rows.length),sum=0,min=Infinity,max=-Infinity;for(let i=0;i<n;i++){let v=rows[i][node];sum+=v;min=Math.min(min,v);max=Math.max(max,v)}return [sum/n,min,max,rows[n-1][node],rows[n-1][node]-rows[0][node]]}
 const names=['反应釜温度 / °C','冷却水出口温度 / °C','反应釜压力 / kPa','冷却水阀命令 / %'];
 async function load(){let id=++token;second=null;error='';try{let r=await fetch('/api/trajectory?run='+other);if(!r.ok)throw Error('对比轨迹不可用');let d=await r.json();if(id===token)second=d}catch(e){if(id===token)error=e.message}}
 onMount(load);
 $: times=trajectory.time.filter(t=>t<=cursor&&t%10===0);
</script>
<section class="panel"><div class="panel-title">历史实验对比 · 最多两条轨迹</div><div class="toolbar"><label>比较变量<select bind:value={node}>{#each names as n,i}<option value={i}>{n}</option>{/each}</select></label><label>第二条实验<select bind:value={other} onchange={load}>{#each runs as r}<option value={r.dataset_run_id}>{r.dataset_run_id} · seed {r.seed}</option>{/each}</select></label></div>
 <p>当前：{trajectory.run.dataset_run_id} / seed {trajectory.run.seed} / 离线故障标签 {trajectory.run.fault_id||'正常'}。{#if second}对比：{second.run.dataset_run_id} / seed {second.run.seed} / 标签 {second.run.fault_id||'正常'}。{/if}</p>
 {#if error}<p role="alert">{error}</p><button onclick={load}>重试对比</button>{:else if !second}<p>正在读取第二条真实档案…</p>{:else}<Chart title={names[node]} data={[{x:times,y:times.map(t=>trajectory.values[t][node]),name:trajectory.run.dataset_run_id,mode:'lines',line:{color:'#72d4b2',width:2}},{x:times,y:times.map(t=>second.values[t]?.[node]),name:second.run.dataset_run_id,mode:'lines',line:{dash:'dot',color:'#e9b76c',width:2}}]}/>{/if}
 {#if second}<div class="comparison-stats"><p>观测统计 · {names[node]} · 0–{cursor}秒 / 原始1秒记录（非模型评价指标）</p><table><thead><tr><th>当前变量</th><th>当前实验（绿色）</th><th>对比实验（橙色）</th></tr></thead><tbody>{#each ['均值','最小值','最大值','当前值','较起点变化'] as name,i}<tr><td>{name}</td><td>{stats(trajectory.values)[i].toFixed(3)}</td><td>{stats(second.values)[i].toFixed(3)}</td></tr>{/each}</tbody></table></div>{/if}
 <div class="history-timeline"><span>0秒 / 初始化</span><span>1800秒 / 预热结束</span><span>3600秒 / 当前{trajectory.run.fault_id?'计划注入':'正常评估'}；对比{second?.run.fault_id?'计划注入':'正常评估'}</span><span>{cursor}秒 / 当前</span></div><p class="source">按绝对仿真时间对齐，仅展示截至回放时刻的观测。故障标签仅为离线档案信息，比较图不重新运行诊断。</p></section>
