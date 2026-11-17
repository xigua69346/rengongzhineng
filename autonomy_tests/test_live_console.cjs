const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root='src/causalverse/autonomy/console/';
test('frontend parses and uses real backend only',()=>{const s=fs.readFileSync(root+'app.js','utf8');new vm.Script(s);assert(!s.includes('Math.random'));assert(s.includes('/api/status'));assert(s.includes('CONNECTION_UNAVAILABLE'))});
test('lifecycle controls and evidence disclosure exist',()=>{const s=fs.readFileSync(root+'index.html','utf8');for(const id of ['start','pause','resume','stop','clock','ai','events','evidence'])assert(s.includes('id="'+id+'"'));assert(s.includes('180秒'));assert(s.includes('false'))});
test('polling executes in a UI-only transport fixture without reference errors',async()=>{
 const nodes=new Map();const get=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',children:[],replaceChildren(){},prepend(){},getContext(){return {clearRect(){}}}});return nodes.get(id)};
 const fixture={status:'RUNNING',wall_seconds:1,actual_rate:1,detection_status:'WAITING',identity:{episode_id:'fixture',source_mode:'UI_TEST_FIXTURE'},records:[],latest:null,cursor_gap:false};
 const sandbox={document:{getElementById:get,body:{dataset:{}}},localStorage:{getItem:()=> 'fixture'},setInterval(){},fetch:async path=>({ok:true,json:async()=>path.includes('session')?{csrf:'test'}:fixture}),console};
 vm.runInNewContext(fs.readFileSync(root+'app.js','utf8'),sandbox);await new Promise(resolve=>setImmediate(resolve));
 assert.equal(get('state').textContent,'RUNNING');assert.equal(get('ai').textContent,'WAITING');
});
