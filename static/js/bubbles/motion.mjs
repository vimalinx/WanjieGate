// Tangent geometry adapted from Paper.js Meta Balls, originally by SATO Hiroyuki.
// https://paperjs.org/examples/meta-balls/ — MIT attribution: docs/licenses/paperjs.txt
export const motion={enterGap:32,exitGap:58,duration:780,elasticity:1.08,handleRate:2.4,maxStretch:.12};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export function pickTarget(a,items,current){
 const gap=b=>Math.hypot(b.x-a.x,b.y-a.y)-a.r-b.r;
 const held=items.find(b=>b.id===current);
 if(held&&gap(held)<motion.exitGap)return held;
 return items.filter(b=>gap(b)<motion.enterGap).sort((b,c)=>gap(b)-gap(c))[0]||null;
}
const polar=(angle,r)=>[Math.cos(angle)*r,Math.sin(angle)*r];
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const point=(o,angle)=>add([o.x,o.y],polar(angle,o.r));
export function geometry(a,b){
 const d=Math.hypot(b.x-a.x,b.y-a.y),sum=a.r+b.r,gap=d-sum;
 if(a.r<=0||b.r<=0||d<=Math.abs(a.r-b.r)||gap>=motion.exitGap)return null;
 const acos=n=>Math.acos(clamp(n,-1,1));
 const u1=d<sum?acos((a.r*a.r+d*d-b.r*b.r)/(2*a.r*d)):0;
 const u2=d<sum?acos((b.r*b.r+d*d-a.r*a.r)/(2*b.r*d)):0;
 const angle=Math.atan2(b.y-a.y,b.x-a.x),tangent=acos((a.r-b.r)/d);
 const v=.5*clamp((motion.exitGap-gap)/motion.exitGap,0,1);
 const aa=angle+u1+(tangent-u1)*v,ab=angle-u1-(tangent-u1)*v;
 const ba=angle+Math.PI-u2-(Math.PI-u2-tangent)*v,bb=angle-Math.PI+u2+(Math.PI-u2-tangent)*v;
 const p1a=point(a,aa),p1b=point(a,ab),p2a=point(b,ba),p2b=point(b,bb);
 const rate=Math.min(v*motion.handleRate,Math.hypot(p1a[0]-p2a[0],p1a[1]-p2a[1])/sum)*Math.min(1,d*2/sum);
 return {p1a,p1b,p2a,p2b,c1:add(p1a,polar(aa-Math.PI/2,a.r*rate)),c2:add(p2a,polar(ba+Math.PI/2,b.r*rate)),c3:add(p2b,polar(bb-Math.PI/2,b.r*rate)),c4:add(p1b,polar(ab+Math.PI/2,a.r*rate)),largeA:2*Math.PI-(aa-ab)>Math.PI?1:0,largeB:ba-bb>Math.PI?1:0};
}
export function bridge(a,b){const g=geometry(a,b);if(!g)return '';return `M ${g.p1a} C ${g.c1} ${g.c2} ${g.p2a} L ${g.p2b} C ${g.c3} ${g.c4} ${g.p1b} Z`;}
const circle=o=>`M ${o.x-o.r},${o.y} A ${o.r},${o.r} 0 1 0 ${o.x+o.r},${o.y} A ${o.r},${o.r} 0 1 0 ${o.x-o.r},${o.y} Z`;
export function outline(a,b){
 const g=geometry(a,b);if(!g)return Math.hypot(b.x-a.x,b.y-a.y)<=Math.abs(a.r-b.r)?circle(a.r>=b.r?a:b):circle(a)+' '+circle(b);
 return `M ${g.p1a} C ${g.c1} ${g.c2} ${g.p2a} A ${b.r},${b.r} 0 ${g.largeB} 0 ${g.p2b} C ${g.c3} ${g.c4} ${g.p1b} A ${a.r},${a.r} 0 ${g.largeA} 0 ${g.p1a} Z`;
}
export function deformation(vx,vy){return {angle:Math.atan2(vy,vx)*180/Math.PI,stretch:1+Math.min(motion.maxStretch,Math.hypot(vx,vy)*.035)};}
