import {validateComponent} from './component-schema.js';
// Installed modules are trusted application code, not sandboxed third-party scripts.
let catalog=[];const styles=new Set();
export const catalogReady=fetch('/extensions/catalog.json').then(r=>{if(!r.ok)throw new Error('Component catalog unavailable');return r.json();}).then(v=>{catalog=v.modules;return catalog;});
export const components=()=>catalog;
export const descriptor=key=>catalog.find(m=>m.slotKey===key||m.id===key);
export const MATERIAL='application/vnd.wanjie.material+json';
export function encodeMaterial(id,intent,payload){return JSON.stringify({version:'0.1',id,intent,kind:id.startsWith('ref:')?'citation':id.startsWith('image:')?'image':'text',text:payload.text.slice(0,12000),...(payload.artifact?{artifact:payload.artifact}:{})});}
export function decodeMaterial(raw,intent){try{const p=JSON.parse(raw);if(p.version==='0.1'&&p.intent===intent&&['text','citation','image','artifact'].includes(p.kind)&&typeof p.text==='string'&&p.text.length<=12000)return p;}catch{}return null;}
export class ExtensionHost {
 constructor(space){this.space=space;this.instances=new Map();this.disabled=new Set();}
 clear(){for(const i of this.instances.values()){i.cancelled=true;try{i.hooks?.dispose?.();}catch{}}this.instances.clear();this.disabled.clear();}
 async update(){
  const s=this.space,input={intent:s.owner,text:s.editor.value,selection:s.editor.value.slice(s.editor.selectionStart,s.editor.selectionEnd),artifacts:(s.state().artifacts||[]).map(a=>({id:a.id,title:a.title,kind:a.kind}))};
  for(const m of components().filter(m=>!m.builtin)){
   if(this.disabled.has(m.id))continue;
   const score=s.presentation?.components?.[m.id]||0;
   if(!this.instances.has(m.id)&&input.text.length<m.activation.minimumCharacters)continue;
   const admitted=score>=(m.activation.threshold??.75)?score:Math.min(score,.54);
   if(!s.shouldShow(m.id,admitted,!!m.activation.always))continue;
   try{
    let item=this.instances.get(m.id);if(item)item.latestInput=structuredClone(input);
    if(!item){
     const block=s.block(m.id,m.title,'',m.placement,'extension');if(!block)continue;
     item={cancelled:false,latestInput:structuredClone(input)};this.instances.set(m.id,item);
     if(m.style&&!styles.has(m.style)){const link=document.createElement('link');link.rel='stylesheet';link.href=m.style;document.head.append(link);styles.add(m.style);}
     const module=await import(m.entry);if(item.cancelled||s.owner!==input.intent)continue;
     const prefix='wanjie-component:'+input.intent+':'+m.id+':'+m.version;
     item.hooks=module.mount(block.el.querySelector('.growth-body'),Object.freeze({
      getState:()=>{const value=JSON.parse(localStorage.getItem(prefix)||'{}');return validateComponent(value,m.stateSchema);},
      setState:value=>{validateComponent(value,m.stateSchema);const data=JSON.stringify(value);if(data.length>8000)throw new Error('Component state exceeds budget');localStorage.setItem(prefix,data);},
      insert:text=>{if(!navigator.userActivation?.isActive)throw new Error('Insertion requires a user gesture');s.insert({text:String(text).slice(0,12000)});}
     }));
    }
    if(item.cancelled||s.owner!==item.latestInput.intent)continue;validateComponent(item.latestInput,m.inputSchema);item.hooks?.update?.(structuredClone(item.latestInput));
   }catch(error){try{this.instances.get(m.id)?.hooks?.dispose?.();}catch{}this.disabled.add(m.id);console.error('Extension failed',m.id,error);const b=s.blocks.get(m.id);if(b)b.el.querySelector('.growth-body').textContent='此组件暂不可用';}
  }
 }
}
