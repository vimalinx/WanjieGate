// Commands survive a lost HTTP response. A retry reuses the same message identity.
export class CommandClient {
  constructor(transport, storage) { this.transport=transport; this.storage=storage; }
  async send(type,payload={},intent=null,options={}) {
    const signature=JSON.stringify([type,payload,intent,options]);
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(signature));
    const key='wanjie-command:'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
    let command=JSON.parse(this.storage.getItem(key)||'null');
    if(command) {
      const prior=await this.transport('/commands/'+command.id);
      if(prior.found){this.storage.removeItem(key);return prior.response;}
    } else {
      command={protocolVersion:'0.1',id:crypto.randomUUID(),kind:'command',type,timestamp:Date.now(),source:'renderer',payload,ttl:120000,...options};
      if(intent)command.intent=intent;
      command.idempotencyKey=command.id;
      this.storage.setItem(key,JSON.stringify(command));
    }
    try { const result=await this.transport('/commands',command);this.storage.removeItem(key);return result; }
    catch(error) {if(error.confirmedFailure)this.storage.removeItem(key);throw error;}
  }
  pending(){return Object.keys(this.storage).filter(k=>k.startsWith('wanjie-command:')).map(k=>({key:k,command:JSON.parse(this.storage.getItem(k))}));}
  async reconcile(){const result=[];for(const p of this.pending()){const response=await this.transport('/commands/'+p.command.id);if(response.found)this.storage.removeItem(p.key);result.push({...p,...response});}return result;}
}
