"""Keep Logix Designer on its own Windows virtual desktop so GUI automation runs out of sight.

Uses pyvda (Explorer's virtual-desktop COM interfaces). Moving another process's window needs
these internal interfaces: the documented IVirtualDesktopManager.MoveWindowToDesktop returns
E_ACCESSDENIED for windows of other processes. All helpers degrade to "unknown" instead of
raising, because those internal interfaces change between Windows builds.

Windows switches the user's desktop when a window on another desktop becomes the foreground
window, so callers must also keep Logix Designer out of the foreground (LockSetForegroundWindow).
"""
from __future__ import annotations

import ctypes

_DWMWA_CLOAKED = 14


def is_cloaked(hwnd: int) -> bool:
    """True when DWM hides the window, e.g. because it sits on another virtual desktop."""
    v = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, _DWMWA_CLOAKED, ctypes.byref(v), ctypes.sizeof(v))
    return v.value != 0


def info(hwnd: int | None = None) -> dict:
    out: dict = {}
    try:
        import pyvda
        out["desktops"] = len(pyvda.get_virtual_desktops())
        out["current"] = pyvda.VirtualDesktop.current().number
        if hwnd:
            out["window_desktop"] = pyvda.AppView(hwnd=hwnd).desktop.number
    except Exception as e:
        out["error"] = f"virtual desktop API unavailable: {e}"
    if hwnd:
        out["hidden_from_user"] = is_cloaked(hwnd)
    return out


def work_desktop_number() -> int:
    """The desktop Logix Designer lives on: the last one, created if there is only one."""
    import pyvda
    desktops = pyvda.get_virtual_desktops()
    if len(desktops) < 2:
        pyvda.VirtualDesktop.create()
        desktops = pyvda.get_virtual_desktops()
    return desktops[-1].number


def move_to_work_desktop(hwnd: int) -> dict:
    """Move hwnd to the work desktop unless the user is currently *on* that desktop.

    Never switches the user's desktop. If the user is looking at the work desktop, the window is
    left where it is (they are watching on purpose).
    """
    import pyvda
    target = work_desktop_number()
    view = pyvda.AppView(hwnd=hwnd)
    moved = False
    if view.desktop.number != target and pyvda.VirtualDesktop.current().number != target:
        view.move(pyvda.VirtualDesktop(target))
        moved = True
    return {"moved": moved, "work_desktop": target, **info(hwnd)}
