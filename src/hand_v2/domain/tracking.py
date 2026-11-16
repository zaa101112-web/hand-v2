from dataclasses import replace
import math
from .features import distance


class HandIdentityTracker:
    """Geometric association; ambiguous crossings receive new IDs, never old history."""
    def __init__(self,prefix='hand'):
        self.prefix=prefix;self.next_id=0;self.previous={}

    def _new_id(self):
        self.next_id+=1
        return f'{self.prefix}-{self.next_id}'

    def update(self,hands,width,height):
        diag=math.hypot(width,height)
        centers=[(sum(h.landmarks[i].x for i in (0,5,9,13,17))*width/5,
                  sum(h.landmarks[i].y for i in (0,5,9,13,17))*height/5) for h in hands]
        previous=list(self.previous.items())
        ambiguous=len(centers)==2 and distance(centers[0],centers[1])<diag*.06
        assignments={};used=set()
        candidates=sorted((distance(center,old)/diag,i,key) for i,center in enumerate(centers) for key,old in previous)
        if not ambiguous:
            if len(centers)==2 and len(previous)==2:
                direct=sum(distance(centers[i],previous[i][1]) for i in (0,1))
                crossed=sum(distance(centers[i],previous[1-i][1]) for i in (0,1))
                ambiguous=abs(direct-crossed)<diag*.03
            if not ambiguous:
                for cost,i,key in candidates:
                    if cost<=.2 and i not in assignments and key not in used:
                        assignments[i]=key;used.add(key)
        output=[];self.previous={}
        for i,hand in enumerate(hands):
            key=assignments.get(i) or self._new_id()
            self.previous[key]=centers[i]
            output.append(replace(hand,hand_id=key))
        return tuple(output)
