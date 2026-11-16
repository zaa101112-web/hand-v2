from hand_v2.domain.models import ForegroundSnapshot


class WindowsForeground:
    def __init__(self, clock, native):
        self.clock, self.native = clock, native

    def snapshot(self):
        try:
            hwnd, pid, start, path = self.native.foreground_identity()
            return ForegroundSnapshot(self.clock.now_ms(), hwnd, pid, start, path, 'OK')
        except (OSError, ValueError):
            return ForegroundSnapshot(self.clock.now_ms(), query_status='FAILED')
