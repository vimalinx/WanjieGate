#!/usr/bin/env python3
"""Explicit, bounded real JEV acceptance. Synthetic inputs; five paid calls, no retry."""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.store import Store
from backend.composition import parse_dataset
from backend.runtime import Kernel
from backend.runtime.protocol import message, uid

CASES=[
 ('research','我现在只查阅 JEV 的官方文档，对比它的判断类型，不写代码。','intent.frame','EXPLORE'),
 ('implementation','现在开始修改万界门的 Python 代码，修复意图切换时的并发错误。','intent.frame','ACT'),
 ('writing','请把我们关于万界门架构的讨论写成一篇中文设计说明，给同事阅读。','intent.frame','ACT'),
 ('reminder','换个事，今晚十点提醒我给电脑充电，这和项目无关。','intent.continuity','new'),
 ('analysis','请统计已经导入的销售表：总销售额、平均值、最高值。','capability.selection','data.analyze')]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');parser.add_argument('--case',choices=[c[0] for c in CASES],action='append');args=parser.parse_args()
    if not args.run:parser.error('Explicit --run is required; this makes five real billed calls.')
    cases=[c for c in CASES if not args.case or c[0] in args.case]
    root=Path('.ai/live-smoke/jev-runtime')/uid();root.mkdir(parents=True,mode=0o700)
    kernel=Kernel(Store(root/'state.sqlite3'));rows=[]
    def cmd(type_,payload,iid=None):return kernel.execute(message('command',type_,payload,'renderer',iid))
    try:
        for name,text,signal_name,expected in cases:
            iid=cmd('intent.create',{'title':'JEV 实测 '+name,'state':{'goal':'开发万界门 Intent Runtime','domain':'software'}})['value']['id']
            cmd('intent.update',{'preferences':{'localOnly':False}},iid)
            cmd('grant.create',{'capabilities':['semantic.observe'],'expiresIn':600,'maxCalls':1,'network':True,'maxEffect':'L0','reason':'用户授权的真实 JEV 集成测试；合成输入'},iid)
            cmd('artifact.create',{'kind':'note','title':'架构原则','content':{'text':'Intent 持久保存工作状态，Agent 是临时工作者。'}},iid)
            if name=='analysis':
                cmd('artifact.create',{'kind':'dataset','title':'销售表','content':parse_dataset('日期,销售额\n周一,10\n周二,15','销售表')},iid)
            task=cmd('semantic.observe',{'text':text},iid)['task']
            deadline=time.monotonic()+45
            while task['status'] in ('running','queued') and time.monotonic()<deadline:
                time.sleep(.05);task=kernel.db.get(task['id'])
            events=kernel.db.events(correlation=task['command']['correlationId'])
            signals=[m['payload'] for m in events if m['kind']=='signal']
            answer=next((s for s in signals if s['name']==signal_name),{})
            actual=answer.get('value')
            if signal_name=='capability.selection' and actual:actual=actual[0]['capability']
            if signal_name=='intent.frame' and actual:actual=actual['phase']
            row={'case':name,'task':task['id'],'intent':iid,'status':task['status'],'expected':expected,'actual':actual,
                 'matched':task['status']=='success' and actual==expected,'score':answer.get('score'),'semantic':task.get('result',{}).get('semantic'),
                 'phaseAfter':kernel.db.get(iid)['state']['phase'],'policies':[m['payload'] for m in events if m['type']=='policy.evaluated'],'error':task.get('error')}
            rows.append(row);report=root/'report.json';report.write_text(json.dumps(rows,ensure_ascii=False,indent=2));report.chmod(0o600)
            print(json.dumps({k:v for k,v in row.items() if k!='policies'},ensure_ascii=False),flush=True)
            if task['status']!='success':break
    finally:kernel.shutdown()
    print('Report: '+str(root/'report.json'))
    return 0 if len(rows)==len(cases) and all(r['matched'] for r in rows) else 1

if __name__=='__main__':raise SystemExit(main())
