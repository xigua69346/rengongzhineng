<script>
 export let intervalData;export let summary;
 $: widths=[0,1,2].map(j=>intervalData.joint_upper.reduce((a,r,i)=>a+r[j]-intervalData.joint_lower[i][j],0)/6);
</script>
<div class="summary-grid">{#each ['T9 / °C','C21 / °C','P7 / kPa'] as target,j}<div class="summary-card"><small>{target} · 全独立测试平均MAE</small><strong>{summary.MAE[j].toFixed(3)}</strong><span>当前历史条件区间平均全宽：{widths[j].toFixed(3)}</span><span>联合覆盖 {summary.joint_coverage*100}% · 20个种子</span></div>{/each}</div>
<div class="notice">区间越宽，表示当前预测对未来状态的不确定性越大。这里保留原始上下界；20/20覆盖的精确95%区间为83.2%–100%，不能当必然覆盖保证。MAE为全测试汇总，宽度为当前选中实验，二者统计口径不同。</div>
