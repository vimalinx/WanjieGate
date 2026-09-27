// Decide a typed route; the server validates and executes the actual capability.
export function executionFor(b,items,text){
 const r=b.resource||{};
 if(r.action==='desktop')return {capability:'vicinae.launch',input:{command:r.command,query:r.query||''}};
 if(b.kind==='link'){try{const u=new URL(r.url);if(u.protocol!=='https:')throw Error();return {url:u.href}}catch{return {error:'不支持的网页地址'}}}
 if(b.members||b.kind==='action')return {workflow:true};
 if(r.market)return {capability:'market.query',input:{text:r.market}};
 if(r.url)return {capability:'web.read',input:{url:r.url}};
 return {details:true};
}
