from datetime import datetime,timezone
import json,logging,math,re
from logging.handlers import RotatingFileHandler
from queue import Queue,Empty,Full
from threading import Thread


class JsonlEvents:
    FIELDS={'command_id','event_id','frame_id','context','epoch','status','reason','action','gesture','target',
            'input_ms','capture_to_result_ms','release_ms','frame_age_ms','inference_ms','fps','at_ms','revision','owned_count','dropped'}
    LEVELS={'DEBUG':10,'INFO':20,'WARNING':30,'ERROR':40}
    def __init__(self,folder,max_bytes=5*1024*1024,max_files=3,level='INFO'):
        self.queue=Queue(maxsize=2048);self.error='';self.dropped=0;self.closed=False;self.level=level
        self.folder=folder;self.max_bytes=max_bytes;self.max_files=max_files
        self.thread=Thread(target=self._run,name='HAND-event-log',daemon=True);self.thread.start()
    def record(self,kind,level='INFO',**fields):
        if self.closed or self.LEVELS.get(level,20)<self.LEVELS.get(self.level,20):return
        row={'kind':kind if kind in ('command','gesture','stop','release','camera','state','shutdown','capture') else 'event',
             'utc':datetime.now(timezone.utc).isoformat(),'level':level}
        for key,value in fields.items():
            if key not in self.FIELDS:continue
            if type(value) in (bool,int) or (type(value) is float and math.isfinite(value)):row[key]=value
            elif isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',value):row[key]=str(value)
        try:self.queue.put_nowait(row)
        except Full:self.dropped+=1
    def _run(self):
        handler=None
        try:
            from pathlib import Path
            folder=Path(self.folder);folder.mkdir(parents=True,exist_ok=True)
            handler=RotatingFileHandler(folder/'events.jsonl',maxBytes=self.max_bytes,backupCount=self.max_files-1,encoding='utf-8')
            # Route errors to our diagnostic instead of logging's process-global stderr handler.
            handler.handleError=lambda record:self._error('LOG_WRITE_FAILED')
            while not self.closed or not self.queue.empty():
                try:row=self.queue.get(timeout=.05)
                except Empty:continue
                message=json.dumps(row,ensure_ascii=False,allow_nan=False,separators=(',',':'))
                handler.emit(logging.LogRecord('HAND',logging.INFO,'',0,message,(),None))
        except Exception as exc:self.error=type(exc).__name__
        finally:
            if handler:handler.close()
    def _error(self,error):self.error=error
    def close(self):
        self.closed=True;self.thread.join(timeout=1)
        return not self.thread.is_alive()
