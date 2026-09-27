import {executionFor} from './execution.mjs';
const intentMode=window.location.pathname==='/launcher';
import {installGlass} from './glass.mjs';
import {destinationFor,previewContent,safeDestination} from './handoff.mjs';
import {motion,pickTarget,outline,deformation} from './motion.mjs';
import {toolURL} from './destinations.mjs';
import {initialState,reduce,visibleBubbles,mergeRequest,manualMergeOptions,validInteraction,layoutPositions} from './state.mjs';
import {createClient} from './client.mjs';
const $=s=>document.querySelector(s),client=createClient(),canvasEl=$('#canvas'),bubbleLayer=$('#bubbles');
const toolWindows=new Map();
function reducedMotion(){return matchMedia('(prefers-reduced-motion: reduce)').matches||document.documentElement.classList.contains('reduced-motion')}
function setMotion(reduced){document.documentElement.classList.toggle('reduced-motion',reduced);$('#reduce-motion').setAttribute('aria-pressed',String(reduced));localStorage.setItem('wanjie-reduced-motion',String(reduced))}
setMotion(localStorage.getItem('wanjie-reduced-motion')==='true');$('#reduce-motion').onclick=()=>setMotion(!document.documentElement.classList.contains('reduced-motion'));
let state=initialState(),canvas=null,snapshot=null,intentId=null,enabled=false,composing=false,saveTimer,inputTimer,saveTail=Promise.resolve(),suggestBusy=false,suggestNext=null,detailsId=null,drag=null,trace=[],toastTimer;
const labels={source:'资料',action:'动作',link:'外部入口',flow:'执行组合',collection:'资料集合'},symbols={source:'⌑',action:'✧',link:'↗',flow:'⌘',collection:'◫'};
const anchors=intentMode?[[.18,.20],[.5,.20],[.82,.20],[.18,.80],[.5,.80],[.82,.80],[.08,.5],[.92,.5]]:[[.22,.31],[.5,.31],[.78,.31],[.22,.73],[.5,.80],[.78,.73],[.09,.46],[.91,.46],[.12,.82],[.88,.82],[.36,.86],[.65,.86]];
const terminal=t=>!['queued','running','submitting'].includes(t);
function element(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function button(text,fn,cls='secondary'){const b=element('button',text,cls);b.onclick=()=>Promise.resolve(fn()).catch(error);return b}
function append(parent,...children){parent.append(...children);return parent}
function toast(text){$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,4300)}
function error(e){toast(e.message||String(e));$('#status').textContent=e.message||String(e)}
function backup(){if(intentId)localStorage.setItem('wanjie-bubble-backup:'+intentId,JSON.stringify({version:canvas?.version,state}))}
function emit(event,persist=true){state=reduce(state,event);render();if(persist){backup();scheduleSave()}}
function content(){const {pending,undo,notice,...saved}=state;return structuredClone(saved)}
function scheduleSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>save().catch(error),300)}
function save(){clearTimeout(saveTimer);saveTail=saveTail.catch(()=>{}).then(async()=>{if(!canvas)return;const value=content();$('#save-status').textContent='保存中';try{const r=await client.command('artifact.update',{artifact:canvas.id,version:canvas.version,content:value});canvas=r.value;backup();$('#save-status').textContent='已保存'}catch(e){$('#save-status').textContent='保存失败 · 本机副本保留';throw e}});return saveTail}
function render(){
 updatePanelLayout();
 if(drag)return;
 const items=visibleBubbles(state),layout=layoutPositions(state,anchors);bubbleLayer.replaceChildren();$('#welcome').hidden=items.length>0;$('#undo').disabled=!state.undo;
 items.forEach((b,i)=>{const p=layout[b.id];if(intentMode&&!state.positions[b.id])state.positions[b.id]=p;const node=element(b.kind==='link'?'a':'button',undefined,'bubble '+b.kind+(b.selected?' selected':''));node.dataset.id=b.id;if(intentMode&&b.inputRevision!=null&&b.inputRevision!==state.inputRevision)node.classList.add('stale');if(b.kind==='link'){node.draggable=false;node.href=b.resource.url;node.target='_blank';node.rel='noopener noreferrer'};node.style.left=(p.x*100)+'%';node.style.top=(p.y*100)+'%';node.style.setProperty('--delay',(-i*1.23)+'s');node.style.setProperty('--float-time',(6.4+i*.73)+'s');node.append(element('span',undefined,'bubble-shell'));node.setAttribute('aria-label',`${labels[b.kind]}：${b.title}`);append(node,element('span',symbols[b.kind]||'◌','symbol'),element('strong',b.title),element('small',b.members?`${b.members.length} 个连接 · ${labels[b.kind]}`:labels[b.kind]));if(state.pending&&[state.pending.leftId,state.pending.rightId].includes(b.id))node.classList.add('matching');if(b.pinned)node.append(element('span','·','fixed'));node.addEventListener('pointerdown',startDrag);node.addEventListener('pointerenter',()=>showPreview(b.id,node));node.addEventListener('pointerleave',hidePreview);node.addEventListener('focus',()=>showPreview(b.id,node));node.addEventListener('blur',hidePreview);node.onclick=e=>{e.preventDefault();if(!node.wasDragged)showPreview(b.id,node)};node.ondblclick=e=>{e.preventDefault();if(!node.wasDragged)(intentMode?executeIntent(b.id):burstOpen(b.id,node))};node.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();(intentMode?executeIntent(b.id):burstOpen(b.id,node))}else if(e.key===' '){e.preventDefault();showDetails(b.id)}};bubbleLayer.append(node)});
 if(state.pending){const pair=[state.pending.leftId,state.pending.rightId].map(id=>[...bubbleLayer.children].find(n=>n.dataset.id===id));if(pair.every(Boolean))drawBridge(circle(pair[0]),circle(pair[1]),state.pending.status==='choice'?'选择组合方式':'正在匹配');}
 else drawBridge(null,null);
}
function requestSuggestions(mode='initial'){if(composing||!state.input.trim())return;if(!enabled){$('#status').textContent='先在连接设置中启用 Jev';return}suggestNext={mode,text:state.input,revision:state.inputRevision};pumpSuggestions()}
async function pumpSuggestions(){if(suggestBusy||!suggestNext)return;const req=suggestNext;suggestNext=null;suggestBusy=true;$('#status').textContent='Jev 正在寻找与你的想法相关的灵感…';$('#more').disabled=$('#refresh').disabled=true;try{const result=await client.capability('bubble.suggest',{text:req.text});record('候选判断',result.decision);emit({type:'suggestions',mode:req.mode,revision:req.revision,items:result.candidates.map(b=>({...b,inputRevision:req.revision}))});if(req.revision===state.inputRevision)$('#status').textContent=state.notice||(result.candidates.length?`找到 ${result.candidates.length} 个相关方向 · 双击执行，拖近组合`:'暂未找到合适的泡泡，试试补充应用名或具体动作')}
 catch(e){if(req.revision===state.inputRevision)error(e)}finally{suggestBusy=false;$('#more').disabled=$('#refresh').disabled=false;if(suggestNext)pumpSuggestions()}}
