"""Local browser-history observer for real hand trials; never injects OS input.

This dev-only page creates three known back steps and records its own popstate
events. It has no command endpoint and does not read other browsing history.
"""
import argparse
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
from pathlib import Path
import secrets


PAGE='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>HAND 뒤로가기 확인</title>
<style>body{margin:0;background:#f5f7fa;color:#17342f;font:20px "Malgun Gothic",sans-serif}main{max-width:760px;margin:60px auto;padding:36px;background:white;border:1px solid #dce5ec;border-radius:18px}h1{font-size:30px}#step{font-size:100px;font-weight:bold;color:#087f76;margin:22px 0}p{line-height:1.7}.muted{font-size:16px;color:#526579}</style>
<main><h1>HAND 뒤로가기 확인</h1><p>손을 펼쳐 상태창의 <b>동작 가능</b>을 확인한 뒤, 검지를 왼쪽으로 쓸어주세요.<br>한 번마다 손을 펼쳐 다시 준비합니다.</p><div id="step"></div><p id="message"></p><p class="muted">3 → 2 → 1 → 0으로 바뀌면 세 번 모두 뒤로간 것입니다.<br>이 페이지 자체의 이동만 기록합니다.</p></main>
<script>
const run='__RUN__';
function display(event){
  const step=history.state?.step;
  document.querySelector('#step').textContent=step;
  document.title='HAND 확인 · 단계 '+step;
  document.querySelector('#message').textContent=step===0?'세 단계 뒤로가기를 완료했습니다.':'남은 뒤로가기: '+step+'회';
  fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run,step,event})}).catch(()=>{});
}
if(history.state?.run!==run){
  history.replaceState({run,step:0},'', '#0');
  for(let step=1;step<=3;step++)history.pushState({run,step},'', '#'+step);
}
window.addEventListener('popstate',()=>display('popstate'));
display('load');
</script></html>'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run=secrets.token_hex(12)
    state={'source':'REAL_BROWSER_HISTORY_OBSERVER_NO_INPUT_INJECTION','url':None,'run':run,'events':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,body,content='application/json'):
            payload=body.encode('utf-8') if isinstance(body,str) else json.dumps(body).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type',content+'; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        def do_GET(self):
            if self.path=='/':return self.reply(PAGE.replace('__RUN__',run),'text/html')
            if self.path=='/status':return self.reply(state)
            self.send_error(404)
        def do_POST(self):
            length=int(self.headers.get('Content-Length','0'))
            if self.path!='/report' or not 0<length<=4096:return self.send_error(400)
            try:data=json.loads(self.rfile.read(length))
            except (ValueError,UnicodeDecodeError):return self.send_error(400)
            if data.get('run')!=run or type(data.get('step')) is not int or not 0<=data['step']<=3 or data.get('event') not in ('load','popstate'):return self.send_error(400)
            state['events'].append({'at_utc':datetime.now(timezone.utc).isoformat(),'step':data['step'],'event':data['event']})
            del state['events'][:-100]
            save();return self.reply({'ok':True})
    server=HTTPServer(('127.0.0.1',0),Handler)
    state['url']=f'http://127.0.0.1:{server.server_port}/';save()
    print(state['url'],flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':main()
