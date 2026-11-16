"""Explicit local test harness: synthetic gestures, REAL input, NO camera evidence.

Run only with --ack-real-input and an isolated Chrome profile on the served QA pages.
The production entry point does not expose these control endpoints or camera bypass.
"""
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from queue import SimpleQueue, Empty
import secrets
import sys
from threading import Thread
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ack-real-input',action='store_true',required=True)
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--label',default='m02-live-session')
    args=parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.qt.window import MainWindow
    from hand_v2.domain.models import Gesture, GestureEvent, ExecutionMode
    app=QApplication([])
    runtime=build_runtime(ExecutionMode.REAL)
    window=MainWindow(runtime)
    # Synthetic gesture source is restricted to this explicitly invoked test harness.
    runtime.controller.recover('CAMERA_UNAVAILABLE')
    queue=SimpleQueue()
    token=secrets.token_urlsafe(24)
    pages={}
    outcomes=[]
    actions=[]
    initial_hwnd=None
    file=ROOT/'.build-staging/live-qa-session.json'
    file.parent.mkdir(exist_ok=True)
    panel_hwnd=int(window.mini_panel.winId())  # Qt objects are accessed only on their owning thread.

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,data,content='application/json'):
            body=data.encode() if isinstance(data,str) else json.dumps(data,ensure_ascii=False,default=str).encode()
            self.send_response(200);self.send_header('Content-Type',content+'; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/status':
                return self.reply({'state':asdict(runtime.controller.state),'foreground':asdict(runtime.foreground.snapshot()),
                                   'pages':pages,'actions':actions[-30:],'outcomes':outcomes[-30:],
                                   'hotkey_registered':bool(window.hotkey and window.hotkey.registered),
                                   'panel_hwnd':panel_hwnd})
            if self.path.startswith('/page/'):
                name=self.path.split('/')[-1]
                if name not in ('A','B','C'): self.send_error(404);return
                html='''<!doctype html><meta charset="utf-8"><title>HAND V2 QA PAGE __NAME__</title>
<style>body{margin:40px;font:22px system-ui;background:#f5f7fa;color:#17342f}header{padding:25px;background:#dff3ed}section{height:650px;border-bottom:2px solid #087f76}a{padding:15px;display:inline-block}#metrics{position:fixed;bottom:0;background:white;padding:12px;font:16px monospace}</style>
<header><h1>HAND V2 QA · PAGE __NAME__</h1><p>독립 Chrome 시험 창 · 실제 단축키 효과 확인</p><a href="/page/A">Page A</a><a href="/page/B">Page B</a><a href="/page/C" target="_blank">Open page C in new tab</a></header>
<section>Section 1</section><section>Section 2</section><section>Section 3</section><section>Section 4</section><div id="metrics"></div>
<script>const name='__NAME__';const loaded=Date.now(); const loads=+(sessionStorage.getItem(name)||0)+1;sessionStorage.setItem(name,loads);let last='';
function report(){const p={name,visible:document.visibilityState,focused:document.hasFocus(),scrollY,ratio:devicePixelRatio,width:innerWidth,loads,loaded};const s=JSON.stringify(p);if(s!==last){last=s;document.querySelector('#metrics').textContent=s;fetch('/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:s}).catch(()=>{})}}setInterval(report,100);report();</script>'''
                return self.reply(html.replace('__NAME__',name),'text/html')
            self.send_error(404)
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            if self.path=='/telemetry':
                if data.get('name') in ('A','B','C'):
                    pages[data['name']]={**data,'received':time.time()}
                return self.reply({'ok':True})
            if self.path=='/command' and self.headers.get('X-QA-Token')==token:
                queue.put(data);return self.reply({'queued':True})
            self.send_error(403)

    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.daemon_threads=True
    Thread(target=server.serve_forever,daemon=True).start()
    file.write_text(json.dumps({'port':server.server_port,'token':token,'pid':__import__('os').getpid()}),encoding='utf-8')
    def pump():
        nonlocal initial_hwnd
        runtime.pump()
        try: item=queue.get_nowait()
        except Empty: return
        action=item['action'];now=runtime.clock.now_ms()
        fg=runtime.foreground.snapshot()
        before=asdict(runtime.controller.state)
        if action=='quit': window.close();app.quit();return
        if action=='show_panel': window.show_mini_panel()
        elif action=='hide_panel':window.mini_panel.hide()
        elif action=='stop':runtime.controller.stop('QA explicit stop')
        elif action=='continue':runtime.controller.ack_confirmation()
        elif action=='block_camera':runtime.controller.block('CAMERA_UNAVAILABLE')
        else:
            if not fg.is_chrome or not any(p['visible']=='visible' and p['focused'] for p in pages.values()):
                actions.append({'action':action,'error':'QA_PAGE_NOT_FOCUSED'});return
            if initial_hwnd is None:initial_hwnd=fg.hwnd
            if fg.hwnd!=initial_hwnd:
                actions.append({'action':action,'error':'QA_WINDOW_CHANGED'});return
            if action=='neutral':runtime.controller.neutral(True)
            else:
                gesture=Gesture[action]
                event=GestureEvent(runtime.ids.next_id('qa'),gesture,('synthetic-qa-hand',),now,now,
                                   runtime.controller.state.context_version,runtime.controller.state.camera_epoch)
                runtime.controller.handle(event);runtime.controller.flush_executor()
        actions.append({'action':action,'before_context':before['context_version'],'at':now,'foreground_hwnd':fg.hwnd})
        outcomes.append({'action':action,'state':asdict(runtime.controller.state),'foreground_after':runtime.foreground.snapshot().hwnd})
    timer=QTimer();timer.timeout.connect(pump);timer.start(20)
    result=app.exec()
    server.shutdown();server.server_close()
    (ROOT/'docs/validation'/f'{args.label}.json').write_text(json.dumps({'actions':actions,'outcomes':outcomes,'pages':pages,
        'shutdown_ok':window.shutdown_ok,'exit_code':result,'source':'synthetic gestures -> production Controller/KeyboardWorker/Win32; real Chrome pages'},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    return result if window.shutdown_ok else 2


if __name__=='__main__':raise SystemExit(main())
