'use strict';
let csrf='',episode=localStorage.getItem('s3_episode')||'',cursor=-1,latestInference=null,points=[],busy=false;
const $=id=>document.getElementById(id),text=(id,value)=>{$(id).textContent=value};
async function request(path,data){const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(data)}:{});const v=await r.json();if(!r.ok)throw Error(v.error||r.status);return v}
async function control(op){await request('/api/control',{episode_id:episode,op});text('notice','已申请'+op+'，以生产进程回执为准。')}
function line(s){const li=document.createElement('li');li.textContent=s;$('timeline').prepend(li);while($('timeline').children.length>15)$('timeline').lastChild.remove()}
function draw(){const c=$('plot'),x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);if(points.length<2)return;const lo=Math.min(...points)-.01,hi=Math.max(...points)+.01;x.strokeStyle='#355058';for(let i=1;i<4;i++){x.beginPath();x.moveTo(0,i*50);x.lineTo(900,i*50);x.stroke()}x.strokeStyle='#93d4b6';x.lineWidth=2;x.beginPath();points.forEach((v,i)=>{const px=i/(points.length-1)*880+10,py=185-(v-lo)/(hi-lo)*170;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();x.fillStyle='#afc6c2';x.fillText(hi.toFixed(3)+' °C',8,12);x.fillText(lo.toFixed(3)+' °C',8,198)}
async function poll(){
 const requestedEpisode=episode;
 if(!episode||busy)return;busy=true;
 try{
  const v=await request('/api/status?episode='+encodeURIComponent(episode)+'&after='+cursor);
  if(requestedEpisode!==episode)return;text('state',v.status);if($('notice').textContent.startsWith('未使用历史NPZ'))text('notice','已连接本Episode真实采集记录；暂停或结束时显示最后观测，不代表持续推进。');document.body.dataset.running=String(v.status==='RUNNING');text('wall',v.wall_seconds.toFixed(1)+' s');text('factor',v.actual_rate.toFixed(2)+'×');
  text('identity',v.identity.episode_id+' · '+v.identity.source_mode);
  if(v.cursor_gap)text('notice','游标缺口：正在从已验证账本补读。');
  for(const r of v.records){
   cursor=r.seq;
   if(r.kind==='observation'){points.push(r.payload.measurements[8]);if(points.length>600)points.shift()}
   else if(r.kind==='inference'){
    latestInference=r.payload;line('AI真实推理 @ '+r.payload.observation_time.at(-1)+' s');
   }else if(r.kind==='anomaly_event'){text('events',r.payload.status+' · '+(r.payload.first_alarm_time===undefined?'未触发；无在线真值，不能判定漏报/误报。':'首次报警 '+r.payload.first_alarm_time+' s / 最近 '+r.payload.latest_time+' s；变量贡献 '+r.payload.variables.join('、')+'。候选贡献不是根因。'));line('自动事件 '+r.payload.status+' @ '+r.payload.latest_time+' s')}
   else line(r.kind+' · '+(r.payload.status||r.payload.reason||''));
  }
  if(latestInference){const a=latestInference.arrays,i=a.T2.length-1;text('ai','PCA + Threshold · '+latestInference.elapsed_ms.toFixed(3)+' ms');$('scores').replaceChildren();
   for(const [k,val] of [['T²',a.T2[i]],['SPE',a.SPE[i]],['Threshold',a.threshold_score[i]],['PCA报警',a.pred_PCA[i]],['Threshold报警',a.pred_Threshold[i]]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=String(val);$('scores').append(dt,dd)}
  }else text('ai',v.detection_status);
  const o=v.latest;if(o){const m=o.measurements;text('clock',o.measurement_time+' s');text('quality',o.quality);
   for(const [id,value] of [['t9','T9 '+m[8].toFixed(3)+' °C'],['p7','P7 '+m[6].toFixed(2)+' kPa'],['c21','C21 '+m[20].toFixed(3)+' °C'],['u10','U10 '+o.commands[9].toFixed(3)+' %命令'],['l8','L8 '+m[7].toFixed(2)+' %'],['f6',m[5].toFixed(3)+' kscmh']])text(id,value);
   text('freshness','测量 '+o.measurement_time+' s / 状态 '+o.state_time+' s；气体分析样本年龄 '+o.freshness.gas_age_seconds+' s / 产品 '+o.freshness.product_age_seconds+' s；延迟采样保持。');
   text('evidence',JSON.stringify({observation:o,inference:latestInference},null,2));draw();
  }
 }catch(e){text('notice','连接/访问异常：'+e.message+'；原值仅为最后已知观测，不代表生产正常。');text('state','CONNECTION_UNAVAILABLE')}
 finally{busy=false}
}
$('start').onclick=async()=>{try{const s=await request('/api/start',{rate:Number($('rate').value),limit:14400});episode=s.episode_id;localStorage.setItem('s3_episode',episode);cursor=-1;points=[];latestInference=null;for(const id of ['clock','quality','t9','p7','c21','u10','l8','f6'])text(id,'—');text('freshness','WAITING：本Episode尚无观测');text('evidence','WAITING');draw();$('scores').replaceChildren();$('timeline').replaceChildren();text('events','WAITING：尚未到达本Episode的检测网格。');text('ai','WAITING_WARMUP_OR_180S_GRID');text('notice','真实TEP生产已申请启动；原PI运行，无AI自动调节。');await poll()}catch(e){text('notice',e.message)}};
for(const op of ['pause','resume','stop'])$(op).onclick=()=>control(op).catch(e=>text('notice',e.message));
$('inject').onclick=()=>request('/api/operator-fault',{episode_id:episode,fault_id:Number($('fault').value)}).then(()=>text('notice','人工故障注入已申请；AI仅根据传感器观测检测，不读取故障标签。')).catch(e=>text('notice',e.message));
request('/api/session').then(s=>{csrf=s.csrf;poll();setInterval(poll,1000)}).catch(e=>text('notice',e.message));