function record(type,decision){if(decision?.model)$('#connection').textContent='Jev 已连接';trace.unshift({type,...decision,time:new Date().toLocaleTimeString()});trace=trace.slice(0,12)}
function onInput(){suggestNext=null;if(intentMode){$('#drawer').hidden=true;detailsId=null}emit({type:'input',text:$('#intent').value});closeFusion();clearTimeout(inputTimer);if(!composing)inputTimer=setTimeout(()=>requestSuggestions(),intentMode?150:750)}
$('#intent').addEventListener('input',onInput);$('#intent').addEventListener('compositionstart',()=>{composing=true;clearTimeout(inputTimer);emit({type:'input',text:$('#intent').value});closeFusion()});$('#intent').addEventListener('compositionend',()=>{composing=false;onInput()});$('#intent').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!composing){e.preventDefault();clearTimeout(inputTimer);requestSuggestions()}});
$('#more').onclick=()=>requestSuggestions('more');$('#refresh').onclick=()=>requestSuggestions('refresh');$('#undo').onclick=()=>{emit({type:'undo'});closeDrawer()};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('#intent').value=b.dataset.prompt;onInput();$('#intent').focus()});
function startDrag(e){if(e.button!==0)return;hidePreview();const node=e.currentTarget,id=node.dataset.id;closeFusion();state=reduce(state,{type:'mergeCancel'});drawBridge(null,null);for(const n of bubbleLayer.children)n.classList.remove('matching');const box=node.getBoundingClientRect(),area=canvasEl.getBoundingClientRect();drag={id,node,startX:e.clientX,startY:e.clientY,x:box.left+box.width/2-area.left,y:box.top+box.height/2-area.top,area,old:state.positions[id],moved:false,target:null,request:null,result:null};node.setPointerCapture(e.pointerId);node.addEventListener('pointermove',moveDrag);node.addEventListener('pointerup',endDrag,{once:true});node.addEventListener('pointercancel',cancelDrag,{once:true});document.body.classList.add('drag-active')}
function circle(node){const r=node.getBoundingClientRect(),area=canvasEl.getBoundingClientRect();return {id:node.dataset.id,x:r.left+r.width/2-area.left,y:r.top+r.height/2-area.top,r:r.width/2};}
let connectionEpoch=0;
function drawBridge(a,b,label='松开组合'){connectionEpoch++;for(const n of bubbleLayer.children)n.classList.remove('connected');$('#bridge').style.removeProperty('opacity');const path=$('#bridge-path'),hint=$('#merge-hint');if(!b){$('#bridge').classList.remove('visible');hint.hidden=true;return}path.setAttribute('d',outline(a,b));for(const n of bubbleLayer.children)if([a.id,b.id].includes(n.dataset.id))n.classList.add('connected');$('#bridge').classList.add('visible');$('#bridge').style.setProperty('--from',getComputedStyle([...bubbleLayer.children].find(n=>n.dataset.id===a.id)).getPropertyValue('--tint'));const target=[...bubbleLayer.children].find(n=>n.dataset.id===b.id);$('#bridge').style.setProperty('--to',getComputedStyle(target).getPropertyValue('--tint'));const gradient=$('#bridge-color');gradient.setAttribute('gradientUnits','userSpaceOnUse');for(const [key,value]of Object.entries({x1:a.x,y1:a.y,x2:b.x,y2:b.y}))gradient.setAttribute(key,value);hint.textContent=label;hint.hidden=false;hint.style.left=((a.x+b.x)/2)+'px';hint.style.top=(Math.min(a.y,b.y)-Math.max(a.r,b.r)-32)+'px';}
function moveDrag(e){if(!drag)return;const d=drag,dx=e.clientX-d.startX,dy=e.clientY-d.startY;if(Math.hypot(dx,dy)<5&&!d.moved)return;d.moved=true;d.node.wasDragged=true;d.node.classList.add('dragging');const x=Math.max(48,Math.min(d.area.width-48,d.x+dx)),y=Math.max(150,Math.min(d.area.height-70,d.y+dy));d.pos={x:x/d.area.width,y:y/d.area.height};d.node.style.left=x+'px';d.node.style.top=y+'px';d.node.style.translate='0 0';const now=performance.now(),dt=Math.max(8,now-(d.lastTime||now-16));d.shape=deformation((e.clientX-(d.lastX??d.startX))/dt,(e.clientY-(d.lastY??d.startY))/dt);d.lastX=e.clientX;d.lastY=e.clientY;d.lastTime=now;if(!reducedMotion()){d.node.style.setProperty('--drag-angle',d.shape.angle+'deg');d.node.style.setProperty('--drag-stretch',d.shape.stretch);d.node.style.setProperty('--drag-squash',1/d.shape.stretch)}const a=circle(d.node),items=[...bubbleLayer.children].filter(n=>n!==d.node&&manualMergeOptions(state,d.id,n.dataset.id).length).map(circle),target=pickTarget(a,items,d.target);d.target=target?.id||null;for(const n of bubbleLayer.children)n.classList.toggle('target',n.dataset.id===d.target);drawBridge(a,target);}
function cleanupDrag(d){d.node.removeEventListener('pointermove',moveDrag);d.node.removeEventListener('pointerup',endDrag);d.node.removeEventListener('pointercancel',cancelDrag);document.body.classList.remove('drag-active');bubbleLayer.querySelectorAll('.target').forEach(n=>n.classList.remove('target'));drawBridge(null,null);setTimeout(()=>d.node.wasDragged=false,50)}
function endDrag(){if(!drag)return;const d=drag;drag=null;cleanupDrag(d);if(!d.moved)return;d.released=true;if(d.target){const target=[...bubbleLayer.children].find(n=>n.dataset.id===d.target);if(target){const c=circle(target);state=reduce(state,{type:'pin',id:d.target,position:{x:c.x/d.area.width,y:c.y/d.area.height}})}}if(!d.target){emit({type:'pin',id:d.id,position:d.pos});recoil(d);return}emit({type:'pin',id:d.id,position:d.pos});beginMerge(d.id,d.target,d);}
function recoil(d){const node=[...bubbleLayer.children].find(n=>n.dataset.id===d.id);if(!node||reducedMotion())return;const angle=d.shape?.angle||0,stretch=d.shape?.stretch||1;node.querySelector('.bubble-shell').animate([stretch,.95,1.025,.99,1].map(v=>({transform:`rotate(${angle}deg) scale(${v},${1/v}) rotate(${-angle}deg)`})),{duration:520,easing:'ease-out'});}
function cancelDrag(){if(!drag)return;const d=drag;drag=null;cleanupDrag(d);emit({type:'mergeCancel'},false)}
function groupObject(id){return visibleBubbles(state).find(b=>b.id===id)}
async function beginMerge(leftId,rightId,session={released:true}) {
 if(!enabled){toast('请先在连接设置中启用 Jev');render();return}
 const left=groupObject(leftId),right=groupObject(rightId);if(!left||!right)return;
 const req=mergeRequest(state,leftId,rightId);const positions=layoutPositions(state,anchors);req.center={userPlaced:true,x:(positions[leftId].x+positions[rightId].x)/2,y:(positions[leftId].y+positions[rightId].y)/2};session.request=req;
 emit({type:'mergeStart',request:req},false);if(session.released)showPending();
 try {
  const result=await Promise.race([
   client.capability('bubble.merge',{text:state.input||'组织这些灵感',left,right}),
   new Promise((_,reject)=>setTimeout(()=>reject(new Error('判断超时')),14000))
  ]);
  record('融合判断',result.decision);session.result=result.merge;
  if(session.released)applyMerge(session);
 } catch(e) {
  if(state.pending?.interactionId!==req.interactionId||!validInteraction(state,req))return;
  session.result={status:'choice',manual:true,error:e.message,options:manualMergeOptions(state,leftId,rightId)};
  if(session.released)applyMerge(session);
 }
}
let fusionGhosts=[],fusionPair=null;
function captureFusion(req){fusionGhosts.forEach(n=>n.remove());fusionGhosts=[];fusionPair=[];if(reducedMotion())return;for(const id of [req.leftId,req.rightId]){const node=[...bubbleLayer.children].find(n=>n.dataset.id===id);if(!node)continue;const c=circle(node),ghost=node.cloneNode(true);ghost.classList.add('connected');fusionPair.push(c);ghost.removeAttribute('data-id');ghost.setAttribute('aria-hidden','true');ghost.tabIndex=-1;ghost.style.cssText+=`;left:${c.x}px;top:${c.y}px;animation:none;translate:0 0;pointer-events:none;z-index:6`;canvasEl.append(ghost);fusionGhosts.push(ghost)}}
function animateFusion(before,req){if(state.pending||!req){fusionGhosts.forEach(n=>n.remove());fusionGhosts=[];return;}const group=state.groups.find(g=>!before.includes(g.id));if(!group)return;const node=[...bubbleLayer.children].find(n=>n.dataset.id===group.id);if(!node||reducedMotion())return;const area=canvasEl.getBoundingClientRect();for(const ghost of fusionGhosts){const anim=ghost.animate([{opacity:1},{left:(req.center.x*area.width)+'px',top:(req.center.y*area.height)+'px',opacity:0}],{duration:motion.duration,easing:'ease-in-out',fill:'forwards'});anim.onfinish=()=>ghost.remove()}fusionGhosts=[];animateConnection(fusionPair,node,req.center);node.querySelector('.bubble-shell').animate([{scale:'.65',opacity:0,borderRadius:'42% 58% 48% 52%'},{scale:String(motion.elasticity),opacity:1,offset:.7},{scale:'1',opacity:1}],{duration:motion.duration,easing:'ease-out'});}
function animateConnection(pair,node,center){
 if(!pair||pair.length!==2||reducedMotion())return;
 node.classList.add('connected');const finalRadius=circle(node).r;const epoch=++connectionEpoch;const area=canvasEl.getBoundingClientRect(),cx=center.x*area.width,cy=center.y*area.height,started=performance.now();
 $('#merge-hint').hidden=true;
 function frame(now){
  if(epoch!==connectionEpoch){node.classList.remove('connected');return;}
  const t=Math.min(1,(now-started)/motion.duration),ease=t*t*(3-2*t);
  if(t>=1||!node.isConnected||reducedMotion()){node.classList.remove('connected');$('#bridge').classList.remove('visible');$('#bridge').style.removeProperty('opacity');return}
  const moved=pair.map(p=>({...p,x:p.x+(cx-p.x)*ease,y:p.y+(cy-p.y)*ease,r:(p.r+(finalRadius-p.r)*ease)*(1+(t>.65?(motion.elasticity-1)*Math.sin(Math.PI*(t-.65)/.35):0))}));
  $('#bridge-path').setAttribute('d',outline(...moved));$('#bridge').classList.add('visible');$('#bridge').style.opacity='1';
  window.requestAnimationFrame(frame);
 }
 window.requestAnimationFrame(frame);
}
function applyMerge(session){if(!state.pending||state.pending.interactionId!==session.request.interactionId||!validInteraction(state,session.request)){render();return;}const supported=manualMergeOptions(state,session.request.leftId,session.request.rightId);if(session.result.status==='clear'&&!supported.some(o=>o.id===session.result.operation))session.result={status:'choice',manual:true,error:'组合不满足当前约束或步骤上限',options:supported};const before=state.groups.map(g=>g.id);captureFusion(session.request);emit({type:'mergeResult',request:session.request,result:session.result});animateFusion(before,session.request);if(state.pending?.status==='choice'){const box=$('#fusion-content');box.replaceChildren(element('p',session.result.manual?`${session.result.error}。泡泡已保留，你可以手动选择受支持的组合；这不是 Jev 的判断。`:'Jev 认为有几种可能，请选择你想要的连接方式。','muted'));if(session.result.manual)box.append(button('重试匹配',()=>beginMerge(session.request.leftId,session.request.rightId)));for(const o of state.pending.options)box.append(button(o.label+(o.probability==null?' · 用户选择':` · ${Math.round(o.probability*100)}%`),()=>{const before=state.groups.map(g=>g.id),req=state.pending;captureFusion(req);emit({type:'mergeChoice',operation:o.id});animateFusion(before,req);closeFusion();toast('已按你的选择建立组合') }));if(!state.pending.options.length)box.append(element('p','这些泡泡暂时没有可执行的组合，可以补充资料或换一个动作。','muted'));if(!$('#fusion').open)$('#fusion').show()}else{closeFusion();toast('灵感已连接，打开组合可查看和运行')}}
function showPending(){const box=$('#fusion-content');box.replaceChildren(element('p','正在匹配 · 两个原泡泡仍然保留…','muted'),element('p','连接只整理泡泡，点击运行后才执行。','muted'));if(!$('#fusion').open)$('#fusion').show()}
function closeFusion(){if($('#fusion').open)$('#fusion').close()}
$('#cancel-fusion').onclick=()=>{emit({type:'mergeCancel'},false);closeFusion()};$('#fusion').addEventListener('cancel',()=>emit({type:'mergeCancel'},false));$('#fusion .dialog-close').onclick=e=>{e.preventDefault();emit({type:'mergeCancel'},false);closeFusion()};
function openDrawer(kicker='IDEA DETAILS'){const box=$('#drawer-content');box.replaceChildren();$('#drawer-kicker').textContent=kicker;$('#drawer').hidden=false;updatePanelLayout();return box}
function closeDrawer(){$('#drawer').hidden=true;updatePanelLayout();const n=[...bubbleLayer.children].find(n=>n.dataset.id===detailsId);n?.focus();detailsId=null}
$('#close').onclick=closeDrawer;document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#bubble-preview').hidden=true;closeDrawer();if(drag)cancelDrag();if(state.pending){emit({type:'mergeCancel'},false);closeFusion()}}});
function leaves(id){const b=[...state.bubbles,...state.groups].find(b=>b.id===id);return b?.members?b.members.flatMap(leaves):b?[b]:[]}
let hoverTimer;const launches=new Map();
function handoffSettings(){try{return JSON.parse(localStorage.getItem('wanjie-handoff-targets')||'{}')}catch{return {}}}
function hidePreview(){clearTimeout(hoverTimer);hoverTimer=setTimeout(()=>{$('#bubble-preview').hidden=true},180)}
function showPreview(id,node){if(drag?.moved)return;clearTimeout(hoverTimer);const b=groupObject(id);if(!b)return;const panel=$('#bubble-preview');panel.replaceChildren(element('strong',b.title),element('p',previewContent(b,leaves(id),snapshot),'preview-text'));const destination=destinationFor(leaves(id),handoffSettings());panel.append(element('small',intentMode?'双击执行 · 拖拽连接 · 空格查看详情':destination?'双击击破 · 打开 '+(destination.kind==='obsidian'?'Obsidian':new URL(destination.url).hostname):'双击设置目标工具 · 空格查看与组合'));panel.append(button('详情与组合',()=>{panel.hidden=true;showDetails(id)}));panel.hidden=false;const r=node.getBoundingClientRect();panel.style.left=Math.max(12,Math.min(innerWidth-324,r.left+r.width/2-150))+'px';const height=panel.getBoundingClientRect().height||280;panel.style.top=(r.bottom+12+height<=innerHeight?r.bottom+12:Math.max(12,r.top-height-12))+'px';}
$('#bubble-preview').onpointerenter=()=>clearTimeout(hoverTimer);$('#bubble-preview').onpointerleave=hidePreview;
function configureHandoff(id){const box=openDrawer('TOOL DESTINATION'),settings=handoffSettings();box.append(element('h2','选择执行工具'),element('p','优先使用你保存的工具选择。可读取本机已安装工具与仓库名称，不读取笔记或浏览器历史；也可填写网页地址。','muted'));for(const [key,label]of [['writing','写作工具网址'],['market','行情工具网址']]){const field=element('input',undefined,'field');field.type='url';field.value=settings[key]||'';field.setAttribute('aria-label',label);box.append(element('label',label),field);field.oninput=()=>settings[key]=field.value.trim()}box.append(button('读取本机工具建议',()=>discoverTools(box,settings).catch(error)));box.append(button('保存工具入口',()=>{if(['writing','market'].some(k=>settings[k]&&!(k==='writing'&&settings[k]==='obsidian'&&settings.vault)&&!safeDestination(settings[k])))return toast('请选择 Obsidian 仓库，或输入完整的 http/https 网页地址');localStorage.setItem('wanjie-handoff-targets',JSON.stringify(settings));toast('工具入口已保存');if(id)showDetails(id);else closeDrawer()},'primary'));}
async function discoverTools(box,settings){const response=await fetch('/api/device-tools');if(!response.ok)throw new Error('本机工具检测不可用');const profile=await response.json();if(!profile.obsidian.installed){box.append(element('p','未检测到 Obsidian；可以填写你常用的网页。','muted'));return}const panel=element('section',undefined,'member');panel.append(element('strong','已安装 Obsidian · 可在应用内新建笔记'));const select=element('select',undefined,'field');select.setAttribute('aria-label','Obsidian 仓库');for(const vault of profile.obsidian.vaults){const option=element('option',vault.name);option.value=vault.id;select.append(option)}panel.append(select,button('写作使用 Obsidian',()=>{if(!select.value)return toast('请先在 Obsidian 建立仓库');settings.writing='obsidian';settings.vault=select.value;localStorage.setItem('wanjie-handoff-targets',JSON.stringify(settings));box.querySelector('[aria-label="写作工具网址"]').value='obsidian';toast('已记住：写作使用 Obsidian')}));box.append(panel)}
async function dispatchObsidian(id,b,destination,content,box,link){try{const response=await fetch('/api/device-tools/obsidian',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:intentId+':'+id,vault:destination.vault,title:b.title,content})});const result=await response.json();if(!response.ok)throw new Error(result.error||'交接失败');link.href='obsidian://open?'+new URLSearchParams({vault:destination.vault,file:result.file,paneType:'tab'}).toString().replaceAll('+','%20');box.querySelector('.run-status').textContent=result.status==='handed_off'?(result.reused?'本次内容已交接过；点击打开原笔记，不重复新建。':'已交给 Obsidian 新建笔记，请在应用中继续写作。'):'无法确认应用是否接收。请先检查 Obsidian，本站不会自动重试新建。';}catch(e){box.querySelector('.run-status').textContent=e.message+'；可复制内容后在 Obsidian 中粘贴。'}}
function burstOpen(id,node){const b=groupObject(id);if(!b)return;clearTimeout(hoverTimer);$('#bubble-preview').hidden=true;const destination=destinationFor(leaves(id),handoffSettings());if(!destination)return configureHandoff(id);const previous=launches.get(id);if(previous&&Date.now()-previous.at<900)return;const native=destination.kind==='obsidian',win=native?null:window.open(destination.url,'wanjie-handoff-'+id);launches.set(id,{at:Date.now()});if(win){try{win.opener=null;win.focus()}catch{}}if(node&&!reducedMotion()){node.classList.add('bursting');const shell=node.querySelector('.bubble-shell');const animation=shell.animate([{transform:'scale(1)',opacity:1},{transform:'scale(1.15)',opacity:.8,offset:.25},{transform:'scale(1.5)',opacity:0,offset:.65},{transform:'scale(.92)',opacity:0,offset:.85},{transform:'scale(1)',opacity:1}],{duration:560,easing:'ease-out'});animation.onfinish=()=>node.classList.remove('bursting')}const box=openDrawer('TOOL HANDOFF');box.append(element('h2',b.title),element('p',native?'正在交给 Obsidian…':win?'已打开目标工具，请在目标中继续操作。':'窗口被拦截，请点击下面的入口打开。','run-status'));const link=element('a','打开目标工具','primary');link.href=native?'obsidian://open?'+new URLSearchParams({vault:destination.vault}).toString().replaceAll('+','%20'):destination.url;link.target='_blank';link.rel='noopener noreferrer';box.append(link,element('p','万界门不会在后台执行本次任务，也无法判断目标工具内的执行结果。','muted'));const context=element('textarea',undefined,'field');context.readOnly=true;context.value=[b.members?'':state.input,previewContent(b,leaves(id),snapshot)].filter(Boolean).join('\n\n');context.setAttribute('aria-label','带到工具的内容');if(native)dispatchObsidian(id,b,destination,context.value,box,link);box.append(context,button('复制内容',()=>navigator.clipboard.writeText(context.value).then(()=>toast('内容已复制')).catch(()=>toast('请选中文本手动复制'))),button('修改目标工具',()=>configureHandoff(id)));}
function showDetails(id){const b=groupObject(id);if(!b)return;detailsId=id;const box=openDrawer();append(box,element('span',labels[b.kind],'tag'),element('h2',b.title),element('p',b.description||'组合保留每个成员，执行时会冻结本次输入和所选资料。','muted'));
 if(b.members){box.append(element('h3','连接成员'));for(const child of leaves(id)){const row=element('div',child.title,'member');row.append(element('small',labels[child.kind]));if(child.resource?.artifact)row.append(button('使用资料最新版本',()=>refreshSource(child.resource.artifact,id)));box.append(row)}box.append(button('拆开组合',()=>{emit({type:'split',id});closeDrawer()}))}
 else if(b.kind==='source'){const a=snapshot?.artifacts.find(a=>a.id===b.resource.artifact);if(a){box.append(button('使用资料最新版本',()=>refreshSource(a.id,id)));box.append(element('p',typeof a.content.text==='string'?a.content.text:JSON.stringify(a.content,null,2),'source-text'))}else box.append(element('p',b.resource.url||b.resource.market||'尚未读取','source-text'));box.append(element('label','运行时读取范围'));const select=element('select',undefined,'field');[['full','完整内容'],['excerpt','原文片段（最多 1200 字符）'],['metadata','仅目录信息（不能用于写作）']].forEach(([v,t])=>{const o=element('option',t);o.value=v;select.append(o)});select.value=b.resource.detail||'full';select.onchange=()=>{state.bubbles=state.bubbles.map(x=>x.id===id?{...x,resource:{...x.resource,detail:select.value},version:(x.version||0)+1}:x);backup();scheduleSave();toast('读取范围已更新')};box.append(select);box.append(button(b.selected?'取消保留这个泡泡':'保留这个泡泡',()=>{emit({type:'select',id});showDetails(id)}))}
 if(b.kind==='link'){const a=element('a','打开对应网站 / 工具','secondary');a.href=b.resource.url;a.target='_blank';a.rel='noopener noreferrer';box.append(a)}else{const select=element('select',undefined,'field');select.setAttribute('aria-label','选择另一个泡泡');for(const other of visibleBubbles(state).filter(x=>x.id!==id&&manualMergeOptions(state,id,x.id).length)){const o=element('option',other.title);o.value=other.id;select.append(o)}append(box,element('h3','与另一个泡泡连接'),select,button('让 Jev 判断组合',()=>{if(select.value){closeDrawer();beginMerge(id,select.value)} }));}
 box.append(button(intentMode?'执行这个泡泡':'打开目标工具',()=>intentMode?executeIntent(id):burstOpen(id,[...bubbleLayer.children].find(n=>n.dataset.id===id)),'primary'));if(state.runs[id])box.append(button('查看历史运行',()=>openTool(id),'secondary'));

}
function openTool(id){const run=state.runs[id];if(!run)return;const url=toolURL(intentId,id,run);const win=window.open(url,'wanjie-'+run.runId);if(win){toolWindows.set(run.runId,win);win.focus()}else{toast('浏览器拦截了工具窗口，请点击下方入口');const a=element('a','打开本次工具（新窗口）','secondary');a.href=url;a.target='_blank';a.rel='noopener';$('#drawer-content').append(a)}}
const watching=new Set();async function watchRun(id,taskId){if(watching.has(taskId))return;watching.add(taskId);try{const {task,snapshot:s}=await client.watch(taskId,{onUpdate:t=>{const run=state.runs[id];if(!run||run.taskId!==taskId)return;if(run.status!==t.status){emit({type:'runUpdate',groupId:id,value:{status:t.status}});if(detailsId===id)showDetails(id)}}});snapshot=s;emit({type:'runUpdate',groupId:id,value:{status:task.status,message:task.error?.message,artifacts:task.artifacts}});updateCounts();if(detailsId===id)showDetails(id);if(task.status==='success'){toast('执行完成，已保存到本次工具');if(!toolWindows.get(state.runs[id].runId)||toolWindows.get(state.runs[id].runId).closed)openTool(id)}else toast(task.error?.message||'执行已停止，阶段资料已保留')}catch(e){error(e)}finally{watching.delete(taskId)}}
async function reconcileRun(id,resubmit=false) {
 const run=state.runs[id];if(!run)return;
 if(run.taskId)return watchRun(id,run.taskId);
 try {
  const found=await client.recover(run,{resubmit});
  if(found.found){emit({type:'runUpdate',groupId:id,value:{taskId:found.response.task.id,status:found.response.task.status,missing:false}});showDetails(id);watchRun(id,found.response.task.id)}
  else {emit({type:'runUpdate',groupId:id,value:{missing:true}});showDetails(id);toast('尚未查到历史受理记录。已保留原运行编号，本页面不会重新提交执行。')}
 }catch(e){error(e)}
}
async function refreshSource(artifactId,detailId) {
 snapshot=await client.snapshot();const artifact=snapshot.artifacts.find(a=>a.id===artifactId);
 if(!artifact)throw new Error('资料已不可访问，请重新添加');
 emit({type:'refreshSource',artifact});closeFusion();await save();showDetails(detailId);
 toast(`已使用资料最新版本 v${artifact.version}；历史产物保持原有来源`);
}
function updateCounts(){$('#result-count').textContent=snapshot?.artifacts.filter(a=>a.kind==='document').length||0}
async function showHistory(){snapshot=await client.snapshot();updateCounts();detailsId=null;const box=openDrawer('YOUR CREATIONS');append(box,element('h2','从灵感到作品'),element('p','每一次执行的资料与结果，都会留在这个空间。','muted'));const arts=snapshot.artifacts.filter(a=>a.kind!=='bubble-canvas').reverse();for(const a of arts){const b=button(a.title,()=>showArtifact(a),'result-row');b.append(element('small',`${a.kind==='document'?'文稿':'资料'} · ${a.source}`));box.append(b)}if(!arts.length)box.append(element('p','还没有产物。添加资料，连接一个动作，然后运行。','muted'))}
function sourceLink(s,i){const row=element('div',`[${i+1}] ${s.title}`,'member');row.append(element('small',`${s.source} · ${s.detail} · v${s.version}`));try{const url=new URL(s.source);if(url.protocol==='https:'){const a=element('a','查看原始来源');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';row.append(a)}}catch{}return row}
function showArtifact(a){detailsId=null;const box=openDrawer('SAVED RESULT');append(box,element('span',a.kind==='document'?'可编辑文稿':'已保存资料','tag'),element('h2',a.title));const editor=element('textarea',undefined,'field editor');editor.setAttribute('aria-label','编辑产物正文');editor.value=typeof a.content?.text==='string'?a.content.text:JSON.stringify(a.content,null,2);box.append(editor);const row=element('div',undefined,'actions-row');append(row,button('保存修改',async()=>{const r=await client.command('artifact.update',{artifact:a.id,version:a.version,content:{...a.content,text:editor.value}});a=r.value;toast('修改已保存')}),button('复制',async()=>{await navigator.clipboard.writeText(editor.value);toast('已复制')}),button('导出 .md',()=>{const url=URL.createObjectURL(new Blob([editor.value+'\n\n'+(a.content.sources||[]).map((s,i)=>`[${i+1}] ${s.title} — ${s.source}`).join('\n')],{type:'text/markdown;charset=utf-8'}));const link=element('a');link.href=url;link.download=a.title+'.md';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}));box.append(row);if(a.content.sources?.length){box.append(element('h3','本次使用的真实来源'));a.content.sources.forEach((s,i)=>{box.append(sourceLink(s,i));const d=element('details');append(d,element('summary','查看冻结的资料内容'),element('div',s.text,'source-text'));box.append(d)})}box.append(element('p',`来源 / 模型：${a.content.model||a.source}`,'muted'))}
function showAddSource(){const box=openDrawer('BRING YOUR OWN CONTEXT');append(box,element('h2','把资料带进来'),element('p','粘贴一段笔记，或加入 HTTPS 链接。网页会在运行时读取。','muted'));const title=element('input',undefined,'field');title.placeholder='给这份资料一个名字';title.maxLength=100;title.setAttribute('aria-label','资料名称');const text=element('textarea',undefined,'field');text.placeholder='笔记正文，或 https:// 开头的网页地址';text.setAttribute('aria-label','资料内容');append(box,title,text,button('添加到画布',async()=>{const value=text.value.trim();if(!value)throw new Error('请先填写资料内容');if(visibleBubbles(state).filter(x=>!x.members).length>=12)throw new Error('画布已有 12 个泡泡，请先合并一些');let bubble;if(/^https:\/\/\S+$/.test(value)){const u=new URL(value);bubble={id:crypto.randomUUID(),kind:'source',title:title.value.trim()||u.hostname,resource:{url:u.href,detail:'excerpt'},description:'用户提供的网页 · 尚未读取',pinned:true}}else{const r=await client.command('artifact.create',{kind:'note',title:title.value.trim()||'我的资料',content:{text:value},source:'用户粘贴'});const a=r.value;bubble={id:'artifact:'+a.id,kind:'source',title:a.title,resource:{artifact:a.id,version:a.version,detail:'full'},description:'用户提供的正文',pinned:true};snapshot=await client.snapshot()}emit({type:'add',bubble});await save();closeDrawer();toast('资料已放入画布，可与动作泡泡连接')} ,'primary'))}
function showSettings(){const box=openDrawer('CONNECTION SETTINGS');append(box,element('h2','让灵感连接真实能力'),element('p','启用后，当前想法与所选资料会交给相应服务处理。密钥仅由本机服务端读取。','muted'),element('div','Jev · 灵感与融合判断\nOpenRouter · 文稿生成\n网页读取 · 指定的 HTTPS 来源\n公开行情 · 以报价时间为准','source-text'),element('p','授权有效 1 小时，最多 100 次能力调用。Jev 与生成可能产生 API 费用；不会自动续期。','muted'),button(enabled?'重新授权 1 小时':'启用 Jev 与执行能力',async()=>{await client.authorize();enabled=true;$('#connection').textContent='Jev 已启用';closeDrawer();toast('当前空间已授权');if(state.input.trim())requestSuggestions()},'primary'));if(!snapshot?.capabilities.some(c=>c.id==='bubble.suggest'))box.append(element('p','当前服务未开启 Demo 提供者，请按 README 设置 WANJIE_DEMO=1 后重启。','error'))}
function showTrace(){const box=openDrawer('JEV DECISION TRACE');append(box,element('h2','判断有迹可循'),element('p','这里展示实际接口响应。融合概率只是本次判断，不代表统计准确率。','muted'));if(!trace.length)box.append(element('p','尚无本页判断记录，输入一个想法后会出现。','muted'));for(const item of trace){const d=element('details');d.open=trace[0]===item;append(d,element('summary',`${item.type} · ${item.elapsed_ms} ms · ${item.time}`),element('pre',JSON.stringify(item,null,2),'trace'));box.append(d)}}
$('#tool-settings').onclick=()=>configureHandoff();$('#settings').onclick=showSettings;$('#history').onclick=()=>showHistory().catch(error);$('#add-source').onclick=showAddSource;$('#inspect').onclick=showTrace;
async function init(){try{intentId=localStorage.getItem('wanjie-bubble-intent');if(intentId){client.setIntent(intentId);try{snapshot=await client.snapshot()}catch{intentId=null}}
 if(!intentId){const r=await client.command('intent.create',{title:'万界门 · 灵感画布'});intentId=r.value.id;client.setIntent(intentId);localStorage.setItem('wanjie-bubble-intent',intentId);snapshot=await client.snapshot()}
 canvas=snapshot.artifacts.find(a=>a.kind==='bubble-canvas');if(!canvas){canvas=(await client.command('artifact.create',{kind:'bubble-canvas',title:'灵感画布',content:content(),source:'用户组织'})).value}
 state=initialState(canvas.content);const local=JSON.parse(localStorage.getItem('wanjie-bubble-backup:'+intentId)||'null');if(local&&local.version===canvas.version)state=initialState(local.state);else if(local&&local.version>canvas.version)toast('检测到本机副本，服务端画布版本不同；请先核对保存状态');$('#intent').value=state.input;enabled=snapshot.grants.some(g=>!g.revoked&&g.expiresAt>Date.now()&&g.remaining>0&&g.capabilities.includes('bubble.suggest'));$('#connection').textContent=enabled?'Jev 已启用':'尚未启用 Jev';render();updateCounts();$('#save-status').textContent='已恢复画布';if(state.input)$('#status').textContent='画布已恢复 · 所有组合与产物均保留';for(const [id,r]of Object.entries(state.runs)){if(r.taskId&&!terminal(r.status))watchRun(id,r.taskId);else if(r.status==='submitting'||r.status==='outcome_unknown')reconcileRun(id).catch(error)}}catch(e){error(e);$('#connection').textContent='连接未完成'}}
if(intentMode)configureIntentSurface();
init().then(()=>{if(intentMode){const q=new URLSearchParams(window.location.search).get('q');if(q&&q!==state.input){$('#intent').value=q;onInput()}else if(state.input.trim()&&enabled)requestSuggestions()}});

installGlass(canvasEl,bubbleLayer);


function configureIntentSurface(){
 document.body.classList.add('intent-mode');
 if(new URLSearchParams(window.location.search).get('native')==='1'){document.body.classList.add('native-panel');document.documentElement.classList.add('native-root')}
 document.title='万界门 × Vicinae · 意图入口';
 if(document.body.classList.contains('native-panel')){
  $('.tools').append($('#settings'),$('#history'));
  const settings=button('⚙',()=>{showSettings();const box=$('#drawer-content');box.append(button('我的产物',()=>showHistory().catch(error),'secondary'),button('添加资料',showAddSource,'secondary'),button('普通命令搜索',()=>$('#tool-settings').onclick(),'secondary'),element('p','⌃⌥ Space 唤起或收起 · Esc 收起 · 双击执行 · 拖近组合','muted'))},'search-settings');settings.setAttribute('aria-label','连接设置');$('.capsule-actions').append(settings);
  const hint=element('span','⌃⌥ Space 唤起 · Esc 收起','shortcut-hint');$('.capsule-caption').append(hint);
  $('#intent').placeholder='搜索命令，或说说你想做什么…';
 }
 const style=document.createElement('link');style.rel='stylesheet';style.href='/launcher.css';document.head.append(style);
 $('.brand small').textContent='WANJIE × VICINAE';
 $('.canvas-heading .eyebrow').textContent='THOUGHTS INTO ACTIONS';
 $('.canvas-heading h1').textContent='想到什么，就从这里开始。';
 $('.canvas-heading p').textContent='一个想法，几种可能。让资料和行动轻轻相连。';
 $('.canvas-bottom > div').textContent='单击预览 · 双击执行 · 拖近组合';
 const social=button('↗ 社交灵感',()=>{$('#intent').value='把这个想法写成一条社交媒体帖子：用自然语言连接桌面工具';onInput();$('#intent').focus()},'');$('.starters').append(social);
 const mark=element('span','Vicinae · 连接中','pill desktop-status');$('nav').prepend(mark);
 fetch('/api/vicinae/status').then(r=>r.json()).then(s=>{mark.textContent=s.available?`Vicinae · ${s.supported} 个入口`:'Vicinae · 未连接';mark.title=s.available?`从 ${s.loaded} 个真实命令中接入已验证用途的入口`:s.message}).catch(()=>mark.textContent='Vicinae · 未连接');
 $('#tool-settings').textContent='普通命令搜索';$('#tool-settings').onclick=()=>{const q=$('#intent').value;window.location.href='vicinae://open?fallbackText='+encodeURIComponent(q)};
}
const intentInFlight=new Set();
async function executeIntent(id){
 if(intentInFlight.has(id))return;
 const b=groupObject(id);if(!b)return;
 clearTimeout(hoverTimer);$('#bubble-preview').hidden=true;
 if(b.inputRevision!=null&&b.inputRevision!==state.inputRevision)return toast('想法已变化，请等待新泡泡；组合请按新想法重新连接。');
 const route=executionFor(b,leaves(id),state.input);
 if(route.error)return toast(route.error);
 if(route.url){window.open(route.url,'_blank','noopener');return}
 if(route.details)return showDetails(id);
 const runKey=id+'@'+state.inputRevision;
 const existing=state.runs[runKey];
 if(existing){if(existing.status==='failure'&&!existing.taskId){delete state.runs[runKey];return executeIntent(id)}if(existing.taskId){await showIntentResult(id,existing.taskId,runKey);return}return toast('正在核对上次运行，请在我的产物中检查，避免重复执行。')}
 if(!enabled)return showSettings();
 intentInFlight.add(id);const runId=crypto.randomUUID();
 const ownerRevision=state.inputRevision,requestText=state.input;
 emit({type:'runStart',groupId:runKey,runId});
 const box=openDrawer('ACTION IN PROGRESS');box.append(element('h2',b.title),element('p','正在执行，当前输入与资料已冻结…','run-status'));
 let payload,type,submitted=false;
 try{
  await save();
  // Saving may await a previous request. Never run a newer input with an older bubble.
  if(ownerRevision!==state.inputRevision)throw new Error('保存期间想法已变化，请重新选择泡泡');
  if(route.workflow){type='bubble.run';payload={runId,canvas:canvas.id,version:canvas.version,groupId:id,text:requestText}}
  else {type='capability.run';payload={capability:route.capability,input:route.input}}
  // Keep the recoverable request locally without changing the canvas revision again.
  state.runs[runKey]={...state.runs[runKey],payload,commandType:type};backup();submitted=true;
  const response=await client.command(type,payload,{id:runId});
  emit({type:'runUpdate',groupId:runKey,value:{taskId:response.task.id,status:response.task.status}});
  await showIntentResult(id,response.task.id,runKey);
 }catch(e){emit({type:'runUpdate',groupId:runKey,value:{status:!submitted||e.confirmedFailure?'failure':'outcome_unknown',message:e.message}});box.append(element('p',e.message,'error'));error(e)}
 finally{intentInFlight.delete(id)}
}
async function showIntentResult(id,taskId,runKey=id){
 const box=openDrawer('ACTION RESULT');const b=groupObject(id);box.append(element('h2',b?.title||'执行结果'));
 const status=element('p','正在取得执行结果…','run-status');box.append(status);
 try{
  const {task,snapshot:s}=await client.watch(taskId,{onUpdate:t=>status.textContent=['queued','running'].includes(t.status)?'正在执行…':t.status});snapshot=s;
  emit({type:'runUpdate',groupId:runKey,value:{status:task.status,artifacts:task.artifacts,message:task.error?.message}});updateCounts();
  const result=task.result||{};
  status.textContent=task.status==='success'?(result.message||'已完成，结果保留在我的产物中。'):(task.error?.message||'任务未完成');
  const all=task.artifacts.map(a=>s.artifacts.find(x=>x.id===a)).filter(Boolean);
  for(const a of all){
   box.append(element('h3',a.title));
   const text=typeof a.content.text==='string'?a.content.text:JSON.stringify(a.content,null,2);
   const field=element('textarea',undefined,'field');field.value=text;field.readOnly=true;field.setAttribute('aria-label','结果内容');
   const quotes=a.content.blocks?.filter(b=>b.type==='quotes').flatMap(b=>b.items)||[];
   if(quotes.length){for(const q of quotes){const card=element('section',undefined,'quote-card');card.append(element('span',q.name+' · '+q.symbol,'eyebrow'),element('strong',String(q.price),'quote-price'),element('span',`${q.change>0?'+':''}${q.change} · ${q.percent}%`,'quote-change'),element('small',`来源报价时间：${q.asof}`),element('small',q.source+' · 可能延迟，以来源时间为准'));box.append(card)}}else box.append(field);
   box.append(button('复制结果',()=>navigator.clipboard.writeText(field.value).then(()=>toast('已复制'))));
   if(a.kind==='document'&&a.title==='起草社交帖子'){
    field.readOnly=false;field.setAttribute('aria-label','编辑发布草稿');
    const link=element('a','带到 X 发布编辑器 ↗','secondary');link.href='https://twitter.com/intent/tweet?text='+encodeURIComponent(text);link.target='_blank';link.rel='noopener noreferrer';field.oninput=()=>link.href='https://twitter.com/intent/tweet?text='+encodeURIComponent(field.value);box.append(link,element('p','可先编辑草稿，再打开发布页继续；这里不会自动发帖。','muted'));
   }
   if(a.kind!=='bubble-canvas')box.append(button('作为资料泡泡继续连接',()=>{emit({type:'add',bubble:{id:'artifact:'+a.id,kind:'source',title:a.title,description:'执行所得的真实资料',resource:{artifact:a.id,version:a.version,detail:'full'},pinned:true}});closeDrawer()}));
  }
  if(['queued','running'].includes(task.status))return;
  if(task.status==='success'&&result.status!=='outcome_unknown'||['failure','cancelled'].includes(task.status))box.append(button('明确再运行一次',()=>{delete state.runs[runKey];backup();return executeIntent(id)}));
 }catch(e){status.textContent=e.message;throw e}
}

function updatePanelLayout(){
 if(!intentMode)return;
 const expanded=!!state.input.trim()||!$('#drawer').hidden;
 document.body.classList.toggle('has-input',expanded);
 if(!state.input.trim())$('#status').textContent='输入一个想法，Jev 会帮你找到可执行的方向';
 window.webkit?.messageHandlers?.layout?.postMessage({expanded});
}
