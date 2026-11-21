from dataclasses import replace

from hand_v2.domain.mapping import action_for, chord_for, target_for
from hand_v2.domain.models import (Action, Activation, AppState, Command, ExecutionMode,
                                   Gesture, Mode, Result, Status)
from hand_v2.domain.queue import CommandQueue
from .ports import Clock, ForegroundPort, IdSource, KeyboardPort, TimerPort, UiPort,EventSink


class Controller:
    """Single writer of application state. All external effects are injected."""
    def __init__(self, clock: Clock, scheduler: TimerPort, ids: IdSource,
                 keyboard: KeyboardPort, foreground: ForegroundPort, ui: UiPort,
                 execution_mode=ExecutionMode.SIMULATED, app_actions=None,events=None):
        self.clock, self.scheduler, self.ids = clock, scheduler, ids
        self.keyboard, self.foreground, self.ui = keyboard, foreground, ui
        self.app_actions = app_actions
        self.events=events or EventSink()
        self._command_times={};self._release_at=None
        self.state = AppState(execution_mode=execution_mode)
        self.queue = CommandQueue()
        self._seen = {}
        self._executed = {}
        self._neutral_timer = None
        self._neutral_since = None
        self._cooldown_until = 0
        self._pending_release = None
        self._release_ok = False
        self._release_revision = 0
        self._target_identity = None
        self._candidate_at = None
        self._publish()

    def _publish(self):
        self.ui.render_state(self.state)

    def _set(self, **changes):
        self.state = replace(self.state, revision=self.state.revision+1, **changes)
        self._publish()

    def initialize(self, camera_ready=False):
        blocked = frozenset() if camera_ready else frozenset({"CAMERA_UNAVAILABLE"})
        self._set(phase="RUNNING", blocked_reasons=blocked, camera_status="CONNECTED" if camera_ready else "DISCONNECTED")
        self._target_identity = self.foreground.snapshot().identity
        self.request_release()

    def request_release(self):
        self._release_at=self.clock.now_ms()
        self._pending_release = self.ids.next_id("release")
        self._release_ok = False
        self._release_revision = self.state.keyboard_state.revision
        self._set(release_pending=True, ready=False)
        reply = self.keyboard.release_owned_keys(self._pending_release, self.state.context_version)
        if reply is not None:
            result, keyboard_state = reply
            self.on_keyboard_state(keyboard_state)
            self.on_release_result(result)

    def on_keyboard_state(self, keyboard_state):
        if keyboard_state.revision <= self.state.keyboard_state.revision:
            return
        self._set(keyboard_state=keyboard_state)
        self._check_release()

    def on_release_result(self, result):
        if result.request_id != self._pending_release:
            return
        self._release_ok = result.success
        if not result.success:
            self.events.record('release',level='ERROR',status='FAILED',reason='INPUT_RELEASE_FAILED',context=self.state.context_version)
            self._set(blocked_reasons=self.state.blocked_reasons | {"INPUT_RELEASE_FAILED"})
        self._check_release()

    def _check_release(self):
        state = self.state.keyboard_state
        if (self._pending_release and self._release_ok and state.revision > self._release_revision
                and state.release_request_id == self._pending_release
                and state.release_status == "CONFIRMED" and not state.owned_keys):
            self._pending_release = None
            self.events.record('release',release_ms=self.clock.now_ms()-self._release_at,owned_count=0,status='CONFIRMED',context=self.state.context_version)
            self._set(release_pending=False, blocked_reasons=self.state.blocked_reasons - {"INPUT_RELEASE_FAILED"})

    def activate(self):
        if (self.state.phase != "RUNNING" or self.state.blocked_reasons or self.state.release_pending
                or self.state.keyboard_state.owned_keys or self.state.dialog_lock or self.state.confirmation_pending):
            return False
        if self.state.activation == Activation.WAITING:
            self._reset_neutral()
            self._set(activation=Activation.ACTIVE, ready=False)
        return True

    def _reset_neutral(self):
        self.scheduler.cancel(self._neutral_timer)
        self._neutral_timer = None
        self._neutral_since = None

    def neutral(self, is_neutral):
        if not is_neutral:
            self._reset_neutral()
            return
        if self._neutral_since is None:
            self._neutral_since = self.clock.now_ms()
            self._neutral_timer = self.scheduler.call_at(self._neutral_since+180, self._try_ready)

    def _try_ready(self):
        self._neutral_timer = None
        if self._neutral_since is None:
            return
        deadline = max(self._neutral_since+180, self._cooldown_until)
        if self.clock.now_ms() < deadline:
            self._neutral_timer = self.scheduler.call_at(deadline, self._try_ready)
            return
        if (self.state.phase == "RUNNING" and self.state.activation == Activation.ACTIVE
                and not self.state.blocked_reasons and not self.state.release_pending
                and not self.state.confirmation_pending and not self.state.dialog_lock):
            self._set(ready=True)

    def _clear_queue(self, reason):
        for cmd in self.queue.clear():
            self._record(Result(cmd.command_id, cmd.context_version, self.clock.now_ms(), Status.CANCELLED, reason))

    def stop(self, reason="button"):
        self.events.record('stop',reason='STOP_REQUEST',context=self.state.context_version,at_ms=self.clock.now_ms())
        self._reset_neutral()
        self._set(activation=Activation.WAITING, ready=False, context_version=self.state.context_version+1,
                  last_stop_reason=reason, last_stop_at_ms=self.clock.now_ms())
        self._clear_queue("STOPPED")
        self.request_release()

    def block(self, reason):
        self._set(blocked_reasons=self.state.blocked_reasons | {reason})
        self.stop(reason)

    def recover(self, reason):
        self._set(blocked_reasons=self.state.blocked_reasons - {reason})

    def begin_camera(self,epoch):
        self._set(camera_epoch=epoch,camera_status='CONNECTING',
                  blocked_reasons=self.state.blocked_reasons | {'CAMERA_UNAVAILABLE'})
        self.stop('카메라 연결')

    def camera_connected(self,epoch):
        if epoch!=self.state.camera_epoch:return
        blocked=frozenset(reason for reason in self.state.blocked_reasons
                          if not reason.startswith(('CAMERA_','VISION_ERROR:')))
        self._set(camera_status='CONNECTED',blocked_reasons=blocked)

    def camera_failed(self,reason):
        self._set(camera_status='DISCONNECTED')
        if reason not in self.state.blocked_reasons:
            if reason!='CAMERA_OFF':
                self.events.record('camera',level='ERROR',reason=reason,epoch=self.state.camera_epoch,context=self.state.context_version)
            self._set(blocked_reasons=self.state.blocked_reasons | {'CAMERA_UNAVAILABLE',reason})
            self.stop(reason)

    def set_mode(self, mode):
        if self.state.mode == Mode.CAPTURE:
            return
        if mode == self.state.mode:
            return
        if mode not in (Mode.IMAGE, Mode.BROWSER):
            raise ValueError("capture mode requires a session")
        self._reset_neutral()
        self._set(mode=mode, ready=False, context_version=self.state.context_version+1)
        self._clear_queue("MODE_CHANGED")
        self.request_release()

    def enter_capture(self):
        self._reset_neutral()
        self._set(mode=Mode.CAPTURE, ready=False, context_version=self.state.context_version+1)
        self._clear_queue('CAPTURE_OPEN')
        self.request_release()

    def leave_capture(self, previous_mode):
        self._reset_neutral()
        self._set(mode=Mode(previous_mode), ready=False, context_version=self.state.context_version+1)
        self._clear_queue('CAPTURE_CLOSED')
        self.request_release()

    def hands_lost(self):
        self._reset_neutral()
        self._set(ready=False, visible_hand_ids=(), last_candidate="손 없음")

    def show_candidate(self, text, hands=()):
        self._candidate_at = self.clock.now_ms()
        self._set(last_candidate=text, visible_hand_ids=hands)

    def refresh_target(self):
        snapshot = self.foreground.snapshot()
        if snapshot.identity != self._target_identity:
            self._target_identity = snapshot.identity
            if self.state.mode == Mode.BROWSER:
                self._reset_neutral()
                self._set(ready=False)
        return snapshot

    def tick(self):
        self.refresh_target()
        if self._candidate_at is not None and self.clock.now_ms()-self._candidate_at > 250:
            self._candidate_at = None
            self.hands_lost()
        cutoff = self.clock.now_ms()-60_000
        self._seen = {k:v for k,v in self._seen.items() if v >= cutoff}
        self._executed = {k:v for k,v in self._executed.items() if v >= cutoff}

    def ack_confirmation(self):
        if self.state.confirmation_pending:
            self._reset_neutral()
            self._set(confirmation_pending=False, ready=False)

    def set_dialog_lock(self, locked):
        if locked==self.state.dialog_lock:return
        self._reset_neutral()
        self._set(dialog_lock=locked, ready=False,context_version=self.state.context_version+1)
        if locked:
            self._clear_queue("DIALOG_OPEN")
            self.request_release()

    def settings_changed(self):
        self._reset_neutral()
        self._set(ready=False,context_version=self.state.context_version+1)
        self._clear_queue('SETTINGS_CHANGED')
        self.request_release()

    def _record(self, result):
        times=self._command_times.pop(result.command_id,None)
        level='ERROR' if result.status==Status.FAILED else 'WARNING' if result.status==Status.BLOCKED else 'INFO'
        self.events.record('command',level=level,command_id=result.command_id,context=result.context_version,status=result.status,
                           reason=result.reason,at_ms=result.completed_at_ms,
                           **({'input_ms':result.completed_at_ms-times[0],'capture_to_result_ms':result.completed_at_ms-times[1]} if times else {}))
        self._set(last_execution=result)
        return result

    def _blocked(self, source_id, reason):
        return self._record(Result(source_id, self.state.context_version, self.clock.now_ms(), Status.BLOCKED, reason))

    def handle(self, event):
        now = self.clock.now_ms()
        if event.event_id in self._seen:
            return self._blocked(event.event_id, "DUPLICATE")
        self._seen[event.event_id] = now
        if event.context_version != self.state.context_version or event.camera_epoch != self.state.camera_epoch:
            return self._blocked(event.event_id, "STALE_CONTEXT")
        if not 0 <= now-event.captured_at_ms <= 250 or event.emitted_at_ms > now:
            return self._blocked(event.event_id, "STALE_EVENT")
        action = action_for(self.state.mode, event.gesture)
        if action == Action.STOP:
            self.stop("숫자 3")
            return None
        if action == Action.ACTIVATE:
            self.activate()
            return None
        if action is None:
            return self._blocked(event.event_id, "UNBOUND_GESTURE")
        if self.state.phase != "RUNNING" or self.state.activation != Activation.ACTIVE:
            return self._blocked(event.event_id, "WAITING")
        if self.state.blocked_reasons or self.state.release_pending or self.state.dialog_lock or self.state.confirmation_pending:
            return self._blocked(event.event_id, "INPUT_BLOCKED")
        target = target_for(self.state.mode, action)
        snapshot = self.refresh_target() if target == "CHROME" else None
        if snapshot is not None and not snapshot.is_chrome:
            self._reset_neutral()
            self._set(ready=False)
            return self._blocked(event.event_id, "TARGET_NOT_CHROME")
        if not self.state.ready:
            return self._blocked(event.event_id, "REARM_REQUIRED")
        cmd = Command(self.ids.next_id("command"), event.event_id, action, target,
                      self.state.context_version, now, event.captured_at_ms+250, snapshot)
        if not self.queue.offer(cmd):
            return self._blocked(event.event_id, "QUEUE_FULL")
        self._command_times[cmd.command_id]=(now,event.captured_at_ms)
        self.events.record('gesture',event_id=event.event_id,command_id=cmd.command_id,context=event.context_version,
                           epoch=event.camera_epoch,gesture=event.gesture,action=action,target=target,at_ms=now)
        # Zoom is incremental physical movement, not an OS key-repeat hold.
        cooldown = (1500 if action in (Action.BOOKMARK, Action.CAPTURE) else
                    200 if action in (Action.ZOOM_IN, Action.ZOOM_OUT) else 600)
        self._cooldown_until = now + cooldown
        self._reset_neutral()
        self._set(ready=False)
        return cmd

    def flush_executor(self):
        while (cmd := self.queue.take()) is not None:
            now = self.clock.now_ms()
            if cmd.command_id in self._executed:
                self._blocked(cmd.command_id, "DUPLICATE_COMMAND")
                continue
            self._executed[cmd.command_id] = now
            if cmd.context_version != self.state.context_version or now > cmd.deadline_ms:
                self._blocked(cmd.command_id, "STALE_COMMAND")
                continue
            if (self.state.activation != Activation.ACTIVE or self.state.blocked_reasons or self.state.release_pending
                    or self.state.confirmation_pending or self.state.dialog_lock):
                self._blocked(cmd.command_id, "INPUT_BLOCKED")
                continue
            if cmd.target == "APP":
                result = self.app_actions.execute(cmd) if self.app_actions else Result(cmd.command_id, cmd.context_version, now, Status.BLOCKED, "NOT_IMPLEMENTED")
            else:
                current = self.foreground.snapshot()
                if not current.is_chrome or current.identity != cmd.target_snapshot.identity:
                    self._blocked(cmd.command_id, "TARGET_CHANGED")
                    self._reset_neutral()
                    self._set(ready=False)
                    continue
                reply = self.keyboard.submit_chord(cmd, chord_for(cmd.action))
                if reply is None:
                    continue  # Async adapter delivers immutable replies through the UI pump.
                result, keys = reply
                self.on_keyboard_state(keys)
            self.on_execution_result(result, cmd.action)

    def on_execution_result(self, result, action):
        if result.context_version != self.state.context_version:
            return
        self._record(result)
        if result.status == Status.FAILED:
            self.block("INPUT_FAILED")
        elif result.status == Status.SENT and action == Action.BOOKMARK:
            self._set(confirmation_pending=True, ready=False)
