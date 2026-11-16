import hashlib
import json
from pathlib import Path
import sys

EXPECTED_MODEL_SHA256='fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'


def resource_root():
    return Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[3]


def verify_bundle(root=None):
    root=Path(root) if root else resource_root()
    model=root/'models/hand_landmarker.task'
    digest=hashlib.sha256(model.read_bytes()).hexdigest()
    if digest!=EXPECTED_MODEL_SHA256:
        raise ValueError('Bundled model hash does not match the pinned artifact')
    defaults=root/'config/defaults.json'
    config=json.loads(defaults.read_text(encoding='utf-8'))
    if config.get('schema_name')!='hand-v2-config' or type(config.get('version')) is not int or config['version']!=1:
        raise ValueError('Unsupported bundled defaults')
    return {'model_sha256':digest,'defaults_sha256':hashlib.sha256(defaults.read_bytes()).hexdigest(),
            'defaults_schema':config['schema_name'],'frozen':bool(getattr(sys,'frozen',False))}
