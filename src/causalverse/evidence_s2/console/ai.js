'use strict';
let aiContext=null,aiConfig=null,aiDirty=false,aiBusy=false;
function aiEnable(){document.getElementById('ai-run').disabled=aiBusy||aiDirty||!aiContext||aiContext.chain!=='D3'||!aiConfig?.api_configured;}
window.addEventListener('evidence-context',async event=>{
  aiContext=event.detail;aiConfig=null;document.getElementById('ai-output').replaceChildren();
  try{aiConfig=await api('/api/ai/session');document.getElementById('ai-state').textContent=`DeepSeek模型：${aiConfig.model} / ${aiContext.chain==='D3'?(aiConfig.api_configured?'就绪，尚未调用':'NOT_CONFIGURED：后端缺少Key，未进行真实调用'):'仅支持D3异常解释'}。机器学习结果继续可用。`;}
  catch{document.getElementById('ai-state').textContent='AI配置不可用；机器学习证据保持可读。';}
  aiEnable();
});
window.addEventListener('evidence-dirty',event=>{aiDirty=event.detail.dirty;aiEnable();if(aiDirty)document.getElementById('ai-state').textContent='条件已变更：先创建匹配快照，再请求AI分析。';});
document.getElementById('ai-run').addEventListener('click',async()=>{
  if(!aiContext||!aiConfig||aiDirty)return;
  const requested=aiContext.context_id;aiBusy=true;aiEnable();document.getElementById('ai-state').textContent=`正在请求 ${aiConfig.model}，等待验证完整结构化输出…`;
  try{
    const r=await api('/api/ai/explain',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':aiConfig.csrf},body:JSON.stringify({context_id:requested})});
    if(aiContext.context_id!==requested||aiDirty)return;
    document.getElementById('ai-state').textContent=`${r.model} / ${r.status} / ${r.elapsed_ms.toFixed(1)}ms / 请求 ${r.request_id} / ${r.api_call_made?'已发起上游请求':'未调用API'}`;
    const output=document.getElementById('ai-output');output.replaceChildren();
    const note=document.createElement('p');note.textContent='DeepSeek负责证据选择与结构化分析；以下中文释义和数值由后端校验回填。不是未经验证的AI自由文本。';output.append(note);
    for(const item of r.analysis){const card=document.createElement('article');card.className='ai-claim';const text=document.createElement('p');text.textContent=item.text;const refs=document.createElement('pre');refs.textContent=JSON.stringify(item.claim,null,2);card.append(text,refs);output.append(card);}
    const audit=document.createElement('pre');audit.textContent=JSON.stringify({usage:r.usage,cost_status:r.cost_status,error_code:r.error_code,optimization_allowed:false,context_id:r.context_id},null,2);output.append(audit);
    if(r.status!=='VALIDATED'){const failure=document.createElement('p');failure.textContent='未得到可验证的AI分析。保留上方原始模型结果，不生成替代AI答复。';output.append(failure);}
  }catch{document.getElementById('ai-state').textContent='AI服务不可用；没有生成AI分析，原始模型结果保持不变。';}
  finally{aiBusy=false;aiEnable();}
});
