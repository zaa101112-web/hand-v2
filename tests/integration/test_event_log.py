import json
from hand_v2.adapters.event_log import JsonlEvents


def test_log_rotates_and_never_serializes_unknown_private_fields(tmp_path):
    log=JsonlEvents(tmp_path,max_bytes=700,max_files=3)
    for i in range(70):
        log.record('command',command_id=f'c-{i}',context=1,status='SENT',reason='OS_INPUT_SENT',
                   url='https://private.example',image=b'private',raw_typing='password',input_ms=12)
    assert log.close()
    files=list(tmp_path.glob('events.jsonl*'))
    assert 1<=len(files)<=3
    combined=''.join(p.read_text(encoding='utf-8') for p in files)
    assert 'private' not in combined and 'password' not in combined
    records=[json.loads(line) for line in combined.splitlines()]
    assert records and all(r['input_ms']==12 for r in records)


def test_log_io_failure_does_not_raise_into_control_pipeline(tmp_path):
    path=tmp_path/'file';path.write_text('occupied')
    log=JsonlEvents(path)
    log.record('stop',reason='BUTTON')
    log.close()
    assert log.error
