#!/usr/bin/env python3
"""One live KEV probe with the current multi-capability contract (no cloud generation)."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.providers import Kev
if __name__=='__main__':
    text=' '.join(sys.argv[1:]) or '分析这周销售数据，整理周报并列出下周行动计划'
    scores,decision=Kev().decide(text,{'dataset':{'name':'演示数据','columns':['日期','销售额']}})
    print(json.dumps({'text':text,'scores':scores,'decision':decision},ensure_ascii=False,indent=2))
