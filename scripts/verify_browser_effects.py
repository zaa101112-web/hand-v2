"""Page-observed assertions against the opt-in live_chrome_qa development harness."""
import argparse,json,time
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',required=True,choices=['back_forward','scroll_zoom_reload','previous_tab','next_tab','reopen','bookmark'])
    parser.add_argument('--output',required=True);args=parser.parse_args()
    session=json.loads((ROOT/'.build-staging/live-qa-session.json').read_text(encoding='utf-8'));base=f"http://127.0.0.1:{session['port']}"
    def status():
        with urlopen(base+'/status',timeout=3) as response:return json.load(response)
    def send(action):
        request=Request(base+'/command',json.dumps({'action':action}).encode(),{'Content-Type':'application/json','X-QA-Token':session['token']})
        with urlopen(request,timeout=3) as response:return json.load(response)
    def wait(check,timeout=5):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            state=status()
            if check(state):return state
            time.sleep(.05)
        raise AssertionError('No expected state/page effect: '+args.case)
    def page(state):
        candidates=[p for p in state['pages'].values() if p['focused'] and p['visible']=='visible']
        return max(candidates,key=lambda p:p['received']) if candidates else {}
    if status()['state']['activation']!='ACTIVE':send('START');wait(lambda s:s['state']['activation']=='ACTIVE')
    cases={
        'back_forward':[('LEFT',lambda a,b:b.get('name')=='A'),('RIGHT',lambda a,b:b.get('name')=='B')],
        'scroll_zoom_reload':[('PAGE_DOWN',lambda a,b:b.get('scrollY',0)>a['scrollY']),('PAGE_UP',lambda a,b:b.get('scrollY',99999)<a['scrollY']),
                              ('ZOOM_IN',lambda a,b:b.get('ratio',0)>a['ratio']),('ZOOM_OUT',lambda a,b:b.get('ratio',999)<a['ratio']),('CIRCLE',lambda a,b:b.get('loads',0)>a['loads'])],
        'previous_tab':[('TAB_LEFT',lambda a,b:b.get('name')=='B')],
        'next_tab':[('TAB_RIGHT',lambda a,b:b.get('name')=='C')],
        'reopen':[('FIST_OPEN',lambda a,b:b.get('name')=='C')],
        'bookmark':[('THUMB',lambda a,b:True)],
    }
    path=ROOT/args.output
    report=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'source':'synthetic semantic gestures -> actual Windows input -> controlled Chrome page effects','records':[]}
    try:
        for gesture,check in cases[args.case]:
            send('neutral');wait(lambda s:s['state']['ready'])
            before=page(status()).copy();previous=status()['state']['last_execution']
            send(gesture)
            sent=wait(lambda s:s['state']['last_execution']!=previous and s['state']['last_execution']['status']=='SENT')
            if gesture=='THUMB':observed=wait(lambda s:s['state']['confirmation_pending'])
            else:observed=wait(lambda s:check(before,page(s)))
            time.sleep(.4)
            report['records'].append({'case':args.case,'gesture':gesture,'status':'PASS','before':before,'after':page(status()),
                                      'result':sent['state']['last_execution'],'confirmation_pending':observed['state']['confirmation_pending']})
            print(gesture,'PASS',flush=True)
    except Exception as exc:
        report['records'].append({'case':args.case,'status':'FAIL','error':str(exc),'observed':status()});raise
    finally:
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
