// A handoff opens a destination; it never submits generation or claims external completion.
export function safeDestination(value){try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:null}catch{return null}}
export function destinationFor(items,settings={}){
 const direct=items.length===1&&items[0].resource?.url;
 const kind=items.some(b=>b.resource?.market||b.resource?.action==='research')?'market':'writing';
 if(!direct&&kind==='writing'&&settings.writing==='obsidian'&&settings.vault)return {kind:'obsidian',vault:settings.vault};
 const url=safeDestination(direct||settings[kind]);
 return url?{url,kind:direct?'website':kind}:null;
}
export function previewContent(b,items,snapshot){return [b.title,b.description,...items.map(item=>{const a=snapshot?.artifacts?.find(a=>a.id===item.resource?.artifact);return [item.id===b.id?null:item.title,item.id===b.id?null:item.description,a?.content?.text||item.resource?.url||item.resource?.market].filter(Boolean).join('\n')})].filter(Boolean).join('\n\n')}
