"""Opt-in local tool discovery and narrowly scoped Obsidian handoff.

No browser history, note contents, or other application databases are scanned.
"""
import hashlib
import json
import re
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlencode, quote

CONFIG = Path.home() / 'Library/Application Support/obsidian/obsidian.json'
LOCK = threading.Lock()

def vaults(config=CONFIG):
    try:
        value=json.loads(config.read_text())
        return {key:Path(item['path']) for key,item in value.get('vaults',{}).items()
                if isinstance(item,dict) and isinstance(item.get('path'),str) and Path(item['path']).is_dir()}
    except (OSError, ValueError, TypeError):
        return {}

def discover(app_roots=None, config=CONFIG):
    roots=app_roots or [Path('/Applications'),Path.home()/'Applications']
    installed=any((root/'Obsidian.app').is_dir() for root in roots)
    return {'obsidian':{'installed':installed,'vaults':[{'id':key,'name':path.name} for key,path in vaults(config).items()] if installed else []},
            'sources':['installed-supported-apps','obsidian-vault-names'], 'historyCollected':False}

def launch_obsidian(request, data_dir, config=CONFIG):
    vault=request.get('vault');available=vaults(config)
    if vault not in available:raise ValueError('请选择本机存在的 Obsidian 仓库')
    identity=request.get('id');content=request.get('content');title=request.get('title')
    if not all(isinstance(v,str) for v in [identity,content,title]) or not identity or len(content)>16000:
        raise ValueError('交接内容格式错误或超过 16000 字符，请改用复制内容')
    digest=hashlib.sha256(json.dumps([vault,identity,content],ensure_ascii=False).encode()).hexdigest()
    title=re.sub(r'[^\w\u4e00-\u9fff -]', '', title).strip()[:36] or '新笔记'
    file=f'万界门/{title}-{digest[:12]}.md'
    receipts=Path(data_dir)/'tool-handoffs';receipts.mkdir(parents=True,exist_ok=True)
    receipt=receipts/(digest+'.json')
    with LOCK:
        if receipt.exists():
            saved=json.loads(receipt.read_text())
            if (available[vault]/saved['file']).is_file():
                uri='obsidian://open?'+urlencode({'vault':vault,'file':saved['file'],'paneType':'tab'},quote_via=quote)
                try:
                    subprocess.run(['open','-a','Obsidian',uri],check=True,timeout=10,capture_output=True)
                except (OSError,subprocess.SubprocessError):
                    return {**saved,'reused':True,'status':'outcome_unknown'}
            return {**saved,'reused':True}
        exists=(available[vault]/file).is_file()
        params={'vault':vault,'file':file,'paneType':'tab'}
        if not exists:params['content']=content
        uri='obsidian://'+('open' if exists else 'new')+'?'+urlencode(params, quote_via=quote)
        # Reserve before dispatch: ambiguous OS failures are never automatically retried.
        result={'status':'dispatching','file':file,'vault':vault,'reused':False}
        receipt.write_text(json.dumps(result,ensure_ascii=False))
        try:
            subprocess.run(['open','-a','Obsidian',uri],check=True,timeout=10,capture_output=True)
            result['status']='handed_off'
        except (OSError,subprocess.SubprocessError):
            result['status']='outcome_unknown'
        receipt.write_text(json.dumps(result,ensure_ascii=False))
        return result
