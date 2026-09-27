"""Artifact content contracts are checked independently from their envelope."""
import math
from .protocol import Fault, validate

def content_schema(kind):
    string={'type':'string','maxLength':100000};number={'type':'number'}
    array=lambda item:{'type':'array','items':item,'maxItems':1000}
    obj=lambda props,required:{'type':'object','properties':props,'required':required}
    if kind in ('document','note','memory','code','terminal'):
        return obj({'text':string},['text'])
    if kind=='dataset':return obj({'headers':array(string),'rows':array(array(string)),'numeric':array({'type':'integer','minimum':0}),'name':string},['headers','rows','numeric','name'])
    if kind=='analysis':return obj({'columns':array(obj({'name':string,'total':number,'mean':number,'min':number,'max':number,'values':array(number)},['name','total','mean','min','max','values'])),'count':{'type':'integer','minimum':1},'labels':array(string)},['columns','count','labels'])
    if kind=='tasks':return obj({'items':array(obj({'id':string,'title':string,'detail':string,'done':{'type':'boolean'}},['id','title','done']))},['items'])
    if kind=='scene':return obj({'title':string,'blocks':array({'type':'object'})},['blocks'])
    if kind=='web':return obj({'url':{'type':'string','pattern':'^https://','maxLength':2000},'text':string,'title':string},['url'])
    return {}

def validate_content(kind,content):
    validate(content,content_schema(kind),'$.content')
    if kind=='bubble-canvas':
        from .bubbles import validate_canvas
        validate_canvas(content)
    if kind=='dataset':
        h=content['headers'];rows=content['rows'];columns=content['numeric']
        if not h or not rows or not columns or any(len(r)!=len(h) for r in rows) or any(c>=len(h) for c in columns):
            raise Fault('invalid_dataset','表格结构不完整')
        try:
            if not all(math.isfinite(float(r[c])) and abs(float(r[c]))<1e15 for r in rows for c in columns):raise ValueError()
        except (ValueError,TypeError,OverflowError):raise Fault('invalid_dataset','数值列必须为有限数值')
    if kind=='analysis' and not content['columns']:raise Fault('invalid_analysis','缺少统计列')
    if kind=='scene':
        from ..live_runtime import parse_scene
        import json
        for b in content['blocks']:
            if b.get('type')=='quotes':
                validate(b,{'type':'object','required':['items'],'properties':{'items':{'type':'array','maxItems':8,'items':{'type':'object','required':['name','symbol','price','change','percent','currency','asof','source','url'],'properties':{k:{'type':'number'} for k in ('price','change','percent')}}}}})
            else:parse_scene(json.dumps({'blocks':[b]}))
