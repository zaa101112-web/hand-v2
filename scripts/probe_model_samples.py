"""Real model check using official MediaPipe sample photos, not live-user accuracy."""
from pathlib import Path
import hashlib,json,sys
from dataclasses import asdict

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import cv2
import numpy as np
import mediapipe as mp
from hand_v2.domain.features import describe_hand,angle,distance
from hand_v2.domain.models import Hand,Landmark
from hand_v2.adapters.resources import resource_root,EXPECTED_MODEL_SHA256

reports=[]
for name in ('victory','pointing_up','thumb_up','right_hands','fist'):
    path=root/'.build-staging/model-samples'/f'{name}.jpg'
    raw=cv2.imdecode(np.frombuffer(path.read_bytes(),dtype=np.uint8),cv2.IMREAD_COLOR)
    rgb=cv2.cvtColor(raw,cv2.COLOR_BGR2RGB);h,w=rgb.shape[:2]
    options=mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_buffer=(resource_root()/'models/hand_landmarker.task').read_bytes()),running_mode=mp.tasks.vision.RunningMode.VIDEO,num_hands=2)
    with mp.tasks.vision.HandLandmarker.create_from_options(options) as model:
        result=model.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb),1000)
    hands=[]
    for i,points in enumerate(result.hand_landmarks):
        raw_label=result.handedness[i][0].category_name.upper()
        hand=Hand(f'sample-{i}',raw_label,tuple(Landmark(p.x,p.y,p.z) for p in points))
        feature=describe_hand(hand,w,h)
        hands.append({'hand':asdict(hand),'features':asdict(feature)})
    reports.append({'sample':name,'source':f'https://storage.googleapis.com/mediapipe-assets/{name}.jpg','image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':[w,h],'hands':hands})
    print(name,[x['features']['pose'] for x in hands])
(root/'docs/validation/m03-model-samples.json').write_text(json.dumps({'model_sha256':EXPECTED_MODEL_SHA256,'source':'official static photos processed by actual VIDEO model; not webcam gesture accuracy','samples':reports},indent=2),encoding='utf-8')
