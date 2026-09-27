#!/usr/bin/env python3
"""Explicit paid live check; private receipts stay outside Git. Never prints credentials."""
import argparse,json,tempfile,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.bubble_providers import load_config,JevClient,OpenRouterGenerator
from backend.runtime.bubbles import install_bubbles
from backend.runtime import Kernel
from backend.runtime.protocol import message
from backend.store import Store

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--env-file',required=True);parser.add_argument('--model',default='deepseek/deepseek-chat-v3.1');parser.add_argument('--flow',choices=['writing','market','decisions'],required=True);args=parser.parse_args()
    cfg=load_config(args.env_file);cfg['WANJIE_GENERATION_MODEL']=args.model;generator=OpenRouterGenerator(cfg);jev=JevClient(cfg)
    out=Path('.ai/test-data/bubble-live');out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        k=Kernel(Store(Path(tmp)/'live.sqlite'),generator);install_bubbles(k,jev,generator);intent=None
        def call(t,p):return k.execute(message('command',t,p,'renderer',intent))
        def wait(t):
            for _ in range(900):
                a=k.db.get(t['id'],'task')
                if a['status'] not in ('queued','running'):return a
                time.sleep(.1)
            raise RuntimeError('等待任务超过 90 秒')
        def cap(name,inp):
            t=wait(call('capability.run',{'capability':name,'input':inp})['task'])
            if t['status']!='success':raise RuntimeError(t.get('error'))
            return t['result']
        try:
            intent=call('intent.create',{'title':'Live '+args.flow})['value']['id'];call('intent.update',{'preferences':{'localOnly':False}});call('grant.create',{'capabilities':['bubble.suggest','bubble.merge','bubble.execute','web.read','market.query','text.generate'],'network':True,'maxEffect':'L2','maxCalls':30,'expiresIn':600,'reason':'显式真实验收'})
            receipt={'flow':args.flow,'time':time.strftime('%Y-%m-%d %H:%M:%S'),'model':args.model}
            if args.flow=='decisions':
                receipt['cases']=[]
                for text in ['我想自己写一篇读书感想，不要代写正文','先找 Python 官方资料，暂时不要写正文','改成股票研究，查询上证指数 sh000001 并整理研究卡片']:
                    result=cap('bubble.suggest',{'text':text});receipt['cases'].append({'input':text,**result})
                receipt['merge']=cap('bubble.merge',{'text':'把两份阅读笔记放在一起，先不执行','left':{'kind':'source','title':'阅读笔记一'},'right':{'kind':'source','title':'阅读笔记二'}})
            else:
                bubbles=[]
                if args.flow=='writing':
                    for title,text in [('阅读笔记一','读书时把问题写在纸上，读完一章后尝试用自己的话复述。这样可以发现不理解的地方。'),('阅读笔记二','把不同章节的观点放在一起比较，记录相同之处和冲突之处。定期回看自己的批注。')]:
                        a=call('artifact.create',{'kind':'note','title':title,'content':{'text':text},'source':'验收者手写样例'})['value'];bubbles.append({'id':a['id'],'kind':'source','title':title,'resource':{'artifact':a['id'],'version':a['version'],'detail':'full'}})
                    action='write';request='根据两份笔记写一篇 200 字以内的阅读方法感想，分别引用两个来源。'
                else:
                    bubbles=[{'id':'quote','kind':'source','title':'上证指数行情','resource':{'market':'上证指数 sh000001 股票行情','detail':'full'}}];action='research';request='整理上证指数 sh000001 研究卡片，200 字以内，明确写报价时间和未添加新闻，不作交易建议。'
                bubbles.append({'id':'action','kind':'action','resource':{'action':action},'title':'执行'})
                content={'input':request,'bubbles':bubbles,'groups':[{'id':'group','members':[b['id'] for b in bubbles],'operation':'combine'}],'positions':{}}
                c=call('artifact.create',{'kind':'bubble-canvas','title':'验收组合','content':content})['value'];runid='live-'+args.flow+'-'+str(time.time_ns());cmd=message('command','bubble.run',{'runId':runid,'canvas':c['id'],'version':c['version'],'groupId':'group','text':request},'renderer',intent);cmd['id']=cmd['idempotencyKey']=runid
                first=k.execute(cmd);duplicate=k.execute(cmd);assert first['task']['id']==duplicate['task']['id'];t=wait(first['task']);receipt['task']=t;receipt['artifacts']=[k.db.get(a,'artifact') for a in t['artifacts']]
                if t['status']!='success':
                    (out/(args.flow+'-failed.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2));raise RuntimeError(t.get('error'))
                doc=receipt['artifacts'][-1];assert doc['kind']=='document';assert len(doc['content']['sources'])==(2 if args.flow=='writing' else 1)
            path=out/(args.flow+'.json');path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2));path.chmod(0o600);print(json.dumps({'flow':args.flow,'status':'success','model':args.model,'receipt':str(path)},ensure_ascii=False))
        finally:k.shutdown()
if __name__=='__main__':main()
