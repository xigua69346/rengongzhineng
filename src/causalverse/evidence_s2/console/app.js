'use strict';
const $ = id => document.getElementById(id);
let csrf, catalog;
let renderedSelection=null;
const selection=()=>JSON.stringify({selection_id:$('case').value,as_of:Number($('time').value),window:Number($('window').value)});
function dirty(){
  const changed=renderedSelection!==null && renderedSelection!==selection();
  $('state').textContent=changed?'待更新：当前显示上一份快照，请重新计算':'已封存 / SHA256 校验';
  $('state').classList.toggle('dirty',changed);
  $('cards').classList.toggle('stale',changed);window.dispatchEvent(new CustomEvent('evidence-dirty',{detail:{dirty:changed}}));
}
const names = {'detection':'异常检测 / PCA + Threshold','diagnosis.static':'机制识别 / Static','diagnosis.VAR':'机制识别 / VAR','diagnosis.logistic':'机制识别 / Logistic','prediction.action':'条件预测 / Action','prediction.delta':'条件预测 / Delta','prediction':'条件预测'};
async function api(path, options) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '服务不可用');
  return result;
}
function choices() {
  $('case').replaceChildren();
  catalog.filter(c => c.chain === $('chain').value).forEach(c => {
    const option = document.createElement('option'); option.value=c.selection_id;option.textContent=c.alias;$('case').append(option);
  });
  $('time').max = $('chain').value === 'D3' ? '14399' : '6120';
}
function render(context) { window.dispatchEvent(new CustomEvent('evidence-context',{detail:{context_id:context.context_id,chain:context.chain}}));
  $('identity').textContent=`${context.alias} · ${context.chain} · as_of=${context.as_of}s · context_id=${context.context_id} · 历史仿真`;
  $('cards').replaceChildren();
  context.evidence.forEach(e => {
    const card=document.createElement('article');card.className='card';
    const head=document.createElement('div');head.className='card-head';
    const title=document.createElement('h3');title.textContent=names[e.kind] || e.kind;
    const badge=document.createElement('span');badge.className='badge'+(e.status==='INFERRED'?'':' warn');badge.textContent=e.status;
    head.append(title,badge);card.append(head);
    const id=document.createElement('p');id.className='eid';id.textContent=`evidence_id ${e.evidence_id}\nSHA256 ${e.payload_sha256}`;card.append(id);
    const description=document.createElement('p');description.className='summary';
    if(e.kind.startsWith('prediction.') && e.status==='INFERRED') description.textContent=e.data.records.map(r=>`Δ${r.delta}：${r.support_status} / ${r.uncertainty_status} / 优化未授权`).join('；');
    else if(e.kind.startsWith('diagnosis.') && e.status==='INFERRED') description.textContent=e.data.records.map(r=>`候选 ${r.candidates.join('、')||'空集'}；${r.refused?'拒绝唯一判断':'模型内单一候选'}。评分不是概率。`).join('；');
    else if(e.kind==='detection' && e.status==='INFERRED') description.textContent=`实际重算 ${(e.data.arrays.observation_time||[]).length} 个可用检测时刻；贡献度及报警逐项保留。`;
    else description.textContent=e.status==='WAITING'?'观测窗口未完整，等待数据。':e.data.reason?`当前数据链未注册此功能。原始原因码：${e.data.reason}`:'没有可用证据；未填补或推断缺失结果。';
    card.append(description);
    const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='查看完整数值、模型参数哈希与审计';pre.textContent=JSON.stringify(e,null,2);details.append(summary,pre);card.append(details);$('cards').append(card);
  });
}
$('chain').addEventListener('change',()=>{choices();dirty();});
['case','time','window'].forEach(id=>$(id).addEventListener('input',dirty));
['case','window'].forEach(id=>$(id).addEventListener('change',dirty));
$('build').addEventListener('click',async()=>{
  $('build').disabled=true;$('state').textContent='正在执行冻结模型…';
  const submitted=selection();
  try {const context=await api('/api/contexts',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:submitted});render(context);renderedSelection=submitted;dirty();}
  catch(error){$('state').textContent='请求失败：'+error.message;}
  finally{$('build').disabled=false;}
});
(async()=>{try{csrf=(await api('/api/session')).csrf;catalog=await api('/api/catalog');choices();$('build').disabled=false;$('state').textContent='准备就绪 / 无 API Key';}catch(error){$('state').textContent='初始化失败：'+error.message;}})();
