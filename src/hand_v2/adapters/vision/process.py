from dataclasses import dataclass
import multiprocessing as mp
from queue import Empty,Full
import time

from hand_v2.domain.models import TrackingFrame,Hand,Landmark


@dataclass(frozen=True,slots=True)
class VisionPacket:
    frame: TrackingFrame
    preview_rgb: bytes | None = None
    inference_ms: float = 0.0


def put_latest(queue,item):
    try:queue.put_nowait(item)
    except Full:
        try:queue.get_nowait()
        except Empty:pass
        try:queue.put_nowait(item)
        except Full:pass


def camera_child(epoch,index,preview_enabled,stop,frames,status,heartbeat):
    capture=None;landmarker=None
    frames.cancel_join_thread();status.cancel_join_thread()
    try:
        import cv2
        import mediapipe as mp_api
        from hand_v2.adapters.resources import resource_root,verify_bundle
        from hand_v2.domain.tracking import HandIdentityTracker
        verify_bundle()
        model=(resource_root()/'models/hand_landmarker.task').read_bytes()
        options=mp_api.tasks.vision.HandLandmarkerOptions(
            base_options=mp_api.tasks.BaseOptions(model_asset_buffer=model),
            running_mode=mp_api.tasks.vision.RunningMode.VIDEO,num_hands=2,
            min_hand_detection_confidence=.5,min_hand_presence_confidence=.5,min_tracking_confidence=.5)
        landmarker=mp_api.tasks.vision.HandLandmarker.create_from_options(options)
        capture=cv2.VideoCapture(index,cv2.CAP_DSHOW)
        if not capture.isOpened():raise RuntimeError('CAMERA_OPEN_FAILED')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH,640);capture.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        capture.set(cv2.CAP_PROP_FPS,30)
        tracker=HandIdentityTracker(prefix=f'e{epoch}')
        frame_id=0;previous=-1;last_preview=-1000;ready=False
        while not stop.is_set():
            ok,bgr=capture.read()
            captured=time.monotonic_ns()//1_000_000
            if not ok or bgr is None:raise RuntimeError('CAMERA_READ_FAILED')
            if captured<=previous:continue
            previous=captured
            rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
            start=time.monotonic_ns()
            result=landmarker.detect_for_video(mp_api.Image(image_format=mp_api.ImageFormat.SRGB,data=rgb),captured)
            duration=(time.monotonic_ns()-start)/1_000_000
            height,width=rgb.shape[:2]
            hands=[]
            for i,points in enumerate(result.hand_landmarks):
                category=result.handedness[i][0]
                raw=category.category_name.upper()
                hands.append(Hand(f'raw-{i}',raw,tuple(Landmark(p.x,p.y,p.z) for p in points),raw,category.score))
            tracked=tracker.update(tuple(hands),width,height)
            frame_id+=1
            frame=TrackingFrame(frame_id,captured,epoch,width,height,tracked)
            preview=None
            if preview_enabled.is_set() and captured-last_preview>=100:
                preview=rgb.tobytes();last_preview=captured
            heartbeat.value=time.monotonic_ns()//1_000_000
            if not ready:
                status.put_nowait(('ready',None));ready=True
            put_latest(frames,VisionPacket(frame,preview,duration))
    except Exception as error:
        reason=str(error) if str(error).startswith('CAMERA_') else 'VISION_ERROR:'+type(error).__name__
        try:status.put_nowait(('error',reason))
        except Full:pass
    finally:
        if capture is not None:capture.release()
        if landmarker is not None:landmarker.close()


class SpawnSession:
    def __init__(self,epoch,index,preview,child_target=camera_child):
        ctx=mp.get_context('spawn')
        self.frames=ctx.Queue(maxsize=1);self.status=ctx.Queue(maxsize=8)
        self.stop_event=ctx.Event();self.preview=ctx.Event()
        if preview:self.preview.set()
        self.heartbeat=ctx.Value('q',time.monotonic_ns()//1_000_000,lock=False)
        self.process=ctx.Process(target=child_target,args=(epoch,index,self.preview,self.stop_event,self.frames,self.status,self.heartbeat),name='HAND-camera',daemon=True)
        self.process.start()

    @property
    def last_heartbeat_ms(self):return self.heartbeat.value
    def is_alive(self):return self.process.is_alive()
    def request_stop(self):self.stop_event.set()
    def terminate(self):self.process.terminate()
    def kill(self):self.process.kill()
    def set_preview(self,value):self.preview.set() if value else self.preview.clear()
    def drain(self):
        events=[]
        for queue,kind in ((self.status,None),(self.frames,'frame')):
            while True:
                try:item=queue.get_nowait()
                except Empty:break
                events.append((kind,item) if kind else item)
        return events
    def close(self):
        self.process.join(timeout=0)
        self.process.close()
        for queue in (self.frames,self.status):
            queue.cancel_join_thread();queue.close()
