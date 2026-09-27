
import {outline} from './motion.mjs';
const rows=document.querySelector('#rows');let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
const gaps=[0,8,38,65],titles=['靠近 → 黏连 → 拉远断开','近距离：饱满连接','远距离：细颈连接','超过阈值：连接断开'];
rows.innerHTML=gaps.map((_,i)=>`<g fill="url(#tint)" transform="translate(0 ${i*135})"><text x="150" y="24" text-anchor="middle">${titles[i]}</text><path id="p${i}" stroke="#a7b99a" stroke-opacity=".55"/><use href="#p${i}" fill="url(#light)"/><text id="a${i}" y="90" text-anchor="middle">资料</text><text id="b${i}" y="90" text-anchor="middle">写作</text></g>`).join('');
function draw(i,gap){const d=74+gap;document.querySelector('#p'+i).setAttribute('d',outline({x:150-d/2,y:85,r:37},{x:150+d/2,y:85,r:37}));document.querySelector('#a'+i).setAttribute('x',150-d/2);document.querySelector('#b'+i).setAttribute('x',150+d/2);}
gaps.forEach((gap,i)=>draw(i,gap));
let phase=0,last=performance.now();function frame(now){if(!paused){phase+=(now-last)/1200;draw(0,20+52*Math.sin(phase));}last=now;requestAnimationFrame(frame)}requestAnimationFrame(frame);
const button=document.querySelector('#pause');function label(){button.textContent=paused?'播放动画':'暂停动画'}label();button.onclick=()=>{paused=!paused;label()};
