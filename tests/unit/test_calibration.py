"""V2-T38: recommendations require evidence and never apply themselves."""
import pytest
from hand_v2.domain.calibration import recommend_swipe,Calibration


def test_recommendation_requires_five_seconds_and_ten_each_direction():
    with pytest.raises(ValueError):recommend_swipe(4999,.002,[.2]*10,[.2]*10)
    with pytest.raises(ValueError):recommend_swipe(5000,.002,[.2]*9,[.2]*10)
    with pytest.raises(ValueError):recommend_swipe(5000,.08,[.2]*10,[.2]*10)
    with pytest.raises(ValueError):recommend_swipe(5000,.002,[.15]*10,[.4]*10)
    value=recommend_swipe(5000,.002,[.2]*10,[.22]*10)
    assert .10<=value<=.25 and value<.2


def test_calibration_does_not_count_curved_or_wrong_direction_samples():
    c=Calibration();c.start()
    for at in range(0,5050,50):c.sample(at,'h','INDEX',(.5,.5))
    assert c.phase=='LEFT'
    c.sample(5100,'h','OPEN',(.5,.5))
    for at,x in [(5200,.5),(5300,.6),(5400,.7)]:c.sample(at,'h','INDEX',(x,.5))
    c.sample(5450,'h','OPEN',(.7,.5))
    assert not c.left
    for n in range(10):
        base=5500+n*400
        for delta,x in [(0,.6),(50,.55),(100,.5),(150,.45),(200,.4)]:c.sample(base+delta,'h','INDEX',(x,.5))
        c.sample(base+250,'h','OPEN',(.4,.5))
    assert c.phase=='RIGHT' and len(c.left)==10
    for n in range(10):
        base=10000+n*400
        for delta,x in [(0,.4),(50,.45),(100,.5),(150,.55),(200,.6)]:c.sample(base+delta,'h','INDEX',(x,.5))
        c.sample(base+250,'h','OPEN',(.6,.5))
    assert c.phase=='READY' and .10<=c.recommendation<=.25


def test_hand_identity_or_long_gap_cannot_extend_stationary_evidence():
    c=Calibration();c.start()
    c.sample(0,'a','INDEX',(.5,.5));c.sample(4999,'a','INDEX',(.5,.5));c.sample(5000,'b','INDEX',(.5,.5))
    assert c.phase=='STILL' and c.still_ms==0
