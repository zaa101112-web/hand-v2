"""Author deterministic geometry inputs, never derive expected events from the recognizer."""
from dataclasses import asdict
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tests.hand_samples import sample_frame,sample_hand
from tests.unit.test_extended_recognition import frame,shifted,zoom_frame,circle_frames,l_frame
from hand_v2.adapters.resources import EXPECTED_MODEL_SHA256

cases=[]
def add(name,expected,frames,active=True):
    cases.append({'name':name,'expected':expected,'active':active,'frames':[asdict(f) for f in frames]})

add('start',['G01'],[sample_frame(1000+t,'V') for t in range(0,701,50)],False)
add('stop',['G02'],[sample_frame(1000+t,'THREE') for t in range(0,451,50)])
for dx,code in ((.24,'G03'),(-.24,'G04')):
    add(code,[code],[sample_frame(1000+t,'INDEX',dx*t/500) for t in range(0,501,50)])
for dx,dy,code in ((.24,0,'G05'),(-.24,0,'G06'),(0,-.24,'G07'),(0,.24,'G08')):
    add(code,[code],[frame(1000+t,shifted(sample_hand('V'),dx*t/500,dy*t/500)) for t in range(0,501,50)])
for sep,code in ((.70,'G09'),(.38,'G10')):
    add(code,[code],[zoom_frame(1000+t) for t in range(0,201,20)]+[zoom_frame(1000+t,sep) for t in range(220,701,20)])
add('circle',['G11'],list(circle_frames()))
add('thumb',['G12'],[sample_frame(1000+t,'THUMB') for t in range(0,701,50)])
add('fist-open',['G13'],[sample_frame(1000+t,'FIST') for t in range(0,301,50)]+[sample_frame(1000+t,'OPEN') for t in range(350,601,50)])
add('frame',['G14'],[l_frame(1000+t) for t in range(0,901,50)])
add('diagonal',[],[frame(1000+t,shifted(sample_hand('V'),.24*t/600,.24*t/600)) for t in range(0,601,50)])
add('open-circle',[],list(circle_frames(angle=250)))
add('two-v',[],[l_frame(1000+t,'V') for t in range(0,901,50)])
add('short-v',[],[sample_frame(1000+t,'V') for t in range(0,551,50)],False)
report={'kind':'RECOGNITION_LANDMARKS','source':'manually authored geometry, not camera accuracy or OS effects',
        'source_commit':'38a7d8a','model_sha256':EXPECTED_MODEL_SHA256,
        'config_sha256':hashlib.sha256((ROOT/'config/defaults.json').read_bytes()).hexdigest(),'cases':cases}
(ROOT/'tests/fixtures/gesture_suite.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
