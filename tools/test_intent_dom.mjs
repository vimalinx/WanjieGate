import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const {Window}=await import(process.env.HAPPY_DOM_MODULE);
const win=new Window({url:'http://127.0.0.1:5175/launcher'});
win.document.write(await fs.readFile(new URL('../static/demo.html',import.meta.url),'utf8'));
for(const key of ['window','document','localStorage','navigator','getComputedStyle'])Object.defineProperty(globalThis,key,{value:key==='window'?win:typeof win[key]==='function'?win[key].bind(win):win[key],configurable:true});
globalThis.innerWidth=1000;globalThis.innerHeight=800;globalThis.matchMedia=()=>({matches:false});
win.HTMLElement.prototype.setPointerCapture=function(){};
win.HTMLElement.prototype.animate=function(){return {onfinish:null}};
win.HTMLDialogElement.prototype.show=function(){this.open=true};win.HTMLDialogElement.prototype.close=function(){this.open=false};
let canvas={id:'canvas',kind:'bubble-canvas',version:1,content:{input:'写草稿',inputRevision:1,bubbles:[{id:'s',kind:'source',title:'资料',resource:{artifact:'note',version:1}},{id:'a',kind:'action',title:'文稿',resource:{action:'blank'}}],groups:[{id:'g',version:0,inputRevision:1,members:['s','a'],operation:'combine',title:'资料 → 文稿'}]}};
let commands=[],tasks=[],runCount=0;
const snapshot=()=>({artifacts:[canvas],tasks,grants:[{expiresAt:Date.now()+1e6,remaining:100,capabilities:['bubble.suggest']}],capabilities:[]});
localStorage.setItem('wanjie-bubble-intent','intent');
globalThis.fetch=async(url,options={})=>{
 if(url==='/api/vicinae/status')return {ok:true,json:async()=>({available:true,supported:6,loaded:226})};
 if(!options.body)return {ok:true,json:async()=>snapshot()};
 const body=JSON.parse(options.body);commands.push(body);let value={};
 if(body.type==='artifact.update'){canvas={...canvas,version:canvas.version+1,content:body.payload.content};value={value:canvas}}
 if(body.type==='capability.run'){const task={id:'suggest',status:'success',artifacts:[],result:{decision:{},candidates:[{id:'a',kind:'action',title:'空白文稿',resource:{action:'blank'}}]}};tasks.push(task);value={task}}
 if(body.type==='bubble.run'){
  if(body.payload.version!==canvas.version)return {ok:false,status:409,json:async()=>({error:'画布版本不匹配',code:'revision_conflict'})};
  runCount++;const task={id:'run',status:'success',artifacts:[],result:{}};tasks.push(task);value={task};
 }
 return {ok:true,json:async()=>value};
};
const tick=ms=>new Promise(r=>setTimeout(r,ms));
await import('../static/js/bubbles/app.mjs?intent-dom');await tick(80);
let node=document.querySelector('[data-id="g"]');assert.ok(node);
node.click();await tick(10);assert.equal(runCount,0,'single click must not execute');
node.dispatchEvent(new win.MouseEvent('dblclick',{bubbles:true}));node.dispatchEvent(new win.MouseEvent('dblclick',{bubbles:true}));await tick(150);
assert.equal(runCount,1,'double-click must execute one workflow using the final saved canvas version');
assert.match(document.querySelector('#drawer-content').textContent,/已完成/);
const input=document.querySelector('#intent');
input.value='';input.dispatchEvent(new win.Event('input',{bubbles:true}));await tick(350);
input.value='第二份空白草稿';input.dispatchEvent(new win.Event('input',{bubbles:true}));await tick(500);
node=document.querySelector('[data-id="a"]');node.dispatchEvent(new win.MouseEvent('dblclick',{bubbles:true}));await tick(120);assert.equal(runCount,2);
input.value='第三份空白草稿';input.dispatchEvent(new win.Event('input',{bubbles:true}));await tick(500);
node=document.querySelector('[data-id="a"]');node.dispatchEvent(new win.MouseEvent('dblclick',{bubbles:true}));await tick(120);assert.equal(runCount,3,'new input must not reuse the previous action result');
console.log('PASS intent DOM: single-click preview, double-click execution, versioned save, duplicate suppression');
await win.happyDOM.abort();process.exit(0);
