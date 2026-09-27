export function initialState(saved={}){return {input:'',inputRevision:0,bubbles:[],groups:[],positions:{},seen:[],runs:{},undo:null,...saved,pending:null};}
export function visibleBubbles(s){const hidden=new Set(s.groups.flatMap(g=>g.members));return [...s.bubbles,...s.groups.map(g=>({...g,kind:g.operation==='collect'?'collection':'flow',title:g.title||'组合灵感'}))].filter(b=>!hidden.has(b.id));}
export function mergeRequest(s,leftId,rightId){return {interactionId:crypto.randomUUID(),revision:s.inputRevision,leftId,rightId,versions:[...s.bubbles,...s.groups].filter(b=>[leftId,rightId].includes(b.id)).map(b=>[b.id,b.version||0])};}
const protectedIds=s=>new Set([...s.groups.flatMap(g=>g.members),...s.bubbles.filter(b=>b.selected||b.pinned).map(b=>b.id)]);
function snapshot(s){return {bubbles:structuredClone(s.bubbles),groups:structuredClone(s.groups),positions:structuredClone(s.positions)};}
function merge(s,request,operation){const objects=[...s.bubbles,...s.groups];const left=objects.find(b=>b.id===request.leftId),right=objects.find(b=>b.id===request.rightId);if(!left||!right)return s;const group={id:crypto.randomUUID(),version:0,members:[left.id,right.id],operation,title:`${left.title} × ${right.title}`};return {...s,undo:snapshot(s),pending:null,groups:[...s.groups,group],positions:{...s.positions,[group.id]:request.center||s.positions[right.id]||{x:.5,y:.78}}};}
export function reduce(state,event){let s=structuredClone(state);switch(event.type){
case 'input':return {...s,input:event.text,inputRevision:s.inputRevision+1,pending:null,understanding:null};
case 'suggestions':{
 if(event.revision!==s.inputRevision)return state;
 if(event.understanding)s.understanding=event.understanding;
 const keep=protectedIds(s);const existing=new Set(s.bubbles.map(b=>b.id));
 const pool=event.items.filter(b=>!keep.has(b.id));let base=event.mode==='more'?s.bubbles:s.bubbles.filter(b=>keep.has(b.id));
 const visibleCount=base.filter(b=>!s.groups.some(g=>g.members.includes(b.id))).length;
 const limit=Math.max(0,Math.min(event.mode==='more'?3:6-visibleCount,12-visibleCount));
 let fresh=pool.filter(b=>!existing.has(b.id)&&!s.seen.includes(b.id));
 if(event.mode==='initial')fresh=pool.filter(b=>!base.some(x=>x.id===b.id));
 const chosen=fresh.slice(0,limit);if(event.mode==='refresh'&&!chosen.length)return {...s,notice:'暂时没有其他合适的灵感'};
 return {...s,bubbles:[...base,...chosen],seen:[...new Set([...s.seen,...chosen.map(b=>b.id)])],notice:chosen.length?'':'没有更多合适的灵感'};
}
case 'refreshSource':return {...s,pending:null,bubbles:s.bubbles.map(b=>b.resource?.artifact===event.artifact.id?{...b,title:event.artifact.title,version:(b.version||0)+1,resource:{...b.resource,version:event.artifact.version}}:b)};
case 'select':s.bubbles=s.bubbles.map(b=>b.id===event.id?{...b,selected:!b.selected}:b);return s;
case 'pin':return {...s,pending:null,positions:{...s.positions,[event.id]:{...event.position,userPlaced:true}},bubbles:s.bubbles.map(b=>b.id===event.id?{...b,pinned:true}:b)};
case 'mergeStart':return {...s,pending:{...event.request,status:'pending'}};
case 'mergeCancel':return {...s,pending:null};
case 'mergeResult':if(!s.pending||s.pending.interactionId!==event.request.interactionId||s.inputRevision!==event.request.revision||event.request.versions.some(([id,version])=>![...s.bubbles,...s.groups].some(b=>b.id===id&&(b.version||0)===version)))return state;
 if(event.result.status==='clear')return merge(s,event.request,event.result.operation);
 return {...s,pending:{...s.pending,status:'choice',options:event.result.options}};
case 'mergeChoice':return s.pending&&validInteraction(s,s.pending)&&manualMergeOptions(s,s.pending.leftId,s.pending.rightId).some(o=>o.id===event.operation)?merge(s,s.pending,event.operation):s;
case 'split':return {...s,undo:snapshot(s),pending:null,groups:s.groups.filter(g=>g.id!==event.id)};
case 'undo':return s.undo?{...s,...s.undo,undo:null,pending:null}:s;
case 'remove':if(protectedIds(s).has(event.id))return s;return {...s,bubbles:s.bubbles.filter(b=>b.id!==event.id)};
case 'add':if(s.bubbles.some(b=>b.id===event.bubble.id))return s;return {...s,bubbles:[...s.bubbles,event.bubble]};
case 'runStart':if(s.runs[event.groupId])return s;return {...s,runs:{...s.runs,[event.groupId]:{runId:event.runId,status:'submitting'}}};
case 'runAgain':if(s.runs[event.groupId]&&!['success','failure','cancelled','partial','interrupted'].includes(s.runs[event.groupId].status))return s;return {...s,runs:{...s.runs,[event.groupId]:{runId:event.runId,status:'submitting'}}};
case 'runUpdate':return {...s,runs:{...s.runs,[event.groupId]:{...s.runs[event.groupId],...event.value}}};
default:return s;
}}

