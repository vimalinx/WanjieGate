#!/usr/bin/env python3
"""Read-only host/ASR adapters -> typed raw events. No mailbox or input injection."""
import argparse
import json
import re
import subprocess
import sys
import time
import uuid

def hyprland_event():
    result=subprocess.run(['hyprctl','-j','activewindow'],capture_output=True,text=True,timeout=3,check=True)
    window=json.loads(result.stdout)
    # No window title, document text or browser URL is collected.
    facts={k:window[k] for k in ('class','pid','monitor') if k in window}
    return {'type':'window.focus','source':'hyprland','text':'当前前台应用类别：'+str(facts.get('class','unknown')),
            'final':True,'observedAt':int(time.time()*1000),'facts':facts}

def speech_events(file,model='fun-asr-realtime'):
    argv=['bl-live-asr','--file',file,'--model',model,'--quiet-sentences']
    proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stream=uuid.uuid4().hex;seq=0;utterance=0;buffer=bytearray()
    def event(raw):
        nonlocal seq,utterance
        text=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',raw.decode(errors='replace')).strip()
        if not text:return None
        final=bool(re.match(r'^\[\d\d:\d\d:\d\d\]',text))
        if text.startswith('!!'):raise RuntimeError('百炼实时 ASR 返回错误；不自动重试')
        if not final and not text.startswith('… '):return None
        text=re.sub(r'^\[\d\d:\d\d:\d\d\]\s*|^…\s*','',text)
        seq+=1
        result={'type':'asr.final' if final else 'asr.partial','source':'bailian:'+model,'text':text,'final':final,
                'stream':stream+':'+str(utterance),'sequence':seq,'observedAt':int(time.time()*1000)}
        if final:utterance+=1
        return result
    try:
        while True:
            byte=proc.stdout.read(1)
            if not byte:break
            if byte in (b'\r',b'\n'):
                e=event(buffer);buffer.clear()
                if e:yield e
            else:buffer.extend(byte)
        if buffer:
            e=event(buffer)
            if e:yield e
        if proc.wait(timeout=5)!=0:raise RuntimeError('百炼实时 ASR 未完成；没有重试')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        proc.stdout.close();proc.stderr.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--hyprland',action='store_true');parser.add_argument('--audio');parser.add_argument('--model',default='fun-asr-realtime');a=parser.parse_args()
    if a.hyprland:print(json.dumps(hyprland_event(),ensure_ascii=False),flush=True)
    if a.audio:
        for e in speech_events(a.audio,a.model):print(json.dumps(e,ensure_ascii=False),flush=True)
