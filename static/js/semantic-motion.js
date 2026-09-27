// Shared motion grammar: semantic state chooses the transition, never probability per frame.
const out='cubic-bezier(.16,1,.3,1)', damped='cubic-bezier(.2,.8,.2,1)';
export const MOTION=Object.freeze({
 APPROACH:{duration:240,easing:out}, EXPAND:{duration:220,easing:damped},
 RECEDE:{duration:180,easing:'cubic-bezier(.4,0,1,1)'},
 BRANCH:{duration:260,easing:damped}, MERGE:{duration:280,easing:damped},
 SETTLE:{duration:120,easing:damped}, GHOST:{duration:160,easing:out},
 FREEZE:{duration:120,easing:damped},
 // Compatibility names; semanticTransition uses the primitive mappings below.
 RETURN:{duration:300,easing:damped}, INTERRUPT:{duration:180,easing:out}
});
export const TRANSITIONS=Object.freeze({
 BRANCH:{primitive:'BRANCH',duration:260}, RETURN:{primitive:'EXPAND',duration:300},
 CORRECT:{primitive:'RECEDE',duration:180}, WARM:{primitive:'APPROACH',duration:240},
 FOREGROUND:{primitive:'EXPAND',duration:220}, PARK:{primitive:'RECEDE',duration:260},
 INTERRUPT:{primitive:'APPROACH',duration:180}, COMMIT:{primitive:'SETTLE',duration:120},
 MERGE:{primitive:'MERGE',duration:280}, HYPOTHESIS:{primitive:'GHOST',duration:160},
 PREPARED:{primitive:'GHOST',duration:160}, READY:{primitive:'EXPAND',duration:220},
 FREEZE:{primitive:'FREEZE',duration:120}
});
const running=new WeakMap(), ghosts=new WeakMap(), active=new Set();
let preferenceObserver=null, preferenceMedia=null;
function observePreferences(){
 if(preferenceObserver)return;
 const changed=()=>{
  if(reduced())for(const run of [...active]){
   try{run.complete(true);}catch(error){queueMicrotask(()=>{throw error;});}
  }
 };
 preferenceObserver=new MutationObserver(changed);
 preferenceObserver.observe(document.body,{attributes:true,attributeFilter:['class']});
 preferenceMedia=matchMedia('(prefers-reduced-motion: reduce)');
 if(preferenceMedia.addEventListener)preferenceMedia.addEventListener('change',changed);
 else preferenceMedia.addListener(changed);
}
const reduced=()=>document.body.classList.contains('motion-off')||matchMedia('(prefers-reduced-motion: reduce)').matches;
function blocked(el,human){
 if(human)return false;
 return el.classList.contains('is-pinned')||el.dataset.motionPinned==='true'||el.contains(document.activeElement)||
  document.body.classList.contains('dragging-block')||document.body.classList.contains('dragging-material');
}
function snapshot(el){const s=getComputedStyle(el);return {transform:s.transform==='none'?'translate(0,0)':s.transform,opacity:s.opacity,filter:s.filter};}
function result(status,reason){return {status,reason,finished:Promise.resolve({status,reason})};}
function restoreGhost(el){
 const state=ghosts.get(el);if(!state)return;
 el.inert=state.inert;for(const [key,value] of Object.entries(state.styles))el.style[key]=value;
 if(state.aria===null)el.removeAttribute('aria-hidden');else el.setAttribute('aria-hidden',state.aria);
 delete el.dataset.motionStage;ghosts.delete(el);
}
function applyGhost(el){
 if(!ghosts.has(el))ghosts.set(el,{inert:el.inert,aria:el.getAttribute('aria-hidden'),styles:{opacity:el.style.opacity,filter:el.style.filter,pointerEvents:el.style.pointerEvents}});
 el.inert=true;el.setAttribute('aria-hidden','true');el.style.pointerEvents='none';
 el.style.opacity='.45';el.style.filter='blur(.5px)';el.dataset.motionStage='ghost';
}
export function setMotionPinned(el,pinned){
 el.dataset.motionPinned=String(Boolean(pinned));
 if(pinned){stopMotion(el);restoreGhost(el);}
}
export function stopMotion(el){
 const run=running.get(el);if(!run)return;
 running.delete(el);run.cleanup();run.animation.cancel();run.resolve({status:'cancelled'});
}
export function disposeMotion(el){stopMotion(el);restoreGhost(el);delete el.dataset.motionPinned;}

