"""Studio 5000 Logix Designer v35 L5X export/import by driving the Logix Designer GUI.

v35 has no usable automation interface for L5X exchange (the Logix Designer SDK has no
import/export RPCs and the v35 COM server is unsupported), so these operations drive the
same UI a user would:
  export: File > Save As... > "Logix Designer XML File (*.L5X)"
  import: File > Open... > *.L5X > "Save Imported Project As" > Import   (creates a new ACD)

Everything is done with posted window messages (no real mouse or keyboard, no focus change):
menu items are located by name through UI Automation and clicked with WM_LBUTTON*, and the
standard file dialogs are filled with WM_SETTEXT. That keeps working while Logix Designer
sits on another virtual desktop, where it is moved by default, so the user's desktop is
undisturbed. Needs a logged-in, unlocked session. Any dialog outside the expected flow
(licensing, save-changes prompts, errors, ...) is left untouched and reported. Never goes
online, downloads or changes controller mode.
"""
from __future__ import annotations

import concurrent.futures
import ctypes
import os
import re
import subprocess
import time
from typing import NamedTuple

from . import vdesktop

LOGIX_EXE = os.environ.get(
    "LOGIX_EXE", r"C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU\v35\Bin\LogixDesigner.Exe")
# Move Logix Designer to another virtual desktop before driving it (set LOGIX_GUI_BACKGROUND=0 to watch it).
BACKGROUND = os.environ.get("LOGIX_GUI_BACKGROUND", "1") != "0"

_DLG_CLASS = "#32770"
_LSFW_LOCK, _LSFW_UNLOCK = 1, 2
_ID_OK, _ID_FILETYPE, _ID_FILENAME = 1, 1136, 1148
_TITLE_RX = re.compile(r"^Logix Designer - .* in (.+?) \[")


class GuiError(Exception):
    pass


class Win(NamedTuple):
    hwnd: int
    pid: int
    cls: str
    title: str


# ---------- pure helpers (no GUI) ----------
def project_file_from_title(title: str) -> str | None:
    """'Logix Designer - TF10 in Probe.ACD [5069-L330ERM 35.14]' -> 'Probe.ACD'."""
    m = _TITLE_RX.match(title or "")
    return m.group(1) if m else None


def title_matches(title: str, acd_path: str) -> bool:
    name = project_file_from_title(title)
    return bool(name) and name.lower() == os.path.basename(acd_path).lower()


def prepare_output(path: str, overwrite: bool) -> str | None:
    """Move an existing output aside as a .bak so the dialog never asks to replace. Returns the backup path."""
    if not os.path.exists(path):
        return None
    if not overwrite:
        raise GuiError(f"{path} already exists; pass overwrite=true to replace it (the old file is kept as .bak)")
    backup = path + ".bak"
    if os.path.exists(backup):
        backup = f"{path}.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    try:
        os.replace(path, backup)
    except OSError as e:
        raise GuiError(f"Cannot move {path} aside (open in Logix Designer?): {e}") from e
    return backup


def _restore(path: str, backup: str | None) -> None:
    if backup and not os.path.exists(path) and os.path.exists(backup):
        os.replace(backup, path)


# ---------- Win32 / UIA plumbing (runs on the GUI thread) ----------
def _windows(pid: int | None = None) -> list[Win]:
    import win32gui
    import win32process
    out: list[Win] = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h):
            p = win32process.GetWindowThreadProcessId(h)[1]
            if pid is None or p == pid:
                out.append(Win(h, p, win32gui.GetClassName(h), win32gui.GetWindowText(h)))
    win32gui.EnumWindows(cb, None)
    return out


def _project_windows() -> list[Win]:
    return [w for w in _windows() if w.cls.startswith("Afx:") and w.title.startswith("Logix Designer")]


def _dialogs(pid: int) -> list[Win]:
    return [w for w in _windows(pid) if w.cls == _DLG_CLASS]


