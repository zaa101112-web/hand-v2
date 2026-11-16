"""Fresh onedir staging; no overwriting running builds or user settings."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--label',default='m03')
args=parser.parse_args()
if not args.label.replace('-','').isalnum():parser.error('label must contain only letters, numbers, or hyphens')
label=args.label
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
stage=ROOT/'.build-staging'/stamp
stage.mkdir(parents=True,exist_ok=False)
env=dict(os.environ)
for name in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
    env.pop(name,None)
windows=Path(os.environ['WINDIR'])
env['PATH']=os.pathsep.join([str(Path(sys.executable).parent),str(windows/'System32'),str(windows)])
env['PYINSTALLER_CONFIG_DIR']=str(stage/'cache')
env['PYTHONIOENCODING']='utf-8'
cmd=[sys.executable,'-m','PyInstaller','--onedir','--windowed','--clean','--name','HAND-v2',
     '--paths',str(ROOT/'src'),'--distpath',str(stage/'dist'),'--workpath',str(stage/'work'),
     '--specpath',str(stage),'--add-data',str(ROOT/'models')+':models',
     '--add-data',str(ROOT/'config')+':config','--collect-all','mediapipe','--collect-all','cv2',
     '--hidden-import','mss','--hidden-import','numpy',str(ROOT/'run.py')]
started=time.monotonic()
log=ROOT/f'docs/validation/{label}-build.log'
with log.open('w',encoding='utf-8') as stream:
    result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
report={'at_utc':datetime.now(timezone.utc).isoformat(),'stage':str(stage.relative_to(ROOT)),
        'exit_code':result.returncode,'duration_seconds':round(time.monotonic()-started,2),
        'lock_sha256':hashlib.sha256((ROOT/'requirements-lock.txt').read_bytes()).hexdigest(),
        'clean_pc_test':'NOT_RUN','fresh_staging':True,'path_sanitized':True}
if result.returncode==0:
    exe=stage/'dist/HAND-v2/HAND-v2.exe'
    report['exe']=str(exe.relative_to(ROOT))
    report['exe_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
    files=[]
    for path in sorted(exe.parent.rglob('*')):
        if path.is_file():files.append({'path':path.relative_to(exe.parent).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest=ROOT/f'docs/validation/{label}-artifact-manifest.json'
    manifest.write_text(json.dumps(files,indent=2),encoding='utf-8')
    report['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
    report['bundle_bytes']=sum(item['bytes'] for item in files)
    smoke_env=dict(env,PATH=os.pathsep.join([str(windows/'System32'),str(windows)]),QT_QPA_PLATFORM='offscreen')
    smoke=subprocess.run([str(exe),'--mode','DEV_SIMULATED','--smoke','--smoke-report',str(ROOT/f'docs/validation/{label}-bundle-smoke.json')],cwd=stage,env=smoke_env,timeout=60)
    report['offscreen_smoke_exit_code']=smoke.returncode
(ROOT/f'docs/validation/{label}-build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(result.returncode if result.returncode else report.get('offscreen_smoke_exit_code',2))
