// Deterministic presentation policy; callers supply only accepted, current semantic samples.
export const COMPOSITION_THRESHOLDS=Object.freeze({strong:.75,weak:.55,exit:.3,consecutive:2});
export class CompositionPolicy {
 constructor(){this.components=new Map();}
 _entry(id){
  if(typeof id!=='string'||!id.trim())throw new TypeError('A stable component identity is required');
  let entry=this.components.get(id);
  if(!entry){entry={state:'cold',weak:0,low:0,dismissed:false,seen:new Set()};this.components.set(id,entry);}
  return entry;
 }
 evaluate(id,{score,sample,pinned=false,explicit=false,interacting=false,dismissed}={}){
  const entry=this._entry(id),previous=entry.state;
  const finish=(reason,accepted=false)=>{
   const changed=entry.state!==previous;
   let transition=null;
   if(changed){
    if(entry.state==='park')transition='PARK';
    else if(previous==='park')transition='RETURN';
    else if(entry.state==='hot')transition='FOREGROUND';
    else if(entry.state==='near')transition='READY';
   }
   return {id,state:entry.state,transition,changed,accepted,reason};
  };
  if(dismissed===true)entry.dismissed=true;
  const fresh=typeof sample==='string'&&sample.length>0&&!entry.seen.has(sample);
  const valid=typeof score==='number'&&Number.isFinite(score)&&score>=0&&score<=1;
  // Samples observed during user constraints are consumed, not replayed when constraints lift.
  if(fresh&&valid)entry.seen.add(sample);
  if(entry.dismissed){
   entry.weak=0;entry.low=0;
   if(entry.state!=='cold')entry.state='park';
   return finish('dismissed',fresh&&valid);
  }
  if(pinned||explicit){
   entry.state='hot';entry.weak=0;entry.low=0;
   return finish(pinned?'pinned':'explicit',fresh&&valid);
  }
  if(interacting){entry.weak=0;entry.low=0;return finish('interacting',fresh&&valid);}
  if(!fresh||!valid)return finish(!valid?'invalid-score':'duplicate-or-missing-sample');
  if(score>=COMPOSITION_THRESHOLDS.strong){
   entry.state='hot';entry.weak=0;entry.low=0;return finish('strong',true);
  }
  if(score>=COMPOSITION_THRESHOLDS.weak){
   entry.weak+=1;entry.low=0;
   if(entry.weak>=COMPOSITION_THRESHOLDS.consecutive&&['cold','park'].includes(entry.state))entry.state='near';
   return finish(entry.weak>=COMPOSITION_THRESHOLDS.consecutive?'stable-candidate':'candidate-pending',true);
  }
  entry.weak=0;
  if(score<COMPOSITION_THRESHOLDS.exit){
   entry.low+=1;
   if(entry.low>=COMPOSITION_THRESHOLDS.consecutive&&['near','hot'].includes(entry.state))entry.state='park';
   return finish(entry.low>=COMPOSITION_THRESHOLDS.consecutive?'low-relevance':'exit-pending',true);
  }
  entry.low=0;return finish('hysteresis-band',true);
 }
 restore(id){
  const entry=this._entry(id);entry.dismissed=false;entry.weak=0;entry.low=0;
  // Explicit re-opening is an immediate human decision, independent of the next model sample.
  const previous=entry.state;entry.state='hot';
  return {id,state:'hot',transition:previous==='hot'?null:'RETURN',changed:previous!=='hot',accepted:false,reason:'restored'};
 }
 forget(id){this.components.delete(id);}
 clear(){this.components.clear();}
}
export const createCompositionPolicy=()=>new CompositionPolicy();
const defaultPolicy=createCompositionPolicy();
export const evaluate=(id,options)=>defaultPolicy.evaluate(id,options);
export const restore=(id)=>defaultPolicy.restore(id);