def _dialog_text(hwnd: int) -> str:
    import win32gui
    parts: list[str] = []

    def cb(c, _):
        if win32gui.GetClassName(c) == "Static" and win32gui.GetWindowText(c).strip():
            parts.append(win32gui.GetWindowText(c).strip())
    win32gui.EnumChildWindows(hwnd, cb, None)
    return " | ".join(parts)[:1000]


def _describe_dialogs(dlgs: list[Win]) -> list[dict]:
    return [{"title": d.title, "text": _dialog_text(d.hwnd)} for d in dlgs]


def _check_dialogs(pid: int, allowed: set[str]) -> None:
    unexpected = [d for d in _dialogs(pid) if d.title not in allowed]
    if unexpected:
        raise GuiError("Unexpected Logix Designer dialog (left open, not touched): "
                       + repr(_describe_dialogs(unexpected)))


def _wait(pred, timeout: float, pid: int, allowed: set[str], what: str):
    end = time.time() + timeout
    while True:
        _check_dialogs(pid, allowed)
        r = pred()
        if r:
            return r
        if time.time() > end:
            raise GuiError(f"Timed out after {timeout:.0f}s waiting for {what}; open dialogs: "
                           + repr(_describe_dialogs(_dialogs(pid))))
        time.sleep(0.5)


def _wait_dialog(pid: int, title: str, timeout: float, allowed: set[str]) -> int:
    return _wait(lambda: next((d.hwnd for d in _dialogs(pid) if d.title == title), None),
                 timeout, pid, allowed | {title}, f"the '{title}' dialog")


def _set_text(hwnd: int, text: str) -> None:
    import win32con
    send = ctypes.windll.user32.SendMessageW
    send(hwnd, win32con.WM_SETTEXT, 0, ctypes.c_wchar_p(text))
    # GetWindowText can't read another process's edit control; WM_GETTEXT can.
    buf = ctypes.create_unicode_buffer(send(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0) + 1)
    send(hwnd, win32con.WM_GETTEXT, len(buf), buf)
    if buf.value != text:
        raise GuiError("Could not set the file name in the dialog")


def _select_file_type(dlg: int, pattern: str) -> None:
    import win32con
    import win32gui
    combo = win32gui.GetDlgItem(dlg, _ID_FILETYPE)
    for i in range(win32gui.SendMessage(combo, win32con.CB_GETCOUNT, 0, 0)):
        buf = ctypes.create_unicode_buffer(win32gui.SendMessage(combo, win32con.CB_GETLBTEXTLEN, i, 0) + 1)
        ctypes.windll.user32.SendMessageW(combo, win32con.CB_GETLBTEXT, i, buf)
        if pattern.lower() in buf.value.lower():
            win32gui.SendMessage(combo, win32con.CB_SETCURSEL, i, 0)
            win32gui.SendMessage(dlg, win32con.WM_COMMAND, (win32con.CBN_SELCHANGE << 16) | _ID_FILETYPE, combo)
            return
    raise GuiError(f"File type '{pattern}' not offered by the dialog")


def _submit_file_dialog(dlg: int, path: str, file_type: str | None = None) -> None:
    import win32con
    import win32gui
    if file_type:
        _select_file_type(dlg, file_type)
        time.sleep(0.5)
    host = win32gui.GetDlgItem(dlg, _ID_FILENAME)
    edit = win32gui.FindWindowEx(host, 0, "Edit", None) or host
    _set_text(edit, path)
    time.sleep(0.3)
    win32gui.PostMessage(dlg, win32con.WM_COMMAND, _ID_OK, win32gui.GetDlgItem(dlg, _ID_OK))


def _post_click(hwnd: int, x: int, y: int) -> None:
    """Click at client coordinates by posting messages: no real mouse, no focus change."""
    import win32api
    import win32con
    import win32gui
    lp = win32api.MAKELONG(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lp)
    time.sleep(0.15)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)


def _child(parent: int, pred) -> int | None:
    import win32gui
    found: list[int] = []

    def cb(h, _):
        if not found and pred(h):
            found.append(h)
    win32gui.EnumChildWindows(parent, cb, None)
    return found[0] if found else None