export function validInteraction(state, request) {
  if (!request || state.inputRevision !== request.revision) return false;
  const visible = visibleBubbles(state);
  return [request.leftId, request.rightId].every(id => visible.some(b => b.id === id)) &&
    request.versions.every(([id, version]) => visible.some(b => b.id === id && (b.version || 0) === version));
}
export function releaseDisposition(state, session) {
  if (!session.target) return 'pin';
  if (!session.request) return 'start';
  if (state.pending?.interactionId !== session.request.interactionId || !validInteraction(state, session.request)) return 'restore';
  return session.result ? 'apply' : 'wait';
}
export function manualMergeOptions(state, leftId, rightId) {
  const visible = visibleBubbles(state);
  const left = visible.find(b => b.id === leftId), right = visible.find(b => b.id === rightId);
  if (!left || !right || left.kind === 'link' || right.kind === 'link') return [];
  const objects = new Map([...state.bubbles, ...state.groups].map(b => [b.id, b]));
  function count(item) {
    if (item.members) return item.members.reduce((n, id) => n + count(objects.get(id)), item.operation === 'compare' ? 1 : 0);
    return item.kind === 'action' || item.resource?.url || item.resource?.market ? 1 : 0;
  }
  function writes(item) {
    return item.members ? item.members.some(id => writes(objects.get(id))) : item.resource?.action === 'write';
  }
  const steps = count(left) + count(right);
  if (steps > 4 || (/不要.{0,6}(代写|正文|帮我写)|不.{0,3}代写|自己写|别.{0,5}(代写|写正文)/.test(state.input) && (writes(left) || writes(right)))) return [];
  if ([left, right].every(b => ['source', 'collection'].includes(b.kind))) {
    const options = [{id:'collect', label:'汇集为资料集合，暂不执行'}];
    if (steps < 4) options.push({id:'compare', label:'组合为资料对比流程'});
    return options;
  }
  return [left, right].some(b => ['action', 'flow'].includes(b.kind)) ? [{id:'combine', label:'把资料与动作连接为执行组合'}] : [];
}
export function layoutPositions(state, anchors) {
  const items=visibleBubbles(state), positions={}, occupied=[];
  const vacant=p=>!occupied.some(q=>Math.abs(q.x-p.x)<.12&&Math.abs(q.y-p.y)<.17);
  const assign=(id,p)=>{positions[id]=p;occupied.push(p)};
  for(const b of items) {
    const fixed=state.positions[b.id];
    if(fixed&&(fixed.userPlaced||vacant(fixed)))assign(b.id,fixed);
  }
  for(const [i,b] of items.entries()) {
    if(positions[b.id])continue;
    const free=anchors.map(([x,y])=>({x,y})).find(vacant);
    assign(b.id,free||{x:anchors[i%anchors.length][0],y:anchors[i%anchors.length][1]});
  }
  return positions;
}
