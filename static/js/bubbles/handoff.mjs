// A handoff opens a destination; it never submits generation or claims external completion.
export function safeDestination(value){try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:null}catch{return null}}
export const nativeNames={chrome:'Chrome 网页搜索',chatgpt:'ChatGPT',kimi:'Kimi',cursor:'Cursor',zotero:'Zotero',reminders:'提醒事项',stocks:'股市',notes:'备忘录'};
export function applyDetectedTools(settings,profile){const next={...settings};for(const [scene,value]of Object.entries(profile.defaults||{}))if(!next[scene])next[scene]=value;if(!settings.writing&&profile.obsidian?.installed&&profile.obsidian.vaults.length===1){next.writing='obsidian';next.vault=profile.obsidian.vaults[0].id}return next}
export const sceneLabels={writing:'写作',research:'研究',learning:'学习',development:'开发',planning:'计划',market:'行情'};
export function sceneFor(items,snapshot){
 const actions=items.filter(b=>b.resource?.action);
 const scenes=new Set((actions.length?actions:items).map(b=>{
  if(b.scene)return b.scene;
  const a=snapshot?.artifacts?.find(a=>a.id===b.resource?.artifact);
  if(b.resource?.market||a?.kind==='market'||a?.content?.blocks?.some(x=>x.type==='quotes'))return 'market';
  if(['note','document','memory'].includes(a?.kind))return 'writing';
  return {write:'writing',blank:'writing',outline:'writing',research:'market',compare:'research',plan:'planning',quiz:'learning',explain:'learning',code:'development'}[b.resource?.action];
 }).filter(Boolean));
 return scenes.size===1?[...scenes][0]:scenes.size>1?'mixed':null;
}
export function destinationFor(items,settings={},snapshot){
 const direct=items.length===1&&items[0].resource?.url,kind=sceneFor(items,snapshot);
 if(!direct&&kind==='writing'&&settings.writing==='obsidian'&&settings.vault)return {kind:'obsidian',vault:settings.vault};
 const tool=settings[kind]?.startsWith('app:')?settings[kind].slice(4):null;
 if(!direct&&nativeNames[tool])return {kind:'app',tool,name:nativeNames[tool]};
 const url=safeDestination(direct||settings[kind]);
 return url?{url,kind:direct?'website':kind}:null;
}
export function handoffContent(b,items,snapshot){
 const actions=items.filter(x=>x.resource?.action);
 const requests=[...new Set((actions.length?actions:items).map(x=>x.request).filter(Boolean))];
 return [...requests.map(x=>'本次要求（保留所有限制）：'+x),previewContent(b,items,snapshot)].join('\n\n');
}
export function previewContent(b,items,snapshot){return [b.title,b.description,...items.map(item=>{const a=snapshot?.artifacts?.find(a=>a.id===item.resource?.artifact);return [item.id===b.id?null:item.title,item.id===b.id?null:item.description,a?['来源：'+a.source+' · v'+a.version,a.content?.text||JSON.stringify(a.content,null,2)].join('\n'):item.resource?.url||item.resource?.market].filter(Boolean).join('\n')})].filter(Boolean).join('\n\n')}
