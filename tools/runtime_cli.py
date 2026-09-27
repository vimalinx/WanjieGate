#!/usr/bin/env python3
"""Local Intent Runtime client; communicates through the same typed command bus."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.runtime.protocol import message, validate_message, schema, validate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:5173')
    sub=parser.add_subparsers(dest='action',required=True)
    state=sub.add_parser('state');state.add_argument('--intent')
    command=sub.add_parser('command');command.add_argument('type');command.add_argument('payload',nargs='?',default='{}');command.add_argument('--intent');command.add_argument('--key');command.add_argument('--revision',type=int)
    watch=sub.add_parser('watch');watch.add_argument('--intent');watch.add_argument('--after',type=int,default=0);watch.add_argument('--once',action='store_true')
    trace=sub.add_parser('trace');trace.add_argument('correlation')
    check=sub.add_parser('validate');check.add_argument('file');check.add_argument('--schema')
    args=parser.parse_args()
    if args.action=='validate':
        data=json.loads(Path(args.file).read_text())
        if args.schema:validate(data,schema(args.schema))
        else:
            for item in data if isinstance(data,list) else [data]:
                validate_message({k:v for k,v in item.items() if k!='seq'})
        print('valid');return
    target=urllib.parse.urlsplit(args.url)
    if target.scheme!='http' or target.hostname not in ('127.0.0.1','localhost') or target.username or target.password or target.path not in ('','/'):
        parser.error('only loopback HTTP runtime endpoints are accepted')
    def request(path,body=None):
        req=urllib.request.Request(args.url.rstrip('/')+'/api/runtime'+path,data=json.dumps(body,ensure_ascii=False).encode() if body else None,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            print(error.read().decode(),file=sys.stderr);raise SystemExit(1)
    if args.action=='state':result=request('/intents/'+args.intent if args.intent else '/state')
    elif args.action=='trace':result=request('/trace/'+args.correlation)
    elif args.action=='command':
        payload=json.loads(Path(args.payload[1:]).read_text() if args.payload.startswith('@') else args.payload)
        extra={}
        if args.key:extra['idempotencyKey']=args.key
        if args.revision is not None:extra['expectedRevision']=args.revision
        msg=message('command',args.type,payload,'renderer',args.intent,**extra)
        # Print only identity before a mutation so an unknown outcome can be reconciled.
        print('command_id='+msg['id']+' idempotency_key='+msg.get('idempotencyKey',msg['id']),file=sys.stderr)
        result=request('/commands',msg)
    else:
        cursor=args.after
        while True:
            result=request('/messages/'+str(cursor)+('/'+args.intent if args.intent else ''))
            for item in result['messages']:print(json.dumps(item,ensure_ascii=False),flush=True)
            cursor=result['cursor']
            if args.once:return
            time.sleep(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
