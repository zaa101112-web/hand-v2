"""Opt-in authored landmarks -> production recognizer -> real isolated Chrome.

No camera evidence, no command endpoint, and no forced foreground changes.
Start only by clicking the local QA page after inspecting its URL.
"""
import argparse
from dataclasses import asdict,replace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from threading import Thread
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]


def main():
    p=argparse.ArgumentParser();p.add_argument('--ack-real-input',action='store_true',required=True)
    args=p.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from hand_v2.bootstrap import build_runtime
    from tests.continuous_samples import continuous_frames
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    r=build_runtime('WINDOWS_REAL');r.controller.recover('CAMERA_UNAVAILABLE')
    token=secrets.token_hex(16);pages={};armed=False;started=None;hwnd=None;cursor=0
    trace=[];checks=[];executions={};status='WAITING';error=None;baseline=None
    plan=list(continuous_frames(50));last_at=None;max_gap=0
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            name='A' if self.path=='/A' else 'B' if self.path=='/B' else None
            if name is None:return self.send_error(404)
            html='''<!doctype html><meta charset="utf-8"><title>HAND continuous QA NAME</title>
<style>body{font:24px system-ui;background:#f4f7fa;color:#17342f;margin:40px}section{height:700px}button{font:24px system-ui;padding:20px}#metrics{position:fixed;bottom:10px;background:white;padding:10px}</style>
<h1>HAND 연속 동작 검증 · NAME</h1><p>합성 손 좌표 → 실제 단축키 → 이 페이지 효과. 실손 정확도 시험이 아닙니다.</p>
<button id="start">자동 검증 시작 (B 탭에서)</button><section>1</section><section>2</section><section>3</section><div id="metrics"></div>
<script>const token='TOKEN',name='NAME';history.replaceState({step:0},'','#0');for(let step=1;step<=20;step++)history.pushState({step},'','#'+step);
function report(arm=false){const data={token,name,step:history.state.step,ratio:devicePixelRatio,scrollY,focused:document.hasFocus(),visible:document.visibilityState==='visible',arm};document.querySelector('#metrics').textContent=JSON.stringify(data,(['name','step','ratio','scrollY']));fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).catch(()=>{});}
document.querySelector('#start').onclick=()=>{report(true);document.querySelector('#start').hidden=true;};setInterval(()=>report(),100);addEventListener('focus',()=>report());addEventListener('popstate',()=>report());report();</script>'''.replace('TOKEN',token).replace('NAME',name)
            body=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            nonlocal armed
            try:
                size=int(self.headers.get('Content-Length','0'))
                if self.path!='/report' or not 0<size<=2048:return self.send_error(400)
                data=json.loads(self.rfile.read(size))
                if data.get('token')!=token or data.get('name') not in ('A','B'):return self.send_error(403)
                pages[data['name']]={k:v for k,v in data.items() if k!='token'}
                pages[data['name']]['received']=time.monotonic()
                if data.get('arm') and data['name']=='B':armed=True
                self.send_response(204);self.end_headers()
            except (ValueError,UnicodeDecodeError):self.send_error(400)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    Thread(target=server.serve_forever,daemon=True).start()
    session=ROOT/'.build-staging/m09-chrome-session.json'
    session.write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','pid':__import__('os').getpid()}),encoding='utf-8')
    print('Waiting for explicit start on local B page',flush=True)
    def finish(value,reason=None):
        nonlocal status,error
        status=value;error=reason;timer.stop();r.controller.stop('Continuous QA finished')
        closed=r.close()
        if not closed:status='FAIL';error='Key release not confirmed'
        report=dict(status=status,error=error,checks=checks,trace=trace,executions=list(executions.values()),
            source='AUTHORED_LANDMARKS_PRODUCTION_RECOGNIZER_REAL_CHROME',human_accuracy='NOT_RUN',
            shutdown_ok=closed,max_frame_gap_ms=max_gap,foreground_hwnd=hwnd,
            camera_tested=False,owned_keys=list(r.controller.state.keyboard_state.owned_keys))
        (ROOT/'docs/validation/m09-chrome.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(status=status,error=error,checks=len(checks))),flush=True);app.quit()
    def pump():
        nonlocal started,hwnd,cursor,baseline,status,last_at,max_gap
        r.scheduler.run_due();r.pump();fg=r.controller.refresh_target()
        fresh=[page for page in pages.values() if page['focused'] and page['visible'] and time.monotonic()-page['received']<.45]
        page=max(fresh,key=lambda x:x['received']) if fresh else None
        if started is None:
            if not armed or page is None or page['name']!='B' or not fg.is_chrome or r.controller.state.release_pending:return
            started=r.clock.now_ms();hwnd=fg.hwnd;baseline=page.copy();status='RUNNING'
        elif not page or not fg.is_chrome or fg.hwnd!=hwnd:return finish('FAIL','QA page lost focus or fresh heartbeat')
        result=r.controller.state.last_execution
        if result:executions[result.command_id]=asdict(result)
        if cursor>=len(plan):return finish('PASS' if len(checks)==8 else 'FAIL','Missing checks' if len(checks)!=8 else None)
        template=plan[cursor];now=r.clock.now_ms();offset=template.captured_at_ms-1000
        if now-started<offset:return
        if now-started-offset>100:return finish('FAIL','Frame scheduling exceeded 100ms')
        cursor+=1
        if last_at is not None:max_gap=max(max_gap,now-last_at)
        last_at=now
        frame=replace(template,frame_id=now,captured_at_ms=now,camera_epoch=r.controller.state.camera_epoch)
        r.vision.accept(frame);r.controller.flush_executor()
        result=r.vision.last_recognition
        if result.gesture:trace.append(dict(at_ms=now-started,gesture=result.gesture.value))
        i=len(checks)
        if i<8 and template.captured_at_ms>=8500+i*5000:
            expected_count=(1,2,3,4,5,6,8,10)[i]
            effect=(page['name']=='B' and page['step']==19 if i==0 else
                page['name']=='B' and page['step']==20 if i==1 else
                page['name']=='A' if i==2 else page['name']=='B' if i==3 else
                page['scrollY']>0 if i==4 else page['scrollY']==0 if i==5 else
                page['ratio']>baseline['ratio'] if i==6 else page['ratio']==baseline['ratio'])
            sent=[x for x in executions.values() if x['status']=='SENT']
            ok=effect and len(sent)==expected_count and len(executions)==expected_count
            checks.append(dict(task=i+1,expected_commands=expected_count,sent=len(sent),page=page.copy(),passed=ok))
            print(json.dumps(dict(task=i+1,passed=ok)),flush=True)
            if not ok:return finish('FAIL','Page effect or command count mismatch')
    def guarded():
        try:pump()
        except Exception as exc:finish('FAIL',repr(exc))
    timer=QTimer();timer.timeout.connect(guarded);timer.start(10)
    QTimer.singleShot(240000,lambda:finish('FAIL','Overall timeout'))
    app.exec();server.shutdown();server.server_close()
    return 0 if status=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
