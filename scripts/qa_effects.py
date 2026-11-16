"""Assert page-observed effects through the running explicit local test harness."""
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
session=json.loads((ROOT/'.build-staging/live-qa-session.json').read_text())
base=f"http://127.0.0.1:{session['port']}"
def status():
    with urlopen(base+'/status',timeout=3) as r:return json.load(r)
def send(action):
    request=Request(base+'/command',json.dumps({'action':action}).encode(),{'Content-Type':'application/json','X-QA-Token':session['token']})
    with urlopen(request,timeout=3) as r:json.load(r)
def wait_for(predicate,timeout=4):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=status()
        if predicate(value):return value
        time.sleep(.05)
    raise AssertionError('Timed out waiting for observed effect')
def page(s):return max((p for p in s['pages'].values() if p['focused'] and p['visible']=='visible'),key=lambda p:p['received'])
def execute(gesture):
    send('neutral')
    wait_for(lambda s:s['state']['ready'])
    previous=status()['state']['last_execution']
    send(gesture)
    return wait_for(lambda s:s['state']['last_execution']!=previous and s['state']['last_execution']['status']=='SENT')

records=[]
path=ROOT/'docs/validation/m02-chrome-effects.json'
cases=[('RIGHT',lambda a,b:b['name']=='B'),('PAGE_DOWN',lambda a,b:b['scrollY']>a['scrollY']),
       ('PAGE_UP',lambda a,b:b['scrollY']<a['scrollY']),('ZOOM_IN',lambda a,b:b['ratio']>a['ratio']),
       ('ZOOM_OUT',lambda a,b:b['ratio']<a['ratio']),('CIRCLE',lambda a,b:b['loads']>a['loads'])]
for gesture,check in cases:
    before=page(status()).copy()
    try:
        sent=execute(gesture)
        observed=wait_for(lambda s:check(before,page(s)))
        time.sleep(.35)  # Allow Chrome's scroll/zoom animation to settle before the next baseline.
        after=page(status()).copy()
        records.append({'gesture':gesture,'status':'PASS','before':before,'after':after,'input_result':sent['state']['last_execution']})
        print(gesture,'PASS',json.dumps(after))
    except Exception as error:
        records.append({'gesture':gesture,'status':'FAIL','error':repr(error),'before':before,'observed':status()})
        raise
    finally:
        path.write_text(json.dumps({'source':'REAL_CHROME_EFFECTS_SYNTHETIC_GESTURES','records':records},indent=2),encoding='utf-8')
