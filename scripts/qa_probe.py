"""Read-only assertions for the explicit local Chrome test session."""
import argparse,json,time
from pathlib import Path
from urllib.request import urlopen

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--page');p.add_argument('--activation');p.add_argument('--confirmation',choices=['true','false']);p.add_argument('--foreground',type=int)
args=p.parse_args()
session=json.loads((root/'.build-staging/live-qa-session.json').read_text())
with urlopen(f"http://127.0.0.1:{session['port']}/status",timeout=3) as response:data=json.load(response)
active=[v for v in data['pages'].values() if v['visible']=='visible' and v['focused']]
page=max(active,key=lambda v:v['received'])['name'] if active else None
record={'label':args.label,'at':time.time(),'state':data['state'],'foreground':data['foreground'],'page':page,'pages':data['pages'],'hotkey_registered':data['hotkey_registered'],'panel_hwnd':data['panel_hwnd']}
checks=[]
if args.page:checks.append(page==args.page)
if args.activation:checks.append(data['state']['activation']==args.activation)
if args.confirmation:checks.append(data['state']['confirmation_pending']==(args.confirmation=='true'))
if args.foreground:checks.append(data['foreground']['hwnd']==args.foreground)
record['status']='PASS' if all(checks) else 'FAIL'
path=root/'docs/validation/m02-followup-checks.json'
history=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
history.append(record);path.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'label':args.label,'status':record['status'],'page':page,'foreground':data['foreground']['hwnd'],'activation':data['state']['activation'],'confirmation':data['state']['confirmation_pending'],'last_result':data['state']['last_execution'],'stop':data['state']['last_stop_reason']},ensure_ascii=True))
raise SystemExit(0 if all(checks) else 1)
