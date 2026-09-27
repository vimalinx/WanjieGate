#!/usr/bin/env python3
"""Explicit real Bailian streaming + Hyprland + JEV DAG probe, maximum 8 decisions."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.store import Store
from backend.runtime import Kernel
from backend.runtime.protocol import message,uid
from tools.event_bridge import speech_events,hyprland_event

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--audio',required=True);parser.add_argument('--run',action='store_true');a=parser.parse_args()
    if not a.run:parser.error('--run is required for real paid services')
    root=Path('.ai/live-smoke/control-v02')/uid();root.mkdir(parents=True,mode=0o700)
    kernel=Kernel(Store(root/'state.sqlite3'));tasks=[];events=[]
    def command(kind,payload,iid=None):return kernel.execute(message('command',kind,payload,'renderer',iid))
    iid=command('intent.create',{'title':'真实流式输入验收','state':{'goal':'设计和实现万界门 Intent Runtime','domain':'software'}})['value']['id']
    command('intent.update',{'preferences':{'localOnly':False}},iid)
    command('grant.create',{'capabilities':['semantic.observe'],'expiresIn':600,'maxCalls':8,'network':True,'maxEffect':'L0','reason':'用户授权真实百炼流式 ASR 与 JEV DAG 测试'},iid)
    command('artifact.create',{'kind':'note','title':'万界门接口文档','content':{'text':'Intent Runtime 支持 Event、Signal、Command、Result。'}},iid)
    def send(event,analyze=False):
        events.append(event)
        with (root/'events.jsonl').open('a') as out:out.write(json.dumps(event,ensure_ascii=False)+'\n')
        result=command('event.observe',{'event':event,'analyze':analyze},iid)
        if 'task' in result:tasks.append(result['task']['id'])
        print(json.dumps({'event':event['type'],'text':event['text'],'analyze':analyze},ensure_ascii=False),flush=True)
    try:
        send(hyprland_event(),True)
        partials=0
        for event in speech_events(a.audio):
            analyze=event['final'] or (partials<1 and len(event['text'])>=8)
            if analyze and not event['final']:partials+=1
            send(event,analyze and len(tasks)<8)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline and any(kernel.db.get(t)['status'] in ('queued','running') for t in tasks):time.sleep(.05)
        results=[kernel.db.get(t) for t in tasks]
        report={'intent':iid,'events':len(events),'partials':sum(e['type']=='asr.partial' for e in events),'finals':sum(e['type']=='asr.final' for e in events),'tasks':[{'id':t['id'],'status':t['status'],'error':t.get('error'),'semantic':t.get('result',{}).get('semantic'),'frames':t.get('result',{}).get('control',{}).get('frames',[])} for t in results], 'intentsCreated':len(kernel.db.list('intent'))}
        path=root/'report.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2));path.chmod(0o600)
        print(json.dumps(report,ensure_ascii=False),flush=True);print('Report: '+str(path))
        return 0 if report['finals'] and all(t['status']=='success' for t in results) and report['intentsCreated']==1 else 1
    finally:kernel.shutdown()

if __name__=='__main__':raise SystemExit(main())
