"""REQ-04/05, V2-T22..27: observable image/capture contracts."""
import pytest
from hand_v2.domain.images import Gallery, ImageAsset
from hand_v2.domain.capture import Rect, Display, CaptureSession


def test_gallery_preserves_slide_zoom_clamps_and_retains_on_empty_load():
    g = Gallery()
    g.replace([ImageAsset('a', 100, 60, b''), ImageAsset('b', 50, 80, b'')])
    g.zoom(1.15)
    g.move(1)
    assert g.current.key == 'b' and g.scale == 1 and g.direction == 1
    g.move(1)
    assert g.index == 1 and g.direction == 0
    g.move(-1)
    assert g.scale == 1.15 and g.direction == -1
    for _ in range(50): g.zoom(1.15)
    assert g.scale == 4
    for _ in range(100): g.zoom(1/1.15)
    assert g.scale == .25
    g.fit()
    g.replace([])
    assert g.current.key == 'a' and g.scale == 1


@pytest.mark.parametrize('scale', [1, 1.25, 1.5])
def test_physical_exclusive_rect_rounds_out_and_clamps(scale):
    d = Display('screen', 100, -200, 1920, 1080, scale)
    assert d.physical(0, 0, 1920/scale, 1080/scale) == Rect(0,0,1920,1080)
    r = d.physical(1.1, 2.1, 41.1, 42.1)
    import math
    assert r == Rect(math.floor(1.1*scale), math.floor(2.1*scale), math.ceil(41.1*scale), math.ceil(42.1*scale))
    assert d.physical(-10,-10,3000,3000) == Rect(0,0,1920,1080)


def session():
    return CaptureSession('s1', 4, 'IMAGE', Display('screen',0,0,1000,800,1))


def test_capture_requires_valid_selection_and_matching_hide_ack():
    s = session()
    assert s.rect == Rect(250,200,750,600)
    s.select(Rect(1,1,32,33))
    assert not s.confirm('c1', 0)
    s.select(Rect(1,1,33,33))
    assert s.confirm('c2', 0)
    assert not s.confirm('duplicate', 1)
    assert not s.ack_hidden('s1','c2',3,10)
    assert not s.ack_hidden('old','c2',4,10)
    assert s.ack_hidden('s1','c2',4,10)
    assert not s.can_start(109)
    assert s.can_start(110)
    assert s.start(110)
    assert not s.start(111)


def test_capture_timeout_retry_cancel_and_late_success_are_truthful():
    s = session()
    s.confirm('c1',0)
    assert s.tick(1000) == 'HIDE_TIMEOUT'
    assert s.phase == 'ERROR'
    assert s.confirm('c2',1001)
    s.ack_hidden('s1','c2',4,1002)
    s.start(1102)
    assert s.tick(6102) == 'SLOW'
    assert s.tick(11102) == 'CAPTURE_STALLED'
    assert s.closed and s.worker_running
    assert not s.confirm('c3',11103)
    assert not s.finish('old','c2',path='wrong.png')
    assert s.finish('s1','c2',path='saved.png')
    assert s.path == 'saved.png' and s.closed and not s.worker_running


def test_cancel_before_worker_prevents_save_and_selection_keyboard_bounds():
    s = session()
    s.adjust(-1000,0)
    assert s.rect.left == 0 and s.rect.width == 500
    s.adjust(0,-1000,resize=True)
    assert not s.rect.valid
    s.fullscreen()
    assert s.rect == Rect(0,0,1000,800)
    s.confirm('c1',0); s.cancel()
    assert not s.ack_hidden('s1','c1',4,0)
    assert not s.start(100)
