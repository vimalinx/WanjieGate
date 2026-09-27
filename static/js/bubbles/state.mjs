export function initialState(saved={}){return {input:'',inputRevision:0,bubbles:[],groups:[],positions:{},seen:[],runs:{},undo:null,...saved,pending:null};}
export function visibleBubbles(s){const hidden=new Set(s.groups.flatMap(g=>g.members));return [...s.bubbles,...s.groups.map(g=>({...g,kind:g.operation==='collect'?'collection':'flow',title:g.title||'组合灵感'}))].filter(b=>!hidden.has(b.id));}
export function mergeRequest(s,leftId,rightId){return {interactionId:crypto.randomUUID(),revision:s.inputRevision,leftId,rightId,versions:[...s.bubbles,...s.groups].filter(b=>[leftId,rightId].includes(b.id)).map(b=>[b.id,b.version||0])};}
const protectedIds=s=>new Set([...s.groups.flatMap(g=>g.members),...s.bubbles.filter(b=>b.selected||b.pinned).map(b=>b.id)]);
function snapshot(s){return {bubbles:structuredClone(s.bubbles),groups:structuredClone(s.groups),positions:structuredClone(s.positions)};}
function merge(s,request,operation){const objects=[...s.bubbles,...s.groups];const left=objects.find(b=>b.id===request.leftId),right=objects.find(b=>b.id===request.rightId);if(!left||!right)return s;const group={id:crypto.randomUUID(),version:0,members:[left.id,right.id],operation,title:`${left.title} × ${right.title}`};return {...s,undo:snapshot(s),pending:null,groups:[...s.groups,group],positions:{...s.positions,[group.id]:s.positions[right.id]||{x:.5,y:.78}}};}
export function reduce(state,event){let s=structuredClone(state);switch(event.type){
case 'input':return {...s,input:event.text,inputRevision:s.inputRevision+1,pending:null};
case 'suggestions':{
 if(event.revision!==s.inputRevision)return state;
 const keep=protectedIds(s);const existing=new Set(s.bubbles.map(b=>b.id));
 const pool=event.items.filter(b=>!keep.has(b.id));let base=event.mode==='more'?s.bubbles:s.bubbles.filter(b=>keep.has(b.id));
 const visibleCount=base.filter(b=>!s.groups.some(g=>g.members.includes(b.id))).length;
 const limit=Math.max(0,Math.min(event.mode==='more'?3:6-visibleCount,12-visibleCount));
 let fresh=pool.filter(b=>!existing.has(b.id)&&!s.seen.includes(b.id));
 if(event.mode==='initial')fresh=pool.filter(b=>!base.some(x=>x.id===b.id));
 const chosen=fresh.slice(0,limit);if(event.mode==='refresh'&&!chosen.length)return {...s,notice:'暂时没有其他合适的灵感'};
 return {...s,bubbles:[...base,...chosen],seen:[...new Set([...s.seen,...chosen.map(b=>b.id)])],notice:chosen.length?'':'没有更多合适的灵感'};
}
case 'select':s.bubbles=s.bubbles.map(b=>b.id===event.id?{...b,selected:!b.selected}:b);return s;
case 'pin':return {...s,pending:null,positions:{...s.positions,[event.id]:event.position},bubbles:s.bubbles.map(b=>b.id===event.id?{...b,pinned:true}:b)};
case 'mergeStart':return {...s,pending:{...event.request,status:'pending'}};
case 'mergeCancel':return {...s,pending:null};
case 'mergeResult':if(!s.pending||s.pending.interactionId!==event.request.interactionId||s.inputRevision!==event.request.revision||event.request.versions.some(([id,version])=>![...s.bubbles,...s.groups].some(b=>b.id===id&&(b.version||0)===version)))return state;
 if(event.result.status==='clear')return merge(s,event.request,event.result.operation);
 return {...s,pending:{...s.pending,status:'choice',options:event.result.options}};
case 'mergeChoice':return s.pending?merge(s,s.pending,event.operation):s;
case 'split':return {...s,undo:snapshot(s),pending:null,groups:s.groups.filter(g=>g.id!==event.id)};
case 'undo':return s.undo?{...s,...s.undo,undo:null,pending:null}:s;
case 'remove':if(protectedIds(s).has(event.id))return s;return {...s,bubbles:s.bubbles.filter(b=>b.id!==event.id)};
case 'add':if(s.bubbles.some(b=>b.id===event.bubble.id))return s;return {...s,bubbles:[...s.bubbles,event.bubble]};
case 'runStart':if(s.runs[event.groupId])return s;return {...s,runs:{...s.runs,[event.groupId]:{runId:event.runId,status:'submitting'}}};
case 'runAgain':if(s.runs[event.groupId]&&!['success','failure','cancelled','partial'].includes(s.runs[event.groupId].status))return s;return {...s,runs:{...s.runs,[event.groupId]:{runId:event.runId,status:'submitting'}}};
case 'runUpdate':return {...s,runs:{...s.runs,[event.groupId]:{...s.runs[event.groupId],...event.value}}};
default:return s;
}}
