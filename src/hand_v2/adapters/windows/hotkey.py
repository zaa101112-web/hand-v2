class GlobalStopHotkey:
    ID = 0x4841

    def __init__(self, hwnd, stop, native):
        self.hwnd, self.stop, self.native = hwnd, stop, native
        self.registered = bool(native.register(hwnd, self.ID, 0x4000, 0x77))  # NOREPEAT, F8

    def dispatch(self, message, wparam):
        if self.registered and message == 0x0312 and wparam == self.ID:
            self.stop()
            return True
        return False

    def close(self):
        if self.registered:
            if not self.native.unregister(self.hwnd, self.ID):
                return False
            self.registered = False
        return True
