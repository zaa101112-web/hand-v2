import json
from pathlib import Path
import pytest

from hand_v2.adapters.resources import verify_bundle


def test_actual_assets_have_fixed_model_and_defaults_contract():
    result=verify_bundle(Path(__file__).parents[2])
    assert result['model_sha256']=='fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'
    assert result['defaults_schema']=='hand-v2-config'


def test_missing_or_wrong_model_fails_even_with_valid_config(tmp_path):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/defaults.json').write_text(json.dumps({'schema_name':'hand-v2-config','version':1}))
    with pytest.raises(FileNotFoundError):verify_bundle(tmp_path)
    (tmp_path/'models').mkdir()
    (tmp_path/'models/hand_landmarker.task').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='model hash'):verify_bundle(tmp_path)