def _menu_popup(main: Win, name: str | None = "File") -> int | None:
    """hwnd of the BCGP toolbar inside an open popup menu called `name` (any menu if None).

    UIA reads the toolbar even when the window is cloaked on another virtual desktop.
    """
    import uiautomation as auto
    import win32gui
    for w in _windows(main.pid):
        if w.cls.startswith("Afx:") and not w.title and w.hwnd != main.hwnd:
            tb = _child(w.hwnd, lambda h: win32gui.GetClassName(h).startswith("BCGPToolBar"))
            if tb and (name is None or auto.ControlFromHandle(tb).Name == name):
                return tb
    return None


# x offsets (client coords, 96-dpi-independent at the scale Logix uses) of the top-level menus,
# measured on v35; _open_menu scans if a guess opens the wrong menu.
_MENU_X = {"File": 20, "Edit": 65, "View": 115, "Search": 190, "Logic": 265, "Communications": 340,
           "Tools": 515, "Window": 590, "Help": 690}


def _wait_popup(main: Win, name: str, timeout: float = 4) -> int:
    end = time.time() + timeout
    while time.time() < end:
        if (tb := _menu_popup(main, name)) is not None:
            return tb
        time.sleep(0.2)
    raise GuiError(f"Menu '{name}' did not open")


def _close_menus(main: Win) -> None:
    import win32con
    import win32gui
    for _ in range(4):
        tb = _menu_popup(main, None)
        if tb is None:
            return
        win32gui.PostMessage(tb, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)
        time.sleep(0.3)


def _open_menu(main: Win, name: str) -> int:
    import win32gui
    bar = _child(main.hwnd, lambda h: win32gui.GetWindowText(h) == "Menu Bar")
    if not bar:
        raise GuiError("Logix Designer menu bar not found")
    if (tb := _menu_popup(main, name)) is not None:  # clicking again would toggle an open menu closed
        return tb
    _close_menus(main)
    xs = [_MENU_X.get(name, 20)] + list(range(15, 760, 25))
    for x in xs:
        _post_click(bar, x, 12)
        for _ in range(10):
            if (tb := _menu_popup(main, name)) is not None:
                return tb
            if _menu_popup(main, None) is not None:
                break  # a different menu opened
            time.sleep(0.2)
        _close_menus(main)
    raise GuiError(f"Could not open the Logix Designer '{name}' menu")


def _open_file_menu(main: Win) -> int:
    return _open_menu(main, "File")


