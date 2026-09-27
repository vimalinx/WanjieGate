import {AdaptiveSpace} from './adaptive-space.js';
import {installEdgeHistory} from './edge-history.js';
import {returnToOrigin,installNextGesture} from './workspace-transition.js';
import {prose,expandedProse,reference,market,illustration} from '../demo/fixtures.js';

// No API client is imported. Demo commands mutate these objects only.
const $=selector=>document.querySelector(selector);
const id=()=>crypto.randomUUID().replaceAll('-','');
const session='demo-'+id();
const spaces=new Map();
let current=null,growth,clock=0,last=performance.now(),playing=true,busy=false,next=0,epoch=0,inputRevision=0;
const makeSpace=(name)=>{
 const key=session+'-'+id();
 const value={intent:{id:key,title:name},surface:{mode:'general',manual:false,blocks:{}},artifacts:[],tasks:[],relations:[],draft:''};
 spaces.set(key,value);return key;
};
const writing=makeSpace('风经过的下午');
const stocks=makeSpace('两条走势 · 模拟行情');
function snapshot(){return spaces.get(current)||{artifacts:[],tasks:[],surface:{}};}
function label(text){$('#demo-stage').textContent=text;}
function pause(){playing=false;$('#demo-play').textContent='继续';}
function fail(error){pause();label('演示已暂停');console.error('Demo:',error);}
function layout(){
 if(!growth)return;
 const entered=growth.mode==='writing'||[...growth.blocks.values()].some(block=>!block.el.hidden);
 document.body.classList.toggle('entered',entered);
 $('#capsule-context').hidden=true;$('#workspace').hidden=true;
 for(const lane of ['left','right','bottom'])document.body.dataset['lane'+lane[0].toUpperCase()+lane.slice(1)]=String(!!document.querySelector(`[data-lane="${lane}"] .growth-block:not([hidden])`));
 if(growth.mode==='writing')growth.resize();else{$('#request').style.height='auto';$('#request').style.height=Math.min(240,Math.max(28,$('#request').scrollHeight))+'px';}
}
function history(){
 const list=$('#intent-list');list.replaceChildren();
 for(const [key,value] of spaces){
  if(!value.draft&&!value.artifacts.length)continue;
  const button=document.createElement('button');button.className='demo-history-entry';button.textContent=value.intent.title;button.setAttribute('aria-current',String(key===current));
  const small=document.createElement('small');small.textContent='演示会话 · 仅存在此标签页';button.append(small);
  button.onclick=async()=>{pause();$('#history-dialog').close();await activate(key);label('可编辑、拖入材料或恢复演示');};list.append(button);
 }
 $('#empty').hidden=!!list.children.length;
}
function render(){growth.update(snapshot(),current);if(snapshot().demoReference)materialReference();layout();history();}
async function command(type,payload={},owner=current){
 const state=spaces.get(owner);if(!state)throw new Error('请选择一个演示会话');
 let value={};
 if(type==='artifact.create'){
  value={...structuredClone(payload),id:id(),intent:owner,version:1,updated:Date.now()};state.artifacts.push(value);
 }else if(type==='artifact.update'){
  value=state.artifacts.find(a=>a.id===payload.artifact);if(!value)throw new Error('演示材料不存在');Object.assign(value,structuredClone(payload),{version:value.version+1,updated:Date.now()});
 }else if(type==='surface.update')state.surface={...state.surface,...structuredClone(payload)};
 else if(type==='relation.add')state.relations.push(structuredClone(payload));
 else throw new Error('这项操作不在演示范围内');
 history();return {value};
}
async function run(capability,payload){
 const owner=current,state=snapshot(),task={id:id(),status:'success',artifacts:[]};
 let artifact;
 if(capability==='reference.search')artifact=await command('artifact.create',{kind:'references',title:'写作材料 · 演示',content:reference,source:'演示数据'},owner);
 else if(capability==='market.query')artifact=await command('artifact.create',{kind:'scene',title:'模拟行情',content:market,source:'演示数据'},owner);
 else throw new Error('演示不会调用外部能力');
 task.artifacts.push(artifact.value.id);state.tasks.push(task);
 setTimeout(()=>{if(current===owner)render();},50);return task;
}
async function activate(key){
 if(current&&growth.mode==='writing')await growth.save();
 if(current)snapshot().draft=$('#request').value;
 current=key;$('#request').value=snapshot().draft||'';render();
}
async function origin(slide=true){
 const owner=current,revision=inputRevision;
 clearTimeout(growth.saveTimer);
 if(owner&&growth.mode==='writing'&&(growth.note||$('#request').value.trim()))await growth.save();
 // A keystroke made while saving must not be discarded by the return animation.
 if(owner!==current||revision!==inputRevision)return false;
 if(owner){
  snapshot().draft=$('#request').value;
  if(!slide){
   await command('surface.update',{mode:'general',document:'',manual:false,blocks:{}},owner);
   delete snapshot().presentation;delete snapshot().demoReference;
  }
 }
 if(owner!==current||revision!==inputRevision)return false;
 await returnToOrigin({slide,reset:()=>{current=null;inputRevision++;$('#request').value='';render();}});
 return true;
}
function write(text){inputRevision++;$('#request').value=text;snapshot().draft=text;growth.changed();layout();}
function signal(values){snapshot().presentation={task:id(),text:$('#request').value.trim(),editor:0,market:0,supports:{},...values};render();}
function materialReference(){
 const key='demo-reference';
 growth.payloads.set(key,{text:'\n> '+reference.entries[0].text+'\n> — 演示示例（人工编写）\n'});
 growth.block('demo-example','从一个场景开始',`<article class="reference-material" draggable="true" data-material="${key}"><span class="demo-reference-label">演示示例 · 人工编写</span><p class="demo-reference-text">${reference.entries[0].text}</p><footer><button data-insert="${key}">插入引用</button></footer></article>`,'right');layout();
}
async function materialImage(){
 await command('artifact.create',{kind:'image',title:'午后窗边 · 演示插图',content:{data:illustration(),description:'本地绘制的演示插图'},source:'演示数据'});render();
}
const steps=[
 {at:1200,label:'从一句话开始',act:async()=>{await activate(writing);write('今天的风很热烈，我喜欢。');}},
 {at:2800,label:'输入连续展开为正文',act:async()=>{signal({editor:.96});}},
 {at:5200,label:'继续记录，正文始终可编辑',act:async()=>{write(prose);}},
 {at:7600,label:'材料从侧边靠近',act:async()=>{snapshot().demoReference=true;materialReference();}},
 {at:10400,label:'拖入引用或插图试试',act:async()=>{write(expandedProse);await materialImage();}},
 {at:15500,label:'分块退场，回到新的起点',act:async()=>{await origin(true);}},
 {at:18400,label:'同一个入口，另一件事',act:async()=>{await activate(stocks);write('看看这两只股票的走势');}},
 {at:20200,label:'行情组件 · 全部为模拟数据',act:async()=>{signal({market:.98});}},
 {at:26000,label:'左侧边缘可展开演示历史',act:async()=>{pause();$('#demo-play').textContent='重播';}}
];

