import {initialState,reduce,visibleBubbles,mergeRequest,releaseDisposition,manualMergeOptions,validInteraction,layoutPositions} from './state.mjs';
import {createClient} from './client.mjs';
const $=s=>document.querySelector(s),client=createClient(),canvasEl=$('#canvas'),bubbleLayer=$('#bubbles');
let state=initialState(),canvas=null,snapshot=null,intentId=null,enabled=false,composing=false,saveTimer,inputTimer,saveTail=Promise.resolve(),suggestBusy=false,suggestNext=null,detailsId=null,drag=null,trace=[],toastTimer;
const labels={source:'资料',action:'动作',link:'外部入口',flow:'执行组合',collection:'资料集合'},symbols={source:'⌑',action:'✧',link:'↗',flow:'⌘',collection:'◫'};
const anchors=[[.22,.31],[.5,.31],[.78,.31],[.22,.73],[.5,.80],[.78,.73],[.09,.46],[.91,.46],[.12,.82],[.88,.82],[.36,.86],[.65,.86]];
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
 if(drag)return;
 const items=visibleBubbles(state),layout=layoutPositions(state,anchors);bubbleLayer.replaceChildren();$('#welcome').hidden=items.length>0;$('#undo').disabled=!state.undo;
 items.forEach((b,i)=>{const p=layout[b.id];const node=element('button',undefined,'bubble '+b.kind+(b.selected?' selected':''));node.dataset.id=b.id;node.style.left=(p.x*100)+'%';node.style.top=(p.y*100)+'%';node.style.setProperty('--delay',(-i*1.23)+'s');node.setAttribute('aria-label',`${labels[b.kind]}：${b.title}`);append(node,element('span',symbols[b.kind]||'◌','symbol'),element('strong',b.title),element('small',b.members?`${b.members.length} 个连接 · ${labels[b.kind]}`:labels[b.kind]));if(b.pinned)node.append(element('span','·','fixed'));node.addEventListener('pointerdown',startDrag);node.onclick=()=>{if(!node.wasDragged)showDetails(b.id)};bubbleLayer.append(node)});
}
function requestSuggestions(mode='initial'){if(composing||!state.input.trim())return;if(!enabled){$('#status').textContent='先在连接设置中启用 Jev';return}suggestNext={mode,text:state.input,revision:state.inputRevision};pumpSuggestions()}
async function pumpSuggestions(){if(suggestBusy||!suggestNext)return;const req=suggestNext;suggestNext=null;suggestBusy=true;$('#status').textContent='Jev 正在寻找与你的想法相关的灵感…';$('#more').disabled=$('#refresh').disabled=true;try{const result=await client.capability('bubble.suggest',{text:req.text});record('候选判断',result.decision);emit({type:'suggestions',mode:req.mode,revision:req.revision,items:result.candidates});if(req.revision===state.inputRevision)$('#status').textContent=state.notice||`找到 ${result.candidates.length} 个相关方向 · 拖动泡泡试试`}
 catch(e){if(req.revision===state.inputRevision)error(e)}finally{suggestBusy=false;$('#more').disabled=$('#refresh').disabled=false;if(suggestNext)pumpSuggestions()}}
