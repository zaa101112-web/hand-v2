"""Real model landmarks from public MediaPipe assets, without using the camera."""
import json
from pathlib import Path

import pytest

from hand_v2.domain.features import describe_hand
from hand_v2.domain.models import Hand, Landmark


@pytest.mark.parametrize('sample,poses',[
    ('victory',['V']),('pointing_up',['INDEX']),('thumb_up',['THUMB']),
    ('right_hands',['OPEN','OPEN']),('fist',['FIST'])])
def test_real_model_poses_include_thumb_folded_at_mcp(sample,poses):
    report=json.loads((Path(__file__).parents[1]/'fixtures/model_poses.json').read_text(encoding='utf-8'))
    row=next(item for item in report['samples'] if item['sample']==sample)
    found=[]
    for record in row['hands']:
        data=dict(record['hand'])
        data['landmarks']=tuple(Landmark(**lm) for lm in data['landmarks'])
        found.append(describe_hand(Hand(**data),*row['size']).pose)
    assert found==poses
