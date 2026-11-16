from pathlib import Path
from hand_v2.adapters.replay import run_fixture


def test_landmark_pipeline_is_repeatable_and_never_constructs_real_adapters(monkeypatch):
    import hand_v2.adapters.windows.native as native
    def forbidden(*args,**kwargs):raise AssertionError('Replay cannot construct Win32')
    monkeypatch.setattr(native,'Win32',forbidden)
    fixture=Path(__file__).parents[1]/'fixtures/landmarks/start_back_stop'
    results=[run_fixture(fixture) for _ in range(10)]
    assert all(r==results[0] for r in results)
    assert results[0]['sent_chords']==[['ALT','LEFT']]
    assert results[0]['activation']=='WAITING'