def _click_menu(toolbar: int, label: str) -> None:
    import uiautomation as auto
    import win32con
    import win32gui
    item = next((c for c in auto.ControlFromHandle(toolbar).GetChildren() if c.Name.startswith(label)), None)
    if item is None:
        win32gui.PostMessage(toolbar, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)
        raise GuiError(f"Menu item '{label}' not found in the File menu")
    r = item.BoundingRectangle
    _post_click(toolbar, *win32gui.ScreenToClient(toolbar, ((r.left + r.right) // 2, (r.top + r.bottom) // 2)))


# ---------- public API ----------
class LogixGui:
    def __init__(self, background: bool = BACKGROUND):
        self._pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="logix-gui")
        self.background = background
        self.last_desktop: dict | None = None

    def _run(self, fn, *args):
        def job():
            import uiautomation as auto
            # Logix Designer's dialogs call SetForegroundWindow; on another virtual desktop that
            # would switch the user over to it. Locking foreground changes blocks that.
            lock = self.background and bool(ctypes.windll.user32.LockSetForegroundWindow(_LSFW_LOCK))
            try:
                with auto.UIAutomationInitializerInThread():
                    return fn(*args)
            finally:
                if lock:
                    ctypes.windll.user32.LockSetForegroundWindow(_LSFW_UNLOCK)
        return self._pool.submit(job).result()

    # --- internals on the GUI thread ---
    @staticmethod
    def _find_project(acd_path: str) -> Win | None:
        return next((w for w in _project_windows() if title_matches(w.title, acd_path)), None)

    @staticmethod
    def _ensure_idle(main: Win, grace: float = 0) -> None:
        end = time.time() + grace
        while _dialogs(main.pid) and time.time() < end:
            time.sleep(0.5)
        dlgs = _dialogs(main.pid)
        if dlgs:
            raise GuiError("Logix Designer has a dialog open; close it first: " + repr(_describe_dialogs(dlgs)))

    def _ensure_project(self, acd_path: str, timeout: float) -> Win:
        main = self._find_project(acd_path)
        if main is None:
            if not os.path.isfile(acd_path):
                raise GuiError(f"File not found: {acd_path}")
            if not os.path.isfile(LOGIX_EXE):
                raise GuiError(f"Logix Designer not found at {LOGIX_EXE} (set LOGIX_EXE)")
            si = None
            if self.background:  # start minimized and without activation
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
            proc = subprocess.Popen([LOGIX_EXE, acd_path], startupinfo=si)
            end = time.time() + timeout
            while (main := self._find_project(acd_path)) is None:
                if time.time() > end:
                    raise GuiError(f"Logix Designer did not open {acd_path} within {timeout:.0f}s; dialogs: "
                                   + repr(_describe_dialogs(_dialogs(proc.pid))))
                self._move_new_windows(proc.pid)  # splash screen, loading windows
                time.sleep(0.2)
        self._hide(main)
        self._ensure_idle(main, grace=30)
        return main

    def _hide(self, main: Win) -> None:
        """Keep Logix Designer off the user's virtual desktop (best effort, never fatal)."""
        import win32con
        import win32gui
        if win32gui.IsIconic(main.hwnd):  # minimized windows still work, but restore for a sane layout
            win32gui.ShowWindow(main.hwnd, win32con.SW_SHOWNOACTIVATE)
        if self.background:
            try:
                self.last_desktop = vdesktop.move_to_work_desktop(main.hwnd)
            except Exception as e:
                self.last_desktop = {"error": f"could not move to another desktop: {e}"}

    def _move_new_windows(self, pid: int) -> None:
        if not self.background:
            return
        for w in _windows(pid):
            if not vdesktop.is_cloaked(w.hwnd):
                try:
                    vdesktop.move_to_work_desktop(w.hwnd)
                except Exception:
                    pass  # window vanished or is not movable; the main window is moved later anyway

    def _rehide(self, pid: int) -> None:
        """Logix Designer recreates its main window when it opens a project; move the new one too."""
        if self.background:
            for w in _project_windows():
                if w.pid == pid:
                    self._hide(w)

    def _export(self, acd_path: str, out_l5x: str, overwrite: bool, timeout: float) -> dict:
        acd, out = os.path.abspath(acd_path), os.path.abspath(out_l5x)
        if not out.lower().endswith(".l5x"):
            raise GuiError("out_l5x must end with .L5X")
        main = self._ensure_project(acd, timeout)
        backup = prepare_output(out, overwrite)
        try:
            _click_menu(_open_file_menu(main), "Save As")
            dlg = _wait_dialog(main.pid, "Save As", 15, set())
            _submit_file_dialog(dlg, out, "(*.L5X)")
            _wait(lambda: not _dialogs(main.pid) and os.path.isfile(out), timeout, main.pid,
                  {"Save As", "Exporting"}, "the export to finish")
        except Exception:
            _restore(out, backup)
            raise
        return {"exported": out, "bytes": os.path.getsize(out), "project": acd, "backup": backup,
                "desktop": vdesktop.info(main.hwnd)}

    def _import(self, l5x_path: str, out_acd: str, overwrite: bool, host_acd: str | None,
                timeout: float) -> dict:
        src, out = os.path.abspath(l5x_path), os.path.abspath(out_acd)
        if not os.path.isfile(src):
            raise GuiError(f"File not found: {src}")
        if not src.lower().endswith(".l5x") or not out.lower().endswith(".acd"):
            raise GuiError("l5x_path must be .L5X and out_acd must be .ACD")
        if self._find_project(out):
            raise GuiError(f"{os.path.basename(out)} is open in Logix Designer; close it or pick another out_acd")
        if host_acd:
            main = self._ensure_project(os.path.abspath(host_acd), timeout)
        else:
            mains = _project_windows()
            if not mains:
                raise GuiError("No Logix Designer project window is open; open any project or pass host_acd")
            main = mains[0]
            self._hide(main)
            self._ensure_idle(main)
        replaced = main.title
        backup = prepare_output(out, overwrite)
        flow = {"Open Project", "Save Imported Project As", "Importing"}
        try:
            _click_menu(_open_file_menu(main), "Open")
            _submit_file_dialog(_wait_dialog(main.pid, "Open Project", 15, set()), src)
            _submit_file_dialog(_wait_dialog(main.pid, "Save Imported Project As", 60, {"Open Project"}), out)
            _wait(lambda: not _dialogs(main.pid) and self._find_project(out), timeout, main.pid, flow,
                  "the import to finish")
        except Exception:
            _restore(out, backup)
            raise
        finally:
            _close_menus(main)
            self._rehide(main.pid)
        main = self._find_project(out) or main
        return {"imported": out, "bytes": os.path.getsize(out), "source": src,
                "window_was_showing": replaced, "backup": backup, "desktop": vdesktop.info(main.hwnd)}

    def _verify(self, acd_path: str, timeout: float) -> dict:
        """Logic > Verify > Controller, then read the Errors pane."""
        import win32con
        import win32gui
        acd = os.path.abspath(acd_path)
        main = self._ensure_project(acd, timeout)
        errors_pane = self._errors_text(main)
        _click_menu(_open_menu(main, "Logic"), "Verify")
        _click_menu(_wait_popup(main, "Verify"), "Controller")
        end = time.time() + timeout
        text = ""
        while time.time() < end:
            _check_dialogs(main.pid, set())
            text = self._errors_text(main)
            if text != errors_pane and re.search(r"Complete - \d+ error\(s\), \d+ warning\(s\)", text):
                break
            time.sleep(1)
        else:
            raise GuiError(f"Verify did not finish within {timeout:.0f}s")
        m = re.search(r"Complete - (\d+) error\(s\), (\d+) warning\(s\)", text)
        errs = [ln for ln in text.splitlines() if ln.startswith("Error")]
        return {"project": acd, "errors": int(m.group(1)), "warnings": int(m.group(2)), "error_lines": errs[:200]}

    @staticmethod
    def _errors_text(main: Win) -> str:
        import win32con
        import win32gui
        send = ctypes.windll.user32.SendMessageW
        best = ""
        hs: list[int] = []
        win32gui.EnumChildWindows(main.hwnd, lambda h, _: hs.append(h), None)
        for h in hs:
            if win32gui.GetClassName(h).startswith("RICHEDIT") and win32gui.IsWindowVisible(h):
                n = send(h, win32con.WM_GETTEXTLENGTH, 0, 0)
                buf = ctypes.create_unicode_buffer(n + 1)
                send(h, win32con.WM_GETTEXT, n + 1, buf)
                if "Complete -" in buf.value or len(buf.value) > len(best):
                    best = buf.value
        return best

    def verify(self, acd_path: str, timeout: float = 600) -> dict:
        return self._run(self._verify, acd_path, timeout)

    def _status(self) -> dict:
        return {"exe": LOGIX_EXE, "exe_found": os.path.isfile(LOGIX_EXE), "background": self.background,
                "desktop": vdesktop.info(),
                "projects": [{"title": w.title, "file": project_file_from_title(w.title), "pid": w.pid,
                              "desktop": vdesktop.info(w.hwnd),
                              "dialogs": _describe_dialogs(_dialogs(w.pid))} for w in _project_windows()]}

    # --- public, thread-safe ---
    def export_l5x(self, acd_path: str, out_l5x: str, overwrite: bool = False, timeout: float = 600) -> dict:
        return self._run(self._export, acd_path, out_l5x, overwrite, timeout)

    def import_l5x(self, l5x_path: str, out_acd: str, overwrite: bool = False, host_acd: str | None = None,
                   timeout: float = 900) -> dict:
        return self._run(self._import, l5x_path, out_acd, overwrite, host_acd, timeout)

    def status(self) -> dict:
        return self._run(self._status)