const style=document.createElement('link');style.rel='stylesheet';style.href='/demo/demo.css';document.head.append(style);
const controls=document.createElement('nav');controls.className='demo-controls';controls.setAttribute('aria-label','演示控制');controls.innerHTML='<strong>演示 · 模拟数据</strong><span id="demo-stage" class="demo-stage" role="status">空白，从一个念头开始</span><button id="demo-play">暂停</button><button id="demo-replay">重播</button><a href="/">退出</a>';document.body.append(controls);
for(let i=0;i<12;i++){const shutter=document.createElement('div');shutter.className='shutter';shutter.style.setProperty('--i',i);shutter.style.setProperty('--direction',i%2?1:-1);const word=document.createElement('span');word.textContent='WANJIE';shutter.append(word);$('#shutters').append(shutter);}
$('#connection').textContent='仅演示 · 不调用模型';
$('.drawer-assistance').hidden=true;$('.drawer-controls').hidden=true;$('#modules-button').hidden=true;$('#generate').hidden=true;
const edge=installEdgeHistory($('#history-dialog'),$('#history-edge'));
$('#history-open').onclick=()=>{pause();edge.open();};$('#history-close').onclick=()=>$('#history-dialog').close();
$('#new-intent').onclick=$('#start-intent').onclick=async()=>{pause();$('#history-dialog').close();if(await origin(true)){next=steps.length;$('#demo-play').textContent='重播';label('新的演示输入 · 重播可看完整流程');}};
growth=new AdaptiveSpace({state:snapshot,command,run,ensure:async()=>{if(!current)await activate(makeSpace('新的演示记录'));return current;},refresh:async()=>render(),layoutChanged:layout,contextChanged:()=>{},fail});
// Installed extensions are outside the mock sandbox; use only built-in blocks here.
growth.extensions.update=()=>{};
$('#request').addEventListener('input',async event=>{
 inputRevision++;if(event.isTrusted)pause();
 if(!current){const text=$('#request').value,key=makeSpace('新的演示记录');spaces.get(key).draft=text;await activate(key);}
 snapshot().draft=$('#request').value;growth.changed();layout();
 if(!event.isComposing&&!$('#request').value.trim()&&growth.mode==='writing'&&!growth.manual){
  try{if(await origin(false)){next=steps.length;$('#demo-play').textContent='重播';label('已回到起点 · 演示不推断新输入');}}catch(error){fail(error);}return;
 }
 label(growth.mode==='writing'?'已暂停 · 编辑只保留在演示中':'演示不推断新输入 · 重播可看完整流程');
});
for(const event of ['pointerdown','dragstart'])document.addEventListener(event,e=>{
 if(e.isTrusted&&!controls.contains(e.target))pause();
},{capture:true});
$('#history-edge').addEventListener('pointerenter',event=>{if(event.isTrusted)pause();});
async function replay(){
 pause();epoch++;while(busy)await new Promise(resolve=>setTimeout(resolve,30));await origin(true);
 for(const value of spaces.values()){value.artifacts=[];value.tasks=[];value.draft='';value.surface={mode:'general',manual:false,blocks:{}};delete value.presentation;delete value.demoReference;}
 // These storage keys belong exclusively to this randomized demo instance.
 for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(key?.includes(session))sessionStorage.removeItem(key);}
 clock=0;next=0;last=performance.now();playing=true;$('#demo-play').textContent='暂停';label('空白，从一个念头开始');history();
}
$('#demo-play').onclick=()=>{if(next>=steps.length){replay().catch(fail);return;}playing=!playing;last=performance.now();$('#demo-play').textContent=playing?'暂停':'继续';};
$('#demo-replay').onclick=()=>replay().catch(fail);
installNextGesture(async()=>{pause();if(await origin(true)){next=steps.length;$('#demo-play').textContent='重播';label('新的演示输入 · 重播可看完整流程');}});
render();
setInterval(async()=>{
 const now=performance.now(),delta=now-last;last=now;if(!playing||busy||document.hidden)return;
 clock+=Math.min(delta,200);const step=steps[next];if(!step||clock<step.at)return;
 busy=true;next++;const token=epoch;label(step.label);
 try{await step.act();if(token===epoch)layout();}catch(error){fail(error);}finally{busy=false;}
},100);
window.addEventListener('pagehide',()=>{
 playing=false;clearTimeout(growth.saveTimer);
 for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(key?.includes(session))sessionStorage.removeItem(key);}
});
