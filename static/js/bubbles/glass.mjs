import * as THREE from '../../vendor/three/three.module.js';
import {SuppliedBubbleMaterial} from './supplied-material.mjs';
export function glassFrame({connected=false,burst=0}={}){const t=Math.min(1,burst/560);return {visible:!connected,opacity:burst>0?.1*Math.max(0,1-Math.sin(Math.PI*t)*1.4):.1,scale:1+(burst>0?.45*Math.sin(Math.PI*t):0)}}
// DOM owns content, focus and hit testing. This canvas owns only the optical shell.
export function installGlass(canvasArea,layer){
 if(!window.WebGLRenderingContext&&!window.WebGL2RenderingContext)return;
 let renderer;
 try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});}catch{return;}
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.setClearColor(0x000000,0);
 renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
 const surface=renderer.domElement;surface.id='glass-bubbles';surface.setAttribute('aria-hidden','true');canvasArea.prepend(surface);
 const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-1,1,1,-1,.1,3000);camera.position.z=1000;
 const studio=new THREE.Scene();studio.background=new THREE.Color('#cbd7e6');
 const room=new THREE.Mesh(new THREE.BoxGeometry(12,12,12),new THREE.MeshBasicMaterial({color:'#a8b4c3',side:THREE.BackSide}));studio.add(room);
 const cards=[[-3,3,2,3,1.5,'#ffffff'],[3,1,1,1,4,'#fff5ec'],[0,-3,2,5,.35,'#c6b5f1'],[0,4,-3,6,2,'#ffffff']];
 for(const [x,y,z,w,h,color]of cards){const card=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide}));card.position.set(x,y,z);card.lookAt(0,0,0);studio.add(card)}
 const pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromScene(studio,0);scene.environment=environment.texture;
 studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose()});pmrem.dispose();
 scene.add(new THREE.HemisphereLight('#ffffff','#c9c5df',2));
 const light=new THREE.DirectionalLight('#fff7ef',3);light.position.set(-300,400,500);scene.add(light);
 const geometry=new THREE.SphereGeometry(1,48,32),objects=new Map();let width=0,height=0,last=performance.now(),frameId,suspended=false,disposed=false;
 const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches||document.documentElement.classList.contains('reduced-motion');
 function frame(now){
  if(suspended||disposed||!surface.isConnected)return;
  const area=canvasArea.getBoundingClientRect(),dt=Math.min(.05,(now-last)/1000);last=now;
  if(width!==area.width||height!==area.height){width=area.width;height=area.height;renderer.setSize(width,height,false);camera.left=-width/2;camera.right=width/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix()}
  const alive=new Set();
  for(const node of layer.children){const id=node.dataset.id;if(!id)continue;alive.add(id);let entry=objects.get(id);
   if(!entry){const material=new SuppliedBubbleMaterial({color:0xffffff});material.rainbowStrength=1.6;material.rimBoost=.55;material.envMapIntensity=1.6;material.wobbleScale=1.65;material.depthWrite=false;const mesh=new THREE.Mesh(geometry,material);mesh.rotation.set(.2,objects.size*.7,.12);scene.add(mesh);entry={mesh,material,time:objects.size*1.7,burstStart:0};objects.set(id,entry)}
   const rect=node.getBoundingClientRect(),paused=reduced()||node.matches(':hover,:focus')||node.classList.contains('dragging')||node.classList.contains('matching');
   if(!paused)entry.time+=dt;entry.material.timeUniform.value=entry.time;
   const bursting=node.classList.contains('bursting')&&!reduced();if(bursting&&!entry.burstStart)entry.burstStart=now;if(!bursting)entry.burstStart=0;
   const visual=glassFrame({connected:node.classList.contains('connected'),burst:entry.burstStart?now-entry.burstStart:0});entry.mesh.visible=visual.visible;entry.material.opacity=visual.opacity;entry.material.rimBoost=.55*(visual.opacity/.1);
   const css=getComputedStyle(node),stretch=node.classList.contains('dragging')&&!reduced()?Number(css.getPropertyValue('--drag-stretch'))||1:1;
   entry.mesh.rotation.z=node.classList.contains('dragging')?-(parseFloat(css.getPropertyValue('--drag-angle'))||0)*Math.PI/180:.12;
   entry.mesh.position.set(rect.left+rect.width/2-area.left-width/2,height/2-(rect.top+rect.height/2-area.top),0);
   entry.mesh.scale.set(rect.width/2*stretch*visual.scale,rect.height/2/stretch*visual.scale,rect.width/2*.8);
  }
  for(const [id,entry]of objects)if(!alive.has(id)){scene.remove(entry.mesh);entry.material.dispose();objects.delete(id)}
  try{renderer.render(scene,camera);canvasArea.classList.add('glass-ready');surface.dataset.state='ready'}catch{canvasArea.classList.remove('glass-ready');surface.dataset.state='failed';return}
  frameId=requestAnimationFrame(frame);
 }
 surface.addEventListener('webglcontextlost',e=>{e.preventDefault();cancelAnimationFrame(frameId);canvasArea.classList.remove('glass-ready');surface.dataset.state='lost'});
 surface.addEventListener('webglcontextrestored',()=>{last=performance.now();frameId=requestAnimationFrame(frame)});
 frameId=requestAnimationFrame(frame);
 window.addEventListener('pagehide',event=>{cancelAnimationFrame(frameId);suspended=true;if(event.persisted)return;disposed=true;canvasArea.classList.remove('glass-ready');for(const o of objects.values())o.material.dispose();geometry.dispose();environment.dispose();renderer.dispose()});
 window.addEventListener('pageshow',event=>{if(event.persisted&&!disposed){suspended=false;last=performance.now();frameId=requestAnimationFrame(frame)}});
}
