export function toolURL(intent,groupId,run){return '/bubble-tool.html?'+new URLSearchParams({intent,group:groupId,run:run.runId});}
export function resolveRun(snapshot,{taskId,runId,groupId}){
 const task=snapshot.tasks.find(t=>taskId?t.id===taskId:t.input?.runId===runId&&t.input?.groupId===groupId);
 if(!task||task.input?.runId!==runId||task.input?.groupId!==groupId)throw new Error('尚未找到这次运行，请返回画布核对任务');
 const artifacts=(task.artifacts||[]).map(id=>snapshot.artifacts.find(a=>a.id===id)).filter(Boolean);
 const market=task.input.reads?.some(b=>b.resource?.market)||task.input.actions?.includes('research');
 return {task,artifacts,kind:market?'market':'writing'};
}
