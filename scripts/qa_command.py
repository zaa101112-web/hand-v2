"""Controller for the explicitly running local Chrome QA harness."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('action',default='status',nargs='?');args=parser.parse_args()
session=json.loads((ROOT/'.build-staging/live-qa-session.json').read_text())
base=f"http://127.0.0.1:{session['port']}"
if args.action=='status':
    with urlopen(base+'/status',timeout=3) as r:data=json.load(r)
    print(json.dumps(data,ensure_ascii=True,indent=2))
else:
    request=Request(base+'/command',json.dumps({'action':args.action}).encode(),{'Content-Type':'application/json','X-QA-Token':session['token']})
    with urlopen(request,timeout=3) as r:print(r.read().decode())
