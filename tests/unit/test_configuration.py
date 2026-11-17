"""REQ-06/07 V2-T28: strict, transactional settings."""
from copy import deepcopy
import json
import pytest
from hand_v2.domain.configuration import validate_config, merge_leaves
from hand_v2.adapters.configuration import ConfigStore, read_defaults


@pytest.mark.parametrize('patch', [
    {'unknown':1},{'version':True},{'version':2},{'camera':{'index':False}},
    {'camera':{'index':-1}},{'camera':None},{'gestures':{'swipe_distance':float('nan')}},
    {'gestures':{'swipe_distance':.26}},{'timing':{'stop_ms':500}},
    {'gestures':{'pinch_enter':.5}},{'display':{'preview':1}}, {'capture':{'folder':3}},
    {'logging':{'level':'SECRET'}},
])
def test_invalid_user_leaf_is_rejected(patch):
    with pytest.raises(ValueError):validate_config(merge_leaves(read_defaults(),patch))


def test_merge_retains_defaults_replaces_arrays_and_checks_relations():
    assert merge_leaves({'a':{'b':1,'c':2},'d':[1,2]},{'a':{'b':3},'d':[4]})=={'a':{'b':3,'c':2},'d':[4]}
    result=validate_config(merge_leaves(read_defaults(),{'camera':{'index':1},'capture':{'folder':None}}))
    assert result['camera']['width']==640 and result['camera']['index']==1


def test_save_failure_keeps_memory_disk_and_corrupt_user_is_preserved(tmp_path,monkeypatch):
    path=tmp_path/'user.json';store=ConfigStore(read_defaults(),path)
    assert not store.load().error
    store.save({'camera':{'index':1}});original=path.read_bytes();memory=deepcopy(store.current)
    import hand_v2.adapters.configuration as module
    def fail(*args):raise PermissionError('test permission denied')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(PermissionError):store.save({'camera':{'index':2}})
    assert path.read_bytes()==original and store.current==memory
    assert not list(tmp_path.glob('*.tmp'))
    path.write_text('{broken',encoding='utf-8')
    loaded=store.load()
    assert loaded.error and path.read_text(encoding='utf-8')=='{broken'
    assert loaded.config==read_defaults()


def test_duplicate_json_keys_are_not_silently_accepted(tmp_path):
    path=tmp_path/'user.json';path.write_text('{"version":1,"version":2}')
    assert ConfigStore(read_defaults(),path).load().error
