"""Explicit development QA: authored landmarks -> production core -> REAL Chrome.

Never camera/human accuracy evidence. Requires --ack-real-input, the isolated
Chrome QA page in front, and a fresh focus heartbeat. No production entry point
imports this script; it does not expose a command endpoint.
"""
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
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
    parser=argparse.ArgumentParser()
    parser.add_argument('--ack-real-input',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--session',type=Path,required=True)
    args=parser.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from hand_v2.bootstrap import build_runtime
    from tests.hand_samples import sample_frame
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    runtime=build_runtime('WINDOWS_REAL')
    runtime.controller.recover('CAMERA_UNAVAILABLE')  # Explicit synthetic source only.
    token=secrets.token_hex(16)
    page={'step':None,'focused':False,'visible':False,'armed':False,'received':0}
    history=[];checks=[];executions={};frames=0;max_gap=0;last_frame=None
    status='WAITING_FOR_QA_PAGE';error=None;initial_hwnd=None;started=None;cursor=0
    plan=[];at=0;expected_step=20

    def hold(pose,duration,dx=0,dy=0):
        nonlocal at
        for _ in range(duration//50):
            plan.append((at,'frame',(pose,dx,dy)));at+=50

    hold('V',750);hold('OPEN',350)
    for case in range(20):
        direction=1 if case%2==0 else -1
        pause=(400,1000,3000)[case%3]
        for t in range(0,151,50):
            plan.append((at,'frame',('INDEX',0,-.08*t/150)));at+=50
        hold('INDEX',pause,dy=-.08)
        for t in range(50,551,50):
            plan.append((at,'frame',('INDEX',direction*.24*t/500,-.08)));at+=50
        hold('INDEX',200,dx=direction*.264,dy=-.08)
        hold('FIST',700)
        if case%2==0:
            # Return while not rearmed: must not send the opposite command.
            for t in range(0,551,50):
                plan.append((at,'frame',('INDEX',direction*(.24-.24*t/500),0)));at+=50
        hold('OPEN',900)
        expected_step-=direction
        plan.append((at,'check',{'case':case+1,'direction':'BACK' if direction==1 else 'FORWARD',
                                'pause_ms':pause,'expected_step':expected_step,'expected_events':case+1}));at+=50

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path!='/':return self.send_error(404)
            html='''<!doctype html><meta charset="utf-8"><title>HAND autonomous swipe QA</title>
<style>body{font:24px system-ui;margin:70px;background:#f5f7fa;color:#17342f}b{font-size:70px;color:#087f76}</style>
<h1>HAND 자동 Chrome 검증</h1><p>테스트 손 좌표 → 실제 인식기 → 단축키 → 이 페이지 이동</p>
<p>카메라/실손 인식률 시험과 구분됩니다.</p><button id="start" style="padding:20px;font:24px system-ui">자동 검증 시작</button><p><b id="step"></b></p>
<script>const run='TOKEN';let armed=false;
document.querySelector('#start').onclick=()=>{history.replaceState({run,step:0},'','#0');for(let step=1;step<=20;step++)history.pushState({run,step},'','#'+step);armed=true;document.querySelector('#start').hidden=true;report('load');};
function report(event){let step=history.state?.step??20;document.querySelector('#step').textContent=step;fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run,step,event,armed,focused:document.hasFocus(),visible:document.visibilityState==='visible'})}).catch(()=>{});}
addEventListener('popstate',()=>report('popstate'));setInterval(()=>report('heartbeat'),100);report('load');</script>'''.replace('TOKEN',token)
            body=html.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if self.path!='/report' or not 0<size<=2048:return self.send_error(400)
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict) or data.get('run')!=token:return self.send_error(403)
                if type(data.get('step')) is not int or not 0<=data['step']<=20:return self.send_error(400)
                page.update(step=data['step'],focused=data.get('focused') is True,visible=data.get('visible') is True,armed=data.get('armed') is True,received=time.monotonic())
                if data.get('event') in ('load','popstate'):
                    history.append({'at_utc':datetime.now(timezone.utc).isoformat(),'step':data['step'],'event':data['event']})
                self.send_response(204);self.end_headers()
            except (ValueError,UnicodeDecodeError):self.send_error(400)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    Thread(target=server.serve_forever,daemon=True).start()
    args.session.parent.mkdir(parents=True,exist_ok=True)
    args.session.write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/'}),encoding='utf-8')
    print(f'http://127.0.0.1:{server.server_port}/',flush=True)

    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'source':'AUTHORED_LANDMARKS_PRODUCTION_RECOGNIZER_REAL_CHROME',
            'status':status,'error':error,'checks':checks,'history':history,'executions':list(executions.values()),
            'frames':frames,'max_frame_gap_ms':max_gap,'camera_tested':False,'human_accuracy_evaluated':False,
            'foreground_hwnd':initial_hwnd,'state':asdict(runtime.controller.state)},ensure_ascii=False,indent=2,
            default=lambda value:sorted(value) if isinstance(value,frozenset) else str(value)),encoding='utf-8')
    def finish(new_status,why=None):
        nonlocal status,error
        status=new_status;error=why;timer.stop();runtime.controller.stop('Autonomous QA complete')
        closed=runtime.close()
        if not closed:status='FAIL';error='Keyboard shutdown not confirmed'
        save();print(json.dumps({'status':status,'checks':len(checks),'error':error}),flush=True);app.quit()
    def pump():
        nonlocal status,initial_hwnd,started,cursor,frames,last_frame,max_gap
        runtime.scheduler.run_due();runtime.pump();runtime.controller.refresh_target()
        fg=runtime.foreground.snapshot()
        focused=fg.is_chrome and page['armed'] and page['focused'] and page['visible'] and time.monotonic()-page['received']<.4
        if started is None:
            if not focused or runtime.controller.state.release_pending:return
            initial_hwnd=fg.hwnd;started=runtime.clock.now_ms();status='RUNNING';save()
        elif not focused or fg.hwnd!=initial_hwnd:return finish('FAIL','QA page lost focus or fresh heartbeat')
        result=runtime.controller.state.last_execution
        if result:executions[result.command_id]=asdict(result)
        if cursor>=len(plan):return finish('PASS')
        offset,kind,data=plan[cursor];now=runtime.clock.now_ms()
        if now-started<offset:return
        if now-started-offset>150:return finish('FAIL','Frame scheduling exceeded 150ms')
        cursor+=1
        if kind=='check':
            observed=sum(e['event']=='popstate' for e in history)
            sent=[e for e in executions.values() if e['status']=='SENT']
            ok=(page['step']==data['expected_step'] and observed==data['expected_events']
                and len(sent)==data['expected_events'] and all(e['detail'].startswith('accepted=4/4;') for e in sent))
            checks.append({**data,'actual_step':page['step'],'actual_events':observed,'sent_commands':len(sent),'status':'PASS' if ok else 'FAIL'})
            save();print(json.dumps(checks[-1]),flush=True)
            if not ok:finish('FAIL','Browser effect or unexpected extra navigation')
            return
        pose,dx,dy=data
        frame=sample_frame(now,pose,dx,epoch=runtime.controller.state.camera_epoch)
        hand=frame.hands[0];frame=replace(frame,hands=(replace(hand,landmarks=tuple(replace(p,y=p.y+dy) for p in hand.landmarks)),))
        if last_frame is not None:max_gap=max(max_gap,now-last_frame)
        last_frame=now;frames+=1;runtime.vision.accept(frame);runtime.controller.flush_executor()
    def guarded_pump():
        try:pump()
        except Exception as exc:finish('FAIL',f'QA harness exception: {exc!r}')
    timer=QTimer();timer.timeout.connect(guarded_pump);timer.start(10)
    QTimer.singleShot(240000,lambda:finish('FAIL','Overall test timeout'))
    app.exec();server.shutdown();server.server_close()
    return 0 if status=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
