import {CommandClient} from '../runtime-client.js';
export async function transport(path,body){const response=await fetch('/api/runtime'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});let value;try{value=await response.json()}catch{throw new Error('连接中断，结果不明，请核对任务')}
 if(!response.ok){const e=new Error(value.error||'请求失败');e.code=value.code;e.confirmedFailure=response.status<500;throw e}return value;}
export function createClient(send=transport,storage=localStorage){const commands=new CommandClient(send,storage);let intent=null;return {
 setIntent(id){intent=id},command(type,payload={},options={}){return commands.send(type,payload,intent,options)},
 async snapshot(){return send(intent?'/intents/'+intent:'/state')},reconcile(){return commands.reconcile()},
 async watch(taskId,{signal,onUpdate}={}){while(true){if(signal?.aborted)throw new Error('已停止等待');const s=await this.snapshot();const t=s.tasks.find(t=>t.id===taskId);if(!t)throw new Error('任务尚不可见，请核对');onUpdate?.(t);if(!['queued','running'].includes(t.status))return {task:t,snapshot:s};await new Promise(r=>setTimeout(r,350));}},
 async capability(capability,input){const {task}=await this.command('capability.run',{capability,input});const result=await this.watch(task.id);if(result.task.status!=='success')throw new Error(result.task.error?.message||'判断未完成');return result.task.result},
 async recover(run,{resubmit=false}={}){
  const known=await send('/commands/'+run.runId);
  if(known.found||!resubmit)return known;
  if(!run.payload||run.payload.runId!==run.runId)throw new Error('缺少原始运行载荷，不能安全重发');
  const response=await this.run(run.payload);return {found:true,response};
 },
 run(payload){return this.command('bubble.run',payload,{id:payload.runId})},
 async authorize(){await this.command('intent.update',{preferences:{localOnly:false,autoRun:false}});return this.command('grant.create',{capabilities:['bubble.suggest','bubble.merge','bubble.execute','text.generate','market.query','web.read'],expiresIn:3600,maxCalls:100,network:true,maxEffect:'L2',reason:'用户为本机黑客松 Demo 授权 Jev、生成、资料读取和行情，各次调用记录在当前 Intent'})}
};}
