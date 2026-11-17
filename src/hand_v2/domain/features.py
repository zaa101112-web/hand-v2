from dataclasses import dataclass
from enum import StrEnum
import math


class FingerState(StrEnum):
    EXTENDED='EXTENDED'
    FOLDED='FOLDED'
    UNKNOWN='UNKNOWN'


def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def angle(a,b,c):
    u=tuple(x-y for x,y in zip(a,b));v=tuple(x-y for x,y in zip(c,b))
    norms=math.sqrt(sum(x*x for x in u)*sum(x*x for x in v))
    if norms<1e-9:return None
    return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/norms))))


class TimeEMA:
    def __init__(self,tau_ms=60):self.tau_ms=tau_ms;self.reset()
    def reset(self):self.value=None;self.at=None
    def update(self,value,at):
        if self.value is None or at<=self.at:self.value=tuple(value)
        else:
            alpha=1-math.exp(-(at-self.at)/self.tau_ms)
            self.value=tuple(a+(b-a)*alpha for a,b in zip(self.value,value))
        self.at=at
        return self.value


@dataclass(frozen=True,slots=True)
class HandFeatures:
    hand_id: str
    fingers: tuple[FingerState,...]
    pose: str
    palm_size: float
    pointer: tuple[float,float]
    center: tuple[float,float]
    pinch_ratio: float


def describe_hand(hand,width,height):
    p=tuple((lm.x*width,lm.y*height,lm.z*width) for lm in hand.landmarks)
    # Palm scale is measured in the image plane, matching the visible 20px gate.
    size=distance(p[5][:2],p[17][:2])
    fingers=[]
    if size<20:
        fingers=[FingerState.UNKNOWN]*5
    else:
        mcp,ip=angle(p[1],p[2],p[3]),angle(p[2],p[3],p[4])
        thumb_gap=distance(p[4],p[5])/size
        if mcp is not None and ip is not None and mcp>=150 and ip>=150 and thumb_gap>=.6:
            fingers.append(FingerState.EXTENDED)
        elif mcp is not None and ip is not None and (mcp<=130 or ip<=130 or thumb_gap<=.4):fingers.append(FingerState.FOLDED)
        else:fingers.append(FingerState.UNKNOWN)
        for base in (5,9,13,17):
            pip=angle(p[base],p[base+1],p[base+2]);dip=angle(p[base+1],p[base+2],p[base+3])
            if pip is not None and dip is not None and pip>=160 and dip>=160:fingers.append(FingerState.EXTENDED)
            elif pip is not None and pip<=120:fingers.append(FingerState.FOLDED)
            else:fingers.append(FingerState.UNKNOWN)
    patterns={(False,True,True,False,False):'V',(True,True,True,False,False):'THREE',
              (False,True,False,False,False):'INDEX',(True,True,True,True,True):'OPEN',
              (False,False,False,False,False):'FIST',(True,False,False,False,False):'THUMB',
              (True,True,False,False,False):'L'}
    pose='UNKNOWN' if FingerState.UNKNOWN in fingers else patterns.get(tuple(f==FingerState.EXTENDED for f in fingers),'OTHER')
    # A one-finger pointing pose does not require squeezing the thumb shut.
    # The three remaining fingers must still be unambiguously folded. Keep
    # V/THREE/L and their safety/priority rules on the original strict classifier.
    if (pose=='UNKNOWN' and size>=20 and fingers[0]==FingerState.UNKNOWN
            and fingers[1:]==[FingerState.EXTENDED,FingerState.FOLDED,FingerState.FOLDED,FingerState.FOLDED]
            and mcp is not None and ip is not None and min(mcp,ip)<=145+1e-9):
        pose='INDEX'
    pointer=(1-hand.landmarks[8].x,hand.landmarks[8].y)
    center=(sum(1-hand.landmarks[i].x for i in (0,5,9,13,17))/5,sum(hand.landmarks[i].y for i in (0,5,9,13,17))/5)
    return HandFeatures(hand.hand_id,tuple(fingers),pose,size,pointer,center,distance(p[4],p[8])/max(size,1e-9))
