export const INITIAL_POINTS=[[450,115],[790,170],[450,425],[135,125],[135,350],[790,445],[135,550]];
export const initialPoints=()=>INITIAL_POINTS.map(p=>[...p]);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
// Ports sit on the actual 204x68 node outline, outside rounded corners.
export function boundary(p,c){let dx=c[0]-p[0],dy=c[1]-p[1];if(Math.abs(dx)+Math.abs(dy)<1e-8)dx=1;
 if(Math.abs(dx)/102>=Math.abs(dy)/34)return [p[0]+Math.sign(dx)*102,p[1]+clamp(dy/Math.abs(dx)*102,-24,24)];
 return [p[0]+clamp(dx/Math.abs(dy)*34,-92,92),p[1]+Math.sign(dy)*34];}
export function edgeGeometry(e,points){const a=points[e.i],b=points[e.j];
 if(e.i===e.j){const start=[a[0]-50,a[1]-34],end=[a[0]+50,a[1]-34];return {start,end,d:`M${start} C${a[0]-140},${a[1]-130} ${a[0]+140},${a[1]-130} ${end}`};}
 const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1,straight=e.type==='candidate'&&Math.abs(dy)<35&&Math.abs(dx)>220,offset=straight?0:e.type==='effect'?95:40;
 const normal=[-dy/len,dx/len],c1=[a[0]+dx*.28+normal[0]*offset,a[1]+dy*.28+normal[1]*offset],c2=[a[0]+dx*.72+normal[0]*offset,a[1]+dy*.72+normal[1]*offset];
 const start=boundary(a,c1),end=boundary(b,c2);
 return {start,end,d:straight?`M${start} L${end}`:`M${start} C${c1} ${c2} ${end}`};}
