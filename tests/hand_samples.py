"""Hand-authored geometry fixtures, not camera/model accuracy evidence."""
from hand_v2.domain.models import Hand,Landmark,TrackingFrame


def sample_hand(pose='V',hand_id='h1',offset=0.0,scale=1.0):
    points=[(.5,.8)]*21
    points[1:5]=[(.38,.72),(.33,.66),(.40,.66),(.45,.65)]
    patterns={'V':(False,True,True,False,False),'THREE':(True,True,True,False,False),
              'INDEX':(False,True,False,False,False),'OPEN':(True,True,True,True,True),
              'FIST':(False,False,False,False,False),'THUMB':(True,False,False,False,False),
              'L':(True,True,False,False,False)}
    extended=patterns[pose]
    if extended[0]:points[1:5]=[(.38,.72),(.33,.66),(.27,.60),(.21,.54)]
    for flag,(base,x,y) in zip(extended[1:],[(5,.42,.60),(9,.50,.58),(13,.58,.60),(17,.66,.63)]):
        points[base]=(x,y)
        points[base+1]=(x,y-.13)
        points[base+2]=(x,y-.23) if flag else (x+.03,y-.03)
        points[base+3]=(x,y-.32) if flag else (x+.02,y+.04)
    return Hand(hand_id,'RIGHT',tuple(Landmark((x-.5)*scale+.5+offset,(y-.5)*scale+.5) for x,y in points))


def sample_frame(at=1000,pose='V',offset=0.0,epoch=1,hand_id='h1'):
    return TrackingFrame(at,at,epoch,640,480,(sample_hand(pose,hand_id,offset),))
