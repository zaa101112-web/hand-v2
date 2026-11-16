"""Typed Win32 bindings. No pointer movement, focus takeover or background messages."""
import ctypes as C
from ctypes import wintypes as W
import sys


class KEYBDINPUT(C.Structure):
    _fields_ = [('wVk', W.WORD), ('wScan', W.WORD), ('dwFlags', W.DWORD),
                ('time', W.DWORD), ('dwExtraInfo', C.c_size_t)]


class MOUSEINPUT(C.Structure):
    # Required solely for sizeof(INPUT); the public send API creates KEYBOARD only.
    _fields_ = [('dx', W.LONG), ('dy', W.LONG), ('mouseData', W.DWORD),
                ('dwFlags', W.DWORD), ('time', W.DWORD), ('dwExtraInfo', C.c_size_t)]


class HARDWAREINPUT(C.Structure):
    _fields_ = [('uMsg', W.DWORD), ('wParamL', W.WORD), ('wParamH', W.WORD)]


class INPUTUNION(C.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]


class INPUT(C.Structure):
    _anonymous_ = ('value',)
    _fields_ = [('type', W.DWORD), ('value', INPUTUNION)]


def bind(dll, name, args, result):
    function = getattr(dll, name)
    function.argtypes, function.restype = args, result
    return function


class Win32:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Windows real mode requires Windows')
        self.user = C.WinDLL('user32', use_last_error=True)
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        self.get_fg = bind(self.user, 'GetForegroundWindow', [], W.HWND)
        self.get_pid = bind(self.user, 'GetWindowThreadProcessId', [W.HWND, C.POINTER(W.DWORD)], W.DWORD)
        self.open_process = bind(self.kernel, 'OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
        self.query_path = bind(self.kernel, 'QueryFullProcessImageNameW', [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL)
        self.process_times = bind(self.kernel, 'GetProcessTimes', [W.HANDLE]+[C.POINTER(W.FILETIME)]*4, W.BOOL)
        self.close_handle = bind(self.kernel, 'CloseHandle', [W.HANDLE], W.BOOL)
        self.send_input = bind(self.user, 'SendInput', [W.UINT, C.POINTER(INPUT), C.c_int], W.UINT)
        self.async_key = bind(self.user, 'GetAsyncKeyState', [C.c_int], C.c_short)
        self.register = bind(self.user, 'RegisterHotKey', [W.HWND, C.c_int, W.UINT, W.UINT], W.BOOL)
        self.unregister = bind(self.user, 'UnregisterHotKey', [W.HWND, C.c_int], W.BOOL)

    def foreground_identity(self):
        hwnd = self.get_fg()
        if not hwnd:
            raise OSError('no foreground window')
        pid = W.DWORD()
        if not self.get_pid(hwnd, C.byref(pid)):
            raise C.WinError(C.get_last_error())
        handle = self.open_process(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
        if not handle:
            raise C.WinError(C.get_last_error())
        try:
            path, length = C.create_unicode_buffer(32768), W.DWORD(32768)
            times = [W.FILETIME() for _ in range(4)]
            if not self.query_path(handle, 0, path, C.byref(length)):
                raise C.WinError(C.get_last_error())
            if not self.process_times(handle, *[C.byref(t) for t in times]):
                raise C.WinError(C.get_last_error())
            if self.get_fg() != hwnd:
                raise OSError('foreground changed while querying')
            started = times[0].dwLowDateTime | times[0].dwHighDateTime << 32
            return int(hwnd), pid.value, started, path.value
        finally:
            self.close_handle(handle)

    def is_down(self, vk):
        return bool(self.async_key(vk) & 0x8000)

    def send(self, inputs):
        batch = (INPUT * len(inputs))()
        for item, key in zip(batch, inputs):
            item.type = 1  # INPUT_KEYBOARD only
            item.ki = KEYBDINPUT(key.vk, 0, key.flags, 0, 0)
        C.set_last_error(0)
        count = int(self.send_input(len(batch), batch, C.sizeof(INPUT)))
        return count, C.get_last_error()
