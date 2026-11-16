const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const crypto=require('node:crypto');const path=require('node:path');
const view=require('../src/causalverse/evidence_s2/console/ai.js');
const root=path.resolve(__dirname,'..');
const good=view.archives.find(a=>a.record.status==='VALIDATED').record;
test('archives contain genuine success rejection and missing-key records',()=>{
 assert.deepEqual(view.archives.map(a=>a.record.status),['VALIDATED','REJECTED','NOT_CONFIGURED']);
 const id=good.request_id;const batches=fs.readdirSync(path.join(root,'artifacts/ai_s2_runs'));
 const source=batches.map(b=>path.join(root,'artifacts/ai_s2_runs',b,'ai',id+'_audit.json')).find(p=>fs.existsSync(p));
 const bytes=fs.readFileSync(source);assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),view.archives[0].source_sha256);
 const original=JSON.parse(bytes);assert.deepEqual(good.analysis,original.analysis);assert.deepEqual(good.usage,original.usage);
});
test('five analysis types have readable titles',()=>{
 assert.deepEqual(good.analysis.map(i=>view.summarize(i).title),['异常指标分析','报警证据分析','检测器分歧分析','时间变化分析','根因证据不足说明']);
});
test('display preserves exact verified values and clock',()=>{
 const s=view.summarize(good.analysis[0]);assert.equal(s.values[0].value,57.86709703253733);assert.deepEqual(s.times,[4860]);
 assert.deepEqual(view.summarize(good.analysis[2]).values.map(v=>v.value),[true,false]);
});
test('fact count and unique evidence count are distinct',()=>{
 const s=view.summarize(good.analysis[2]);assert.equal(s.factCount,2);assert.equal(s.evidenceCount,1);
});
test('root-cause limitation remains insufficient evidence',()=>{
 assert.equal(view.summarize(good.analysis[4]).validation,'INSUFFICIENT_EVIDENCE');
 assert.equal(good.analysis[4].optimization_allowed,false);
});
test('historical VALIDATED is never marked as current success',()=>{
 const s=view.sourceInfo(good,'archive',Date.now());assert.equal(s.kind,'archive');assert.match(s.note,/历史成功不代表当前实时调用成功/);
});
test('existing backend result is labelled cached rather than new call',()=>{
 assert.equal(view.sourceInfo(good,'current',Date.now()).kind,'cached');
 assert.equal(view.sourceInfo({...good,requested_at_utc:null},'current',Date.now()).kind,'cached');
});
test('even recent results do not assert a new upstream call without explicit backend cache information',()=>{
 const now=Date.now();const s=view.sourceInfo({...good,requested_at_utc:new Date(now).toISOString()},'current',now);
 assert.equal(s.kind,'received');assert.match(s.note,/不据本次获取断言新增上游调用/);
});
test('archived rejected and unavailable results never render accepted cards',()=>{
 for(const status of ['REJECTED','UNAVAILABLE','NOT_CONFIGURED'])assert.deepEqual(view.visibleFindings({...good,status}),[]);
});
test('live invocation requires explicit mode fresh D3 context and configuration',()=>{
 const s={mode:'current',busy:false,dirty:false,chain:'D3',configured:true};assert.equal(view.mayCallLive(s),true);
 for(const change of [{mode:'archive'},{busy:true},{dirty:true},{chain:'D511'},{chain:null},{configured:false}])assert.equal(view.mayCallLive({...s,...change}),false);
});