// from/to are viewport rects. direction='exit' moves toward to; default is FLIP after relocation.
// done runs only on completion, never for cancellation or suppressed automatic movement.
export function motion(el,primitive,{from=null,to=null,human=false,done=()=>{},direction=null,duration=null}={}){
 if(!el||!MOTION[primitive])return result('suppressed','unknown-primitive');
 observePreferences();
 if(blocked(el,human))return result('suppressed','user-control');
 const exiting=direction==='exit'||primitive==='RECEDE';
 if(exiting&&!to)return result('suppressed','destination-required');
 const previous=running.has(el),current=snapshot(el);
 stopMotion(el);
 if(primitive==='GHOST')applyGhost(el);else restoreGhost(el);
 const finish=()=>{done({status:'completed'});};
 if(reduced()||typeof el.animate!=='function'){finish();return result('completed','reduced-motion');}
 let frames;
 if(exiting){
  const base=el.getBoundingClientRect(),dx=to.left-base.left,dy=to.top-base.top;
  frames=[current,{transform:`translate(${dx}px,${dy}px) scale(.96)`,opacity:0,filter:'blur(0)'}];
 }else if(from&&to){
  const dx=from.left-to.left,dy=from.top-to.top;
  frames=[{transform:`translate(${dx}px,${dy}px)`,opacity:current.opacity}];
  if(primitive==='BRANCH')frames.push({transform:`translate(${dx*.5}px,${dy*.5-16}px)`,offset:.5});
  frames.push({transform:'translate(0,0)',opacity:1});
 }else if(['SETTLE','FREEZE'].includes(primitive)){
  frames=[previous?current:{transform:'scale(1)'},{transform:'scale(.985)',offset:.5},{transform:'scale(1)'}];
 }else if(primitive==='GHOST'){
  frames=[previous?current:{opacity:0,transform:'scale(.96)',filter:'blur(1px)'},{opacity:.45,transform:'scale(1)',filter:'blur(.5px)'}];
 }else frames=[previous?current:{opacity:.4,transform:'translateY(10px) scale(.98)'},{opacity:1,transform:'translate(0,0)',filter:'blur(0)'}];
 let resolve;const finished=new Promise(r=>{resolve=r;});
 const animation=el.animate(frames,{...MOTION[primitive],duration:duration??MOTION[primitive].duration,fill:'none'});
 const takeControl=()=>{if(!human&&running.get(el)===run)stopMotion(el);};
 const events=['focusin','pointerdown','dragstart'];
 const cleanup=()=>{active.delete(run);for(const event of events)el.removeEventListener(event,takeControl);};
 const complete=(immediate=false)=>{
  if(running.get(el)!==run)return;
  running.delete(el);cleanup();
  if(immediate)animation.cancel();
  resolve({status:'completed'});finish();
 };
 const run={animation,resolve,cleanup,complete};running.set(el,run);active.add(run);
 if(!human)for(const event of events)el.addEventListener(event,takeControl,{once:true});
 animation.finished.then(()=>complete(),()=>{if(running.get(el)===run){running.delete(el);cleanup();resolve({status:'cancelled'});}});
 return {status:'running',finished,cancel:()=>{if(running.get(el)===run)stopMotion(el);}};
}
export function relocate(el,mutate,primitive='EXPAND',human=false){
 if(!el||blocked(el,human))return result('suppressed','user-control');
 const from=el.getBoundingClientRect();stopMotion(el);mutate();const to=el.getBoundingClientRect();
 return motion(el,primitive,{from,to,human});
}
export function semanticTransition(el,transition,options={}){
 const spec=TRANSITIONS[transition];if(!spec)return result('suppressed','unknown-transition');
 return motion(el,spec.primitive,{...options,duration:spec.duration});
}
