from collections import deque
from queue import SimpleQueue, Empty
from threading import Condition, Event, Thread

from hand_v2.domain.models import Result, Status, ReleaseResult


class KeyboardWorker:
    """One serial executor. Priority releases discard queued commands; Qt drains replies."""
    def __init__(self, backend, clock):
        self.backend, self.clock = backend, clock
        self._condition = Condition()
        self._pending = deque()
        self._replies = SimpleQueue()
        self._idle = Event()
        self._idle.set()
        self._closing = False
        self._shutdown_confirmed = False
        self._generation = 0
        self._thread = Thread(target=self._run, name='HAND-keyboard', daemon=True)
        self._thread.start()

    def submit_chord(self, command, chord):
        with self._condition:
            if self._closing or len(self._pending) >= 8:
                return Result(command.command_id,command.context_version,self.clock.now_ms(),Status.BLOCKED,'WORKER_UNAVAILABLE'), self.backend.state
            self._pending.append(('command', (command, chord), self._generation))
            self._idle.clear()
            self._condition.notify()
        return None

    def release_owned_keys(self, request_id, context_version):
        with self._condition:
            self._generation += 1
            # Keep every release ACK so callers can match only their latest request.
            kept = deque()
            for kind, payload, generation in self._pending:
                if kind == 'command':
                    cmd, _ = payload
                    result = Result(cmd.command_id,cmd.context_version,self.clock.now_ms(),Status.CANCELLED,'RELEASE_REQUESTED')
                    self._replies.put(('command',(result,cmd.action,self.backend.state)))
                else:
                    kept.append((kind,payload,generation))
            self._pending = kept
            self._pending.appendleft(('release',(request_id,context_version),self._generation))
            self._idle.clear()
            self._condition.notify()
        return None

    def _run(self):
        while True:
            with self._condition:
                while not self._pending:
                    self._idle.set()
                    if self._closing:
                        return
                    self._condition.wait()
                kind, payload, generation = self._pending.popleft()
            try:
                if kind == 'command':
                    command, chord = payload
                    self.backend.can_send = lambda: generation == self._generation and not self._closing
                    if generation != self._generation or self._closing:
                        result = Result(command.command_id,command.context_version,self.clock.now_ms(),Status.CANCELLED,'RELEASE_REQUESTED')
                        state = self.backend.state
                    else:
                        result, state = self.backend.submit_chord(command, chord)
                    self._replies.put(('command',(result,command.action,state)))
                else:
                    result, state = self.backend.release_owned_keys(*payload)
                    if payload[0]=='worker-shutdown':
                        self._shutdown_confirmed=result.success and state.release_status=='CONFIRMED' and not state.owned_keys
                    self._replies.put(('release',(result,state)))
            except Exception as error:
                # The worker remains available for an explicit release after an adapter fault.
                if kind == 'command':
                    command, _ = payload
                    result=Result(command.command_id,command.context_version,self.clock.now_ms(),Status.FAILED,'WORKER_EXCEPTION',type(error).__name__)
                    self._replies.put(('command',(result,command.action,self.backend.state)))
                else:
                    self._replies.put(('release',(ReleaseResult(payload[0],False,self.clock.now_ms()),self.backend.state)))

    def drain(self):
        messages=[]
        while True:
            try: messages.append(self._replies.get_nowait())
            except Empty: return messages

    def wait_idle(self, timeout):
        return self._idle.wait(timeout)

    def close(self, timeout=1.0):
        if not self._thread.is_alive():
            return self._shutdown_confirmed and not self.backend.state.owned_keys
        self.release_owned_keys('worker-shutdown',0)
        with self._condition:
            self._closing=True
            self._condition.notify()
        self._thread.join(timeout)
        return not self._thread.is_alive() and self._shutdown_confirmed and not self.backend.state.owned_keys
