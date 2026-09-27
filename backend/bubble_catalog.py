"""Bounded resources and actions; model decisions never invent executable capabilities."""
import re
from urllib.parse import quote, urlsplit
from .bubble_presets import PRESETS

ACTIONS={
 'explain':('讲解这个知识点','按用户要求解释概念或错题，交给学习工具'),
 'quiz':('根据材料出题','按用户指定数量和节奏出题，保留是否给答案的约束'),
 'code':('分析与处理代码','在用户选择的开发工具中解释、调试或编写测试，遵守只读约束'),
 'write':('写一篇草稿','依据所选资料撰写正文'),
 'outline':('生成提纲','依据资料生成结构与要点，不代写正文'),
 'research':('整理研究卡片','整理行情与已提供资料，列出待核实问题'),
 'compare':('对比资料','对照两份或更多资料的共同点与差异'),
 'plan':('形成行动清单','把目标和所选资料整理为行动清单'),
 'blank':('打开空白文稿','让用户自己写，不代写'),
}

ACTIONS.update({key:(value['title'],value['description']) for key,value in PRESETS.items()})

def candidates(text,artifacts):
    result=[{'id':'action:'+k,'kind':'action','title':v[0],'description':v[1],'resource':{'action':k}} for k,v in ACTIONS.items()]
    # Historical sources are explicitly chosen from the library, never ranked by title.
    links=[('typesafe','Jev 官方文档','https://docs.typesafe.ai/','人工智能、Jev、决策模型的官方资料'),('gutenberg','公版阅读书库','https://www.gutenberg.org/','文学、读书、阅读与公版书目录'),('python','Python 官方教程','https://docs.python.org/zh-cn/3/tutorial/','编程学习、Python 教程'),('sec','公司公开披露','https://www.sec.gov/edgar/search/','上市公司与股票研究资料入口')]
    for id_,title,url,desc in links:result.append({'id':'web:'+id_,'kind':'source','title':title,'description':desc+' · 尚未读取','resource':{'url':url,'detail':'excerpt'}})
    for i,url in enumerate(re.findall(r'https://[^\s<>"\u3000]+',text)[:4]):
        url=url.rstrip('。，；）)')
        result.append({'id':'url:'+str(i)+':'+url,'kind':'source','title':urlsplit(url).netloc,'description':'用户提供的链接 · 尚未读取','resource':{'url':url,'detail':'excerpt'}})
    result.append({'id':'market:query','kind':'source','title':'查询股票行情','description':'获取当前输入标的的公开报价和走势；以来源时间为准','resource':{'market':text,'detail':'full'}})
    result.append({'id':'search:web','kind':'link','title':'打开网页搜索','description':'在浏览器搜索当前主题，不自动读取结果','resource':{'url':'https://www.bing.com/search?q='+quote(text)}})
    result.append({'id':'search:maps','kind':'link','title':'探索附近去处','description':'生活出行、地点和路线，打开地图搜索','resource':{'url':'https://www.google.com/maps/search/'+quote(text)}})
    return result[:50]

def no_writing(text):
    return bool(re.search(r'不要.{0,6}(代写|正文|帮我写)|不.{0,3}代写|自己写|别.{0,5}(代写|写正文)',text))

def merge_options(left,right):
    kinds=[left['kind'],right['kind']]
    if 'link' in kinds:return {'none':'这些是外部入口，不能直接作为已取得的资料执行'}
    options={}
    if all(k in ('source','collection') for k in kinds):
        options['collect']='把两份资料汇集到一个集合，暂不执行'
        options['compare']='读取并对比两份资料，生成对照文稿'
    if any(k in ('action','flow') for k in kinds):
        options['combine']='将资料提供给动作，或按已有依赖顺序连接操作'
    options['none']='没有合适组合，或信息不足，需要用户补充'
    return options

def choose_merge(answer,options):
    probs=answer['probabilities'];ordered=sorted(probs.values(),reverse=True)
    choice=answer['choice'];top=probs[choice]
    clear=choice!='none' and top>=.85 and top-(ordered[1] if len(ordered)>1 else 0)>=.25
    return {'status':'clear' if clear else 'choice','operation':choice if clear else None,'options':[{'id':k,'label':options[k],'probability':probs[k]} for k in sorted(options,key=lambda k:probs[k],reverse=True) if k!='none'][:3]}
