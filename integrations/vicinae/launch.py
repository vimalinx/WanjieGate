"""Start the project-owned local runtime and native panel; no external repo edits."""
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'.data/native/Wanjie Intent.app'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def ready():
    try:
        with opener.open('http://127.0.0.1:5175/api/vicinae/status',timeout=1) as r:return r.status==200
    except Exception:return False
if not APP.exists():subprocess.run(['bash',str(ROOT/'integrations/vicinae/build.sh')],check=True)
if not ready():
    env={**os.environ,'WANJIE_DEMO':'1','NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
    # Optional machine-local configuration contains a PATH, never a copied credential.
    config=ROOT/'.data/jev-env-path'
    if config.exists():env['WANJIE_ENV_FILE']=config.read_text().strip()
    log=ROOT/'.data/intent-server.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('ab') as stream:
        subprocess.Popen([sys.executable,'-m','backend.server','--port','5175','--data-dir',str(ROOT/'.data/vicinae-preview')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,start_new_session=True)
    for _ in range(50):
        if ready():break
        time.sleep(.1)
    else:raise SystemExit('万界门服务未启动，请检查 .data/intent-server.log')
subprocess.run(['open','-a',str(APP),'--args',sys.argv[1] if len(sys.argv)>1 else ''],check=True)