function record(type,decision){trace.unshift({type,...decision,time:new Date().toLocaleTimeString()});trace=trace.slice(0,12)}
function onInput(){emit({type:'input',text:$('#intent').value});closeFusion();clearTimeout(inputTimer);if(!composing)inputTimer=setTimeout(()=>requestSuggestions(),750)}
$('#intent').addEventListener('input',onInput);$('#intent').addEventListener('compositionstart',()=>{composing=true;clearTimeout(inputTimer);emit({type:'input',text:$('#intent').value});closeFusion()});$('#intent').addEventListener('compositionend',()=>{composing=false;onInput()});$('#intent').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!composing){e.preventDefault();clearTimeout(inputTimer);requestSuggestions()}});
$('#more').onclick=()=>requestSuggestions('more');$('#refresh').onclick=()=>requestSuggestions('refresh');$('#undo').onclick=()=>{emit({type:'undo'});closeDrawer()};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('#intent').value=b.dataset.prompt;onInput();$('#intent').focus()});
function startDrag(e){if(e.button!==0)return;const node=e.currentTarget,id=node.dataset.id;closeFusion();state=reduce(state,{type:'mergeCancel'});const box=node.getBoundingClientRect(),area=canvasEl.getBoundingClientRect();drag={id,node,startX:e.clientX,startY:e.clientY,x:box.left+box.width/2-area.left,y:box.top+box.height/2-area.top,area,old:state.positions[id],moved:false,target:null,request:null,result:null};node.setPointerCapture(e.pointerId);node.addEventListener('pointermove',moveDrag);node.addEventListener('pointerup',endDrag,{once:true});node.addEventListener('pointercancel',cancelDrag,{once:true});document.body.classList.add('drag-active')}
function moveDrag(e){if(!drag)return;const d=drag,dx=e.clientX-d.startX,dy=e.clientY-d.startY;if(Math.hypot(dx,dy)<5&&!d.moved)return;d.moved=true;d.node.wasDragged=true;d.node.classList.add('dragging');const x=Math.max(48,Math.min(d.area.width-48,d.x+dx)),y=Math.max(160,Math.min(d.area.height-90,d.y+dy));d.pos={x:x/d.area.width,y:y/d.area.height};d.node.style.left=x+'px';d.node.style.top=y+'px';let closest=null,distance=90;for(const n of bubbleLayer.children){if(n===d.node)continue;const r=n.getBoundingClientRect();const v=Math.hypot(e.clientX-r.left-r.width/2,e.clientY-r.top-r.height/2);if(v<distance){distance=v;closest=n}}const id=closest?.dataset.id;if(id!==d.target){clearTimeout(d.timer);bubbleLayer.querySelectorAll('.target').forEach(n=>n.classList.remove('target'));state=reduce(state,{type:'mergeCancel'});d.target=id;d.request=null;d.result=null;if(closest){closest.classList.add('target');d.timer=setTimeout(()=>beginMerge(d.id,id,d),250)}}}
function cleanupDrag(d){clearTimeout(d.timer);d.node.removeEventListener('pointermove',moveDrag);document.body.classList.remove('drag-active');bubbleLayer.querySelectorAll('.target').forEach(n=>n.classList.remove('target'));setTimeout(()=>d.node.wasDragged=false,50)}
function endDrag() {
 if(!drag)return;
 const d=drag;drag=null;cleanupDrag(d);
 if(!d.moved)return;
 d.released=true;
 switch(releaseDisposition(state,d)) {
  case 'pin': emit({type:'pin',id:d.id,position:d.pos});break;
  case 'start': beginMerge(d.id,d.target,d);break;
  case 'apply': applyMerge(d);break;
  case 'wait': render();showPending();break;
  default: emit({type:'mergeCancel'},false);closeFusion();render();
 }
}
function cancelDrag(){if(!drag)return;const d=drag;drag=null;cleanupDrag(d);emit({type:'mergeCancel'},false)}
function groupObject(id){return visibleBubbles(state).find(b=>b.id===id)}
async function beginMerge(leftId,rightId,session={released:true}) {
 if(!enabled){toast('请先在连接设置中启用 Jev');render();return}
 const left=groupObject(leftId),right=groupObject(rightId);if(!left||!right)return;
 const req=mergeRequest(state,leftId,rightId);session.request=req;
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
function applyMerge(session){if(!state.pending||state.pending.interactionId!==session.request.interactionId||!validInteraction(state,session.request)){render();return;}const supported=manualMergeOptions(state,session.request.leftId,session.request.rightId);if(session.result.status==='clear'&&!supported.some(o=>o.id===session.result.operation))session.result={status:'choice',manual:true,error:'组合不满足当前约束或步骤上限',options:supported};emit({type:'mergeResult',request:session.request,result:session.result});if(state.pending?.status==='choice'){const box=$('#fusion-content');box.replaceChildren(element('p',session.result.manual?`${session.result.error}。泡泡已保留，你可以手动选择受支持的组合；这不是 Jev 的判断。`:'Jev 认为有几种可能，请选择你想要的连接方式。','muted'));for(const o of state.pending.options)box.append(button(o.label+(o.probability==null?' · 用户选择':` · ${Math.round(o.probability*100)}%`),()=>{emit({type:'mergeChoice',operation:o.id});closeFusion();toast('已按你的选择建立组合') }));if(!state.pending.options.length)box.append(element('p','这些泡泡暂时没有可执行的组合，可以补充资料或换一个动作。','muted'));if(!$('#fusion').open)$('#fusion').showModal()}else{closeFusion();toast('灵感已连接，打开组合可查看和运行')}}
function showPending(){const box=$('#fusion-content');box.replaceChildren(element('p','Jev 正在判断两者的关系…','muted'),element('p','连接只整理泡泡，点击运行后才执行。','muted'));if(!$('#fusion').open)$('#fusion').showModal()}
function closeFusion(){if($('#fusion').open)$('#fusion').close()}
$('#cancel-fusion').onclick=()=>{emit({type:'mergeCancel'},false);closeFusion()};$('#fusion').addEventListener('cancel',()=>emit({type:'mergeCancel'},false));$('#fusion').addEventListener('close',()=>{if(state.pending)emit({type:'mergeCancel'},false)});
function openDrawer(kicker='IDEA DETAILS'){const box=$('#drawer-content');box.replaceChildren();$('#drawer-kicker').textContent=kicker;$('#drawer').hidden=false;return box}
function closeDrawer(){$('#drawer').hidden=true;const n=[...bubbleLayer.children].find(n=>n.dataset.id===detailsId);n?.focus();detailsId=null}
$('#close').onclick=closeDrawer;document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeDrawer();if(drag)cancelDrag()}});
function leaves(id){const b=[...state.bubbles,...state.groups].find(b=>b.id===id);return b?.members?b.members.flatMap(leaves):b?[b]:[]}
function showDetails(id){const b=groupObject(id);if(!b)return;detailsId=id;const box=openDrawer();append(box,element('span',labels[b.kind],'tag'),element('h2',b.title),element('p',b.description||'组合保留每个成员，执行时会冻结本次输入和所选资料。','muted'));
 if(b.members){box.append(element('h3','连接成员'));for(const child of leaves(id)){const row=element('div',child.title,'member');row.append(element('small',labels[child.kind]));if(child.resource?.artifact)row.append(button('使用资料最新版本',()=>refreshSource(child.resource.artifact,id)));box.append(row)}box.append(button('拆开组合',()=>{emit({type:'split',id});closeDrawer()}))}
 else if(b.kind==='source'){const a=snapshot?.artifacts.find(a=>a.id===b.resource.artifact);if(a){box.append(button('使用资料最新版本',()=>refreshSource(a.id,id)));box.append(element('p',typeof a.content.text==='string'?a.content.text:JSON.stringify(a.content,null,2),'source-text'))}else box.append(element('p',b.resource.url||b.resource.market||'尚未读取','source-text'));box.append(element('label','运行时读取范围'));const select=element('select',undefined,'field');[['full','完整内容'],['excerpt','原文片段（最多 1200 字符）'],['metadata','仅目录信息（不能用于写作）']].forEach(([v,t])=>{const o=element('option',t);o.value=v;select.append(o)});select.value=b.resource.detail||'full';select.onchange=()=>{state.bubbles=state.bubbles.map(x=>x.id===id?{...x,resource:{...x.resource,detail:select.value},version:(x.version||0)+1}:x);backup();scheduleSave();toast('读取范围已更新')};box.append(select);box.append(button(b.selected?'取消保留这个泡泡':'保留这个泡泡',()=>{emit({type:'select',id});showDetails(id)}))}
 if(b.kind==='link'){const a=element('a','在新标签中打开搜索','secondary');a.href=b.resource.url;a.target='_blank';a.rel='noopener noreferrer';box.append(a)}else{const select=element('select',undefined,'field');select.setAttribute('aria-label','选择另一个泡泡');for(const other of visibleBubbles(state).filter(x=>x.id!==id)){const o=element('option',other.title);o.value=other.id;select.append(o)}append(box,element('h3','与另一个泡泡连接'),select,button('让 Jev 判断组合',()=>{if(select.value){closeDrawer();beginMerge(id,select.value)} }));}
 if(b.members||b.kind==='action'){
 box.append(element('h3','执行前预览'));const sources=leaves(id).filter(x=>x.kind==='source');append(box,element('p',sources.length?sources.map((x,i)=>`[${i+1}] ${x.title} · ${x.resource.artifact?'已读取':x.resource.url?'执行时读取网页':'执行时查询行情'} · ${x.resource.detail||'full'}`).join('\n'):'尚未添加来源。空白文稿和行动清单可单独运行，写作请先连接资料。','source-text'),element('p','执行会使用当前输入与所选资料，可能产生 API 费用。最多 4 个步骤。','muted'));
 const run=state.runs[id];if(run){append(box,element('p',`任务：${run.status}${run.message?'\n'+run.message:''}`,'run-status'),button('核对这次运行',()=>reconcileRun(id)));if(run.missing&&run.payload)box.append(button('重发本次运行（同一编号）',()=>reconcileRun(id,true)));if(run.taskId&&!terminal(run.status))box.append(button('停止执行',async()=>{await client.command('task.cancel',{task:run.taskId});toast('已请求停止；当前上游调用结束后不再执行后续步骤')}));if(['success','failure','cancelled','partial','interrupted'].includes(run.status))box.append(button('再次运行（创建新任务）',()=>runGroup(id,true),'primary'));if(run.artifacts?.length)box.append(button('查看产物',showHistory));}else box.append(button('运行这个组合',()=>runGroup(id),'primary'));
 }
}
async function runGroup(id,again=false){
 if(!enabled)return showSettings();if(state.runs[id]&&(!again||!['success','failure','cancelled','partial','interrupted'].includes(state.runs[id].status)))return reconcileRun(id);
 const runId=crypto.randomUUID();emit({type:again?'runAgain':'runStart',groupId:id,runId});let submitted=false;
 try{await save();const payload={runId,canvas:canvas.id,version:canvas.version,groupId:id,text:state.input||'按这个组合整理资料'};state.runs[id].payload=payload;backup();submitted=true;
 const r=await client.run(payload);emit({type:'runUpdate',groupId:id,value:{taskId:r.task.id,status:r.task.status}});showDetails(id);watchRun(id,r.task.id);
 }catch(e){emit({type:'runUpdate',groupId:id,value:{status:!submitted||e.confirmedFailure?'failure':'outcome_unknown',message:e.message}});showDetails(id);error(e)}
}
const watching=new Set();async function watchRun(id,taskId){if(watching.has(taskId))return;watching.add(taskId);try{const {task,snapshot:s}=await client.watch(taskId,{onUpdate:t=>{const run=state.runs[id];if(!run||run.taskId!==taskId)return;if(run.status!==t.status){emit({type:'runUpdate',groupId:id,value:{status:t.status}});if(detailsId===id)showDetails(id)}}});snapshot=s;emit({type:'runUpdate',groupId:id,value:{status:task.status,message:task.error?.message,artifacts:task.artifacts}});updateCounts();if(detailsId===id)showDetails(id);if(task.status==='success'){toast('执行完成，产物已经保存');showHistory()}else toast(task.error?.message||'执行已停止，阶段资料已保留')}catch(e){error(e)}finally{watching.delete(taskId)}}
async function reconcileRun(id,resubmit=false) {
 const run=state.runs[id];if(!run)return;
 if(run.taskId)return watchRun(id,run.taskId);
 try {
  const found=await client.recover(run,{resubmit});
  if(found.found){emit({type:'runUpdate',groupId:id,value:{taskId:found.response.task.id,status:found.response.task.status,missing:false}});showDetails(id);watchRun(id,found.response.task.id)}
  else {emit({type:'runUpdate',groupId:id,value:{missing:true}});showDetails(id);toast('尚未查到受理记录。可以手动重发，继续使用同一个运行编号。')}
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
function showSettings(){const box=openDrawer('CONNECTION SETTINGS');append(box,element('h2','让灵感连接真实能力'),element('p','启用后，当前想法与所选资料会交给相应服务处理。密钥仅由本机服务端读取。','muted'),element('div','Jev · 灵感与融合判断\nOpenRouter · 文稿生成\n网页读取 · 指定的 HTTPS 来源\n公开行情 · 以报价时间为准','source-text'),element('p','授权有效 1 小时，最多 100 次能力调用。Jev 与生成可能产生 API 费用；不会自动续期。','muted'),button(enabled?'重新授权 1 小时':'启用 Jev 与执行能力',async()=>{await client.authorize();enabled=true;$('#connection').textContent='Jev 已连接';closeDrawer();toast('当前空间已授权');if(state.input.trim())requestSuggestions()},'primary'));if(!snapshot?.capabilities.some(c=>c.id==='bubble.suggest'))box.append(element('p','当前服务未开启 Demo 提供者，请按 README 设置 WANJIE_DEMO=1 后重启。','error'))}
function showTrace(){const box=openDrawer('JEV DECISION TRACE');append(box,element('h2','判断有迹可循'),element('p','这里展示实际接口响应。融合概率只是本次判断，不代表统计准确率。','muted'));if(!trace.length)box.append(element('p','尚无本页判断记录，输入一个想法后会出现。','muted'));for(const item of trace){const d=element('details');d.open=trace[0]===item;append(d,element('summary',`${item.type} · ${item.elapsed_ms} ms · ${item.time}`),element('pre',JSON.stringify(item,null,2),'trace'));box.append(d)}}
$('#settings').onclick=showSettings;$('#history').onclick=()=>showHistory().catch(error);$('#add-source').onclick=showAddSource;$('#inspect').onclick=showTrace;
async function init(){try{intentId=localStorage.getItem('wanjie-bubble-intent');if(intentId){client.setIntent(intentId);try{snapshot=await client.snapshot()}catch{intentId=null}}
 if(!intentId){const r=await client.command('intent.create',{title:'万界门 · 灵感画布'});intentId=r.value.id;client.setIntent(intentId);localStorage.setItem('wanjie-bubble-intent',intentId);snapshot=await client.snapshot()}
 canvas=snapshot.artifacts.find(a=>a.kind==='bubble-canvas');if(!canvas){canvas=(await client.command('artifact.create',{kind:'bubble-canvas',title:'灵感画布',content:content(),source:'用户组织'})).value}
 state=initialState(canvas.content);const local=JSON.parse(localStorage.getItem('wanjie-bubble-backup:'+intentId)||'null');if(local&&local.version===canvas.version)state=initialState(local.state);else if(local&&local.version>canvas.version)toast('检测到本机副本，服务端画布版本不同；请先核对保存状态');$('#intent').value=state.input;enabled=snapshot.grants.some(g=>!g.revoked&&g.expiresAt>Date.now()&&g.remaining>0&&g.capabilities.includes('bubble.suggest'));$('#connection').textContent=enabled?'Jev 已连接':'尚未启用 Jev';render();updateCounts();$('#save-status').textContent='已恢复画布';if(state.input)$('#status').textContent='画布已恢复 · 所有组合与产物均保留';for(const [id,r]of Object.entries(state.runs)){if(r.taskId&&!terminal(r.status))watchRun(id,r.taskId);else if(r.status==='submitting'||r.status==='outcome_unknown')reconcileRun(id).catch(error)}}catch(e){error(e);$('#connection').textContent='连接未完成'}}
init();
