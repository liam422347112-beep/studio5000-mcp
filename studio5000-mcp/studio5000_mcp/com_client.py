"""Studio 5000 Logix Designer v35 automation through the RSLogix5000Services COM server.

This is the path that supports program modification inside an ACD project (L5X export,
partial L5X import of programs/routines/rungs, save, download). All COM calls run on one
dedicated STA thread because the server is apartment-threaded and the MCP server is async.

Requires a Studio 5000 edition/licence that permits automation; otherwise every project call
fails with 0x8000FFFF (Lgx_E_SERVICES_ERROR).
"""
from __future__ import annotations

import concurrent.futures
import os
import threading

PROGID = os.environ.get("LOGIX_COM_PROGID", "RSLogix5000Services.LogixServices.35.00")

# Enum values from the RSLogix5000Services v35 type library
EXPORT_DEFAULT = 0
IMPORT_OVERWRITE_ON_COLL = 2
PARTIAL_IMPORT_ACCEPT_EDITS = 1
PARTIAL_IMPORT_FINALIZE_EDITS = 2
MODES = {"Unknown": 0, "Run": 1, "Program": 2, "Faulted": 3, "Debug": 4}
MODE_NAMES = {v: k for k, v in MODES.items()}
IMPORT_STATUS = {0: "NoErrors", 1: "ErrorsNoChanges", 2: "ErrorsWithChanges", 3: "AbortNoChanges",
                 4: "AbortWithChanges"}


class ComError(Exception):
    pass


def _describe(e: Exception) -> str:
    args = getattr(e, "args", ())
    if len(args) > 2 and args[2]:
        return f"{args[2][2]} (hr={args[2][5]})"
    return str(e)


class LogixCom:
    def __init__(self):
        self._pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="logix-com",
                                                           initializer=self._init_thread)
        self._svc = None
        self._projects: dict[str, object] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _init_thread():
        import pythoncom
        pythoncom.CoInitialize()

    def _run(self, fn, *args):
        return self._pool.submit(fn, *args).result()

    # ----- internals executed on the COM thread -----
    def _service(self):
        if self._svc is None:
            import win32com.client
            self._svc = win32com.client.Dispatch(PROGID)
        return self._svc

    def _controller(self, path: str):
        path = os.path.abspath(path)
        c = self._projects.get(path)
        if c is None:
            try:
                c = self._service().Open(path)
            except Exception as e:
                raise ComError(f"Open failed for {path}: {_describe(e)}") from e
            self._projects[path] = c
        return c

    def _wrap(self, what: str, fn):
        try:
            return fn()
        except ComError:
            raise
        except Exception as e:
            raise ComError(f"{what} failed: {_describe(e)}") from e

    # ----- public API -----
    def probe(self) -> dict:
        def f():
            svc = self._service()
            return {"progid": PROGID, "type": int(svc.GetType()),
                    "interface_ok": bool(svc.IsInterfaceVersionSupported(256))}
        return self._run(lambda: self._wrap("probe", f))

    def open(self, path: str) -> dict:
        def f():
            c = self._controller(path)
            return {"name": c.Name, "file": c.FilePath, "comm_path": c.ProjectCommPath}
        return self._run(lambda: self._wrap("open", f))

    def close(self, path: str) -> None:
        def f():
            c = self._projects.pop(os.path.abspath(path), None)
            if c is not None:
                c.ForceClose()
        self._run(lambda: self._wrap("close", f))

    def export_xml(self, path: str, xpath: str, out_file: str) -> str:
        """xpath examples: 'Controller', 'Controller/Programs/Program[@Name=\"Main\"]'."""
        def f():
            c = self._controller(path)
            c.ExportXMLToFile(0, xpath, EXPORT_DEFAULT, False, os.path.abspath(out_file))
            return os.path.abspath(out_file)
        return self._run(lambda: self._wrap("export", f))

    def import_xml(self, path: str, xpath: str, xml_file: str) -> dict:
        def f():
            c = self._controller(path)
            log = os.path.abspath(xml_file) + ".import.log"
            res = c.ImportXMLFromFile(0, xpath, os.path.abspath(xml_file), IMPORT_OVERWRITE_ON_COLL,
                                      log, False)
            return {"result": str(res), "log": log}
        return self._run(lambda: self._wrap("import", f))

    def partial_import(self, path: str, xpath: str, l5x_file: str, target_name: str,
                       comment: str = "MCP import") -> dict:
        """Import a partial L5X (program/routine/AOI/UDT export) into the open project."""
        def f():
            c = self._controller(path)
            log = os.path.abspath(l5x_file) + ".import.log"
            res = c.PartialImportFromL5XFile(0, xpath, os.path.abspath(l5x_file), target_name,
                                             IMPORT_OVERWRITE_ON_COLL, log, comment, False)
            return {"result": str(res), "log": log}
        return self._run(lambda: self._wrap("partial import", f))

    def save(self, path: str, save_as: str | None = None) -> str:
        def f():
            c = self._controller(path)
            if save_as:
                c.SaveAs(os.path.abspath(save_as))
                return os.path.abspath(save_as)
            c.Save()
            return c.FilePath
        return self._run(lambda: self._wrap("save", f))

    def set_comm_path(self, path: str, comm_path: str) -> None:
        def f():
            c = self._controller(path)
            c.ProjectCommPath = comm_path
            c.CurrentCommPath = comm_path
        self._run(lambda: self._wrap("set comm path", f))

    def status(self, path: str) -> dict:
        def f():
            c = self._controller(path)
            return {"name": c.Name, "comm_path": c.CurrentCommPath, "mode": MODE_NAMES.get(int(c.Mode), c.Mode),
                    "connected_state": int(c.ConnectedState), "dirty": bool(c.ProjectIsDirty)}
        return self._run(lambda: self._wrap("status", f))

    def go_online(self, path: str) -> None:
        self._run(lambda: self._wrap("go online", lambda: self._controller(path).GoOnline()))

    def go_offline(self, path: str) -> None:
        self._run(lambda: self._wrap("go offline", lambda: self._controller(path).GoOffline()))

    def set_mode(self, path: str, mode: str) -> None:
        def f():
            c = self._controller(path)
            c.Mode = MODES[mode]
        self._run(lambda: self._wrap("set mode", f))

    def download(self, path: str, final_mode: str = "Program") -> None:
        def f():
            c = self._controller(path)
            # Download(EnableForces, ApplyPortChanges, Mode, EnableEvents)
            c.Download(False, False, MODES[final_mode], False)
        self._run(lambda: self._wrap("download", f))
