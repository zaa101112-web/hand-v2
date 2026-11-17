import ctypes
from ctypes import wintypes
import os
from hand_v2.domain.capture import Display


def physical_display(name,scale):
    if os.name!='nt':return None
    class MonitorInfo(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),
                  ('flags',wintypes.DWORD),('device',wintypes.WCHAR*32)]
    found=[]
    get_info=ctypes.windll.user32.GetMonitorInfoW
    get_info.argtypes=[wintypes.HMONITOR,ctypes.POINTER(MonitorInfo)]
    get_info.restype=wintypes.BOOL
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HMONITOR,wintypes.HDC,ctypes.POINTER(wintypes.RECT),wintypes.LPARAM)
    def callback(handle,dc,rect,data):
        info=MonitorInfo();info.size=ctypes.sizeof(info)
        if get_info(handle,ctypes.byref(info)) and info.device==name:
            effective_scale=scale
            if effective_scale is None:
                dpi_x=wintypes.UINT();dpi_y=wintypes.UINT()
                get_dpi=ctypes.windll.shcore.GetDpiForMonitor
                get_dpi.argtypes=[wintypes.HMONITOR,ctypes.c_int,ctypes.POINTER(wintypes.UINT),ctypes.POINTER(wintypes.UINT)]
                if get_dpi(handle,0,ctypes.byref(dpi_x),ctypes.byref(dpi_y))!=0:return True
                effective_scale=dpi_x.value/96
            r=info.monitor;found.append(Display(name,r.left,r.top,r.right-r.left,r.bottom-r.top,effective_scale))
        return True
    callback_ref=callback_type(callback)
    ctypes.windll.user32.EnumDisplayMonitors(None,None,callback_ref,0)
    return found[0] if found else None
