"""MCP server: Studio 5000 Logix Designer v35 program editing + FactoryTalk Logix Echo testing.

Three backends, each optional at runtime:
  * l5x   - offline L5X editing (always available, pure Python)
  * echo  - live tag read/write/test against Logix Echo over EtherNet/IP (pylogix)
  * gui   - ACD <-> L5X export/import by driving the Logix Designer v35 GUI (uiautomation)
  * logix - ACD project operations: Logix Designer SDK (gRPC) and RSLogix5000Services COM.
            Both need a Rockwell licence that allows automation.
"""
from __future__ import annotations

import json
import os
import tempfile

from mcp.server.fastmcp import FastMCP

from . import echo, l5x
from .com_client import ComError, LogixCom
from .gui_client import LogixGui
from .sdk_client import LogixSdk, SdkError

mcp = FastMCP("studio5000-echo")

_com: LogixCom | None = None
_sdk: LogixSdk | None = None
_gui: LogixGui | None = None
ECHO_COMM_PATH = os.environ.get("ECHO_COMM_PATH")  # e.g. as shown in Who Active for the Echo controller


def com() -> LogixCom:
    global _com
    if _com is None:
        _com = LogixCom()
    return _com


def sdk() -> LogixSdk:
    global _sdk
    if _sdk is None:
        _sdk = LogixSdk()
    return _sdk


def gui() -> LogixGui:
    global _gui
    if _gui is None:
        _gui = LogixGui()
    return _gui


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


def _err(e: Exception) -> str:
    return _j({"error": type(e).__name__, "message": str(e)})


# ======================= Echo (online) =======================
@mcp.tool()
def echo_info(ip: str | None = None, slot: int | None = None) -> str:
    """Identify the Logix Echo controller (product, firmware revision, emulator check). Default 127.0.0.1 slot 0."""
    try:
        return _j(echo.info(ip, slot))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_list_programs(ip: str | None = None, slot: int | None = None) -> str:
    """List programs currently downloaded in the Echo controller."""
    try:
        return _j(echo.list_programs(ip, slot))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_list_tags(program: str | None = None, name_filter: str | None = None, limit: int = 300,
                   ip: str | None = None, slot: int | None = None) -> str:
    """List controller-scope tags, or program-scope tags if `program` is given. `name_filter` is a case-insensitive substring."""
    try:
        return _j(echo.list_tags(program, name_filter, ip, slot, limit))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_read(tags: list[str], ip: str | None = None, slot: int | None = None) -> str:
    """Read live tag values. Program tags: 'Program:MainProgram.MyTag'. Members/arrays: 'Udt.Member', 'Arr[3]'."""
    try:
        return _j(echo.read(tags, ip, slot))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_write(values: dict, ip: str | None = None, slot: int | None = None) -> str:
    """Write live tag values, e.g. {"Start_PB": true, "Speed_SP": 12.5}. Only allowed on an Echo emulator."""
    try:
        return _j(echo.write(values, ip, slot))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_run_test(steps: list[dict], ip: str | None = None, slot: int | None = None) -> str:
    """Run a scripted test against the running Echo controller and return pass/fail per step.

    Steps (executed in order):
      {"write": {"Tag": value}}                         set inputs
      {"wait_ms": 200}                                  delay
      {"expect": {"tag": "Motor_Run", "op": "==", "value": true, "timeout_ms": 2000}}
                                                        poll until condition holds (ops: == != > >= < <= ~=)
      {"read": ["TagA", "TagB"]}                        snapshot values
    An expect step stops the test on failure unless it has "stop_on_fail": false.
    """
    try:
        return _j(echo.run_test(steps, ip, slot))
    except Exception as e:
        return _err(e)


# ======================= L5X (offline editing) =======================
@mcp.tool()
def l5x_summary(path: str) -> str:
    """Summarise an L5X export: controller, revision, tasks, programs, routines, UDTs, AOIs."""
    try:
        return _j(l5x.summary(path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_get_routine(path: str, program: str, routine: str, start: int = 0, count: int = 200) -> str:
    """Read a routine. Ladder returns rung number/comment/neutral text; ST returns lines."""
    try:
        return _j(l5x.get_routine(path, program, routine, start, count))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_list_tags(path: str, program: str | None = None, name_filter: str | None = None) -> str:
    """List tags in an L5X (controller scope, or program scope if `program` given). `name_filter` is a regex."""
    try:
        return _j(l5x.list_tags(path, program, name_filter))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_validate_rung(path: str, program: str, text: str) -> str:
    """Check ladder neutral text (e.g. 'XIC(Start)XIO(Stop)OTE(Motor);') for syntax and unknown tags without saving."""
    try:
        doc = l5x.load(path)
        return _j(l5x.validate_rung(text, doc.known_tag_names(program)))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_edit_rung(path: str, program: str, routine: str, action: str, number: int | None = None,
                  text: str | None = None, comment: str | None = None, out_path: str | None = None,
                  force: bool = False) -> str:
    """Modify a ladder routine in an L5X. action = replace | insert | append | delete.

    `number` is the 0-based rung index (insert puts the new rung before it). `text` is neutral
    ladder text ending in ';', branches as [A,B]. Unknown operand tags are rejected unless force=true.
    Writes to `out_path` if given, otherwise in place (original kept once as .bak).
    """
    try:
        return _j(l5x.edit_rung(path, program, routine, action, number, text, comment, out_path, force))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_set_st_routine(path: str, program: str, routine: str, code: str, out_path: str | None = None) -> str:
    """Replace the full body of a structured-text routine."""
    try:
        return _j(l5x.set_st_routine(path, program, routine, code, out_path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_add_routine(path: str, program: str, name: str, routine_type: str = "RLL",
                    description: str | None = None, out_path: str | None = None) -> str:
    """Create an empty RLL or ST routine in a program."""
    try:
        return _j(l5x.add_routine(path, program, name, routine_type, description, out_path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_add_tag(path: str, name: str, data_type: str, program: str | None = None,
                dimensions: str | None = None, description: str | None = None,
                initial_value: str | None = None, out_path: str | None = None) -> str:
    """Add a base tag (controller scope, or program scope if `program` given). `dimensions` like '10' or '4 8'."""
    try:
        return _j(l5x.add_tag(path, name, data_type, program, dimensions, description, initial_value, out_path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_set_tag_value(path: str, name: str, value: str, program: str | None = None,
                      out_path: str | None = None) -> str:
    """Set the stored (download) value of an atomic tag or 1-D array element, e.g. name='HMI_Dint[13]', value='5'."""
    try:
        return _j(l5x.set_tag_value(path, name, value, program, out_path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_delete_tag(path: str, name: str, program: str | None = None, out_path: str | None = None) -> str:
    """Delete a tag from an L5X."""
    try:
        return _j(l5x.delete_tag(path, name, program, out_path))
    except Exception as e:
        return _err(e)


# ======================= ACD <-> L5X via the Logix Designer GUI (v35) =======================
@mcp.tool()
def gui_status() -> str:
    """List Logix Designer project windows, which virtual desktop each is on, and any dialogs they have open."""
    try:
        return _j(gui().status())
    except Exception as e:
        return _err(e)


@mcp.tool()
def gui_export_l5x(acd_path: str, out_l5x: str, overwrite: bool = False, timeout_s: int = 600) -> str:
    """Export a whole ACD project to L5X by driving Logix Designer v35 (File > Save As > *.L5X).

    Opens the ACD in Logix Designer if it is not already open, and keeps it on another virtual
    desktop (env LOGIX_GUI_BACKGROUND=0 to disable). Driven by window messages only, so the user's
    mouse, keyboard and desktop are untouched; needs a logged-in, unlocked session. An existing
    out_l5x is replaced only with overwrite=true (old file kept as .bak). Unexpected dialogs abort
    the run and are reported, never clicked.
    """
    try:
        return _j(gui().export_l5x(acd_path, out_l5x, overwrite, timeout_s))
    except Exception as e:
        return _err(e)


@mcp.tool()
def gui_import_l5x(l5x_path: str, out_acd: str, overwrite: bool = False, host_acd: str | None = None,
                   timeout_s: int = 900) -> str:
    """Create a new ACD from an L5X by driving Logix Designer v35 (File > Open > *.L5X > Save Imported Project As).

    Runs in an already-open Logix Designer project window (or opens `host_acd` first); that window
    then shows the new project. If its current project has unsaved changes, Logix Designer's
    save prompt is reported and left open. An existing out_acd is replaced only with overwrite=true
    (old file kept as .bak). Never goes online or downloads.
    """
    try:
        return _j(gui().import_l5x(l5x_path, out_acd, overwrite, host_acd, timeout_s))
    except Exception as e:
        return _err(e)


@mcp.tool()
def gui_verify(acd_path: str, timeout_s: int = 600) -> str:
    """Run Logic > Verify > Controller in Logix Designer (background desktop) and return the error list."""
    try:
        return _j(gui().verify(acd_path, timeout_s))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_set_controller_type(path: str, catalog: str, out_path: str | None = None) -> str:
    """Retarget a full-project L5X to another controller catalog, e.g. 5069-L330ERM -> 1756-L81E for Echo, and back."""
    try:
        return _j(l5x.set_controller_type(path, catalog, out_path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_clone_module(path: str, template: str, name: str, address: str, out_path: str | None = None,
                     input_size: str | None = None, output_size: str | None = None) -> str:
    """Add an Ethernet module by copying an existing one (new name/IP; optional connection sizes)."""
    try:
        kw = {k: v for k, v in (("conn_InputSize", input_size), ("conn_OutputSize", output_size)) if v}
        return _j(l5x.clone_module(path, template, name, address, out_path, **kw))
    except Exception as e:
        return _err(e)


@mcp.tool()
def l5x_delete_aoi(path: str, name: str, out_path: str | None = None) -> str:
    """Delete an unused Add-On Instruction definition (refuses if any tag or logic still uses it)."""
    try:
        return _j(l5x.delete_aoi(path, name, out_path))
    except Exception as e:
        return _err(e)


# ======================= Logix Echo service API (gRPC :46520) =======================
def _echo_svc():
    from .echo_service import EchoService
    return EchoService()


@mcp.tool()
def echo_controllers() -> str:
    """List emulated controllers in Logix Echo (name, type/firmware, loaded project, mode)."""
    try:
        return _j(_echo_svc().controllers())
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_snapshot(controller: str, name: str, description: str = "") -> str:
    """Create an Echo snapshot of a controller (project + state) before overwriting it."""
    try:
        return _j(_echo_svc().snapshot(controller, name, description))
    except Exception as e:
        return _err(e)


@mcp.tool()
def echo_download(controller: str, acd_path: str, run_after: bool = True, timeout_s: int = 900) -> str:
    """Download an ACD to an Echo controller through the Echo service (no SDK/COM licence needed).

    Turns the key switch to PROGRAM, downloads, and back to RUN if run_after. The ACD must verify
    without errors and match the controller's catalog/firmware.
    """
    try:
        s = _echo_svc()
        s.set_key_switch(controller, "PROGRAM")
        res = s.download(controller, acd_path, timeout_s)
        if run_after:
            res["controller"] = s.set_key_switch(controller, "RUN")
        return _j(res)
    except Exception as e:
        return _err(e)


# ======================= ACD project (licensed backends) =======================
@mcp.tool()
def logix_backend_status(acd_path: str | None = None) -> str:
    """Check which ACD backends work here: Logix Designer SDK (gRPC :53204) and RSLogix5000Services COM.

    If `acd_path` is given, actually tries to open it with each backend (this is what reveals licensing problems).
    """
    out: dict = {}
    try:
        out["com"] = com().probe()
        if acd_path:
            out["com"]["open"] = com().open(acd_path)
    except Exception as e:
        out.setdefault("com", {})["error"] = str(e)
    try:
        if acd_path:
            out["sdk"] = {"open_key": sdk().open(acd_path), "comm_path": sdk().get_comm_path(acd_path)}
        else:
            out["sdk"] = {"note": "pass acd_path to test opening"}
    except Exception as e:
        out["sdk"] = {"error": str(e)}
    return _j(out)


@mcp.tool()
def acd_export_l5x(acd_path: str, out_l5x: str, xpath: str = "Controller") -> str:
    """Export an ACD (or a component via xpath, e.g. Controller/Programs/Program[@Name='MainProgram']) to L5X. COM backend."""
    try:
        return _j({"exported": com().export_xml(acd_path, xpath, out_l5x)})
    except Exception as e:
        return _err(e)


@mcp.tool()
def acd_import_l5x(acd_path: str, l5x_path: str, xpath: str = "Controller", target_name: str | None = None,
                   save: bool = True) -> str:
    """Import an L5X back into an ACD (overwrite on collision) and optionally save. COM backend.

    With `target_name` uses partial import (program/routine/AOI exports); otherwise a full XML import at `xpath`.
    """
    try:
        c = com()
        res = c.partial_import(acd_path, xpath, l5x_path, target_name) if target_name \
            else c.import_xml(acd_path, xpath, l5x_path)
        if save:
            res["saved"] = c.save(acd_path)
        return _j(res)
    except Exception as e:
        return _err(e)


@mcp.tool()
def acd_edit_rung(acd_path: str, program: str, routine: str, action: str, number: int | None = None,
                  text: str | None = None, comment: str | None = None, force: bool = False) -> str:
    """Edit a rung directly in an ACD: exports the program to L5X, applies the edit, re-imports and saves. COM backend."""
    try:
        c = com()
        tmp = os.path.join(tempfile.mkdtemp(prefix="s5k_"), f"{program}.L5X")
        xpath = f"Controller/Programs/Program[@Name='{program}']"
        c.export_xml(acd_path, xpath, tmp)
        edit = l5x.edit_rung(tmp, program, routine, action, number, text, comment, None, force)
        res = c.partial_import(acd_path, "Controller/Programs", tmp, program)
        res["edit"] = edit
        res["saved"] = c.save(acd_path)
        return _j(res)
    except Exception as e:
        return _err(e)


def _deploy_sdk(acd_path: str, comm_path: str | None, run_after: bool) -> dict:
    s = sdk()
    if comm_path:
        s.set_comm_path(acd_path, comm_path)
    s.change_mode(acd_path, "Program")
    s.download(acd_path)
    s.save(acd_path)
    if run_after:
        s.change_mode(acd_path, "Run")
    return {"backend": "sdk", "comm_path": s.get_comm_path(acd_path)}


def _deploy_com(acd_path: str, comm_path: str | None, run_after: bool) -> dict:
    c = com()
    if comm_path:
        c.set_comm_path(acd_path, comm_path)
    c.download(acd_path, "Run" if run_after else "Program")
    c.save(acd_path)
    return {"backend": "com", **c.status(acd_path)}


@mcp.tool()
def acd_deploy_to_echo(acd_path: str, comm_path: str | None = None, run_after: bool = True,
                       backend: str = "auto") -> str:
    """Download an ACD to the Logix Echo controller: Program mode -> download -> save -> Run.

    `comm_path` defaults to env ECHO_COMM_PATH, else the path stored in the project.
    The target must be an Echo emulator (checked over CIP first). backend = auto | sdk | com.
    """
    try:
        target = echo.info()
        if not target["is_emulator"] and not echo.ALLOW_REAL_PLC:
            return _j({"error": "SafetyGuard", "message": f"{target['product']} is not an Echo emulator"})
    except Exception as e:
        return _j({"error": "EchoUnreachable", "message": str(e)})
    comm_path = comm_path or ECHO_COMM_PATH
    errors = {}
    for name, fn in (("sdk", _deploy_sdk), ("com", _deploy_com)):
        if backend not in ("auto", name):
            continue
        try:
            res = fn(acd_path, comm_path, run_after)
            res["programs_in_controller"] = echo.list_programs()
            return _j(res)
        except (SdkError, ComError, OSError) as e:
            errors[name] = str(e)
    return _j({"error": "DeployFailed", "details": errors,
               "hint": "Both backends need a licensed Studio 5000 / Logix Designer SDK. "
                       "Without one, import the edited L5X in Logix Designer manually and download from there."})


@mcp.tool()
def acd_set_mode(acd_path: str, mode: str, backend: str = "sdk") -> str:
    """Change controller mode (Run | Program | Test) at the project's comm path. backend = sdk | com."""
    try:
        if backend == "com":
            com().set_mode(acd_path, mode)
        else:
            sdk().change_mode(acd_path, mode)
        return _j({"mode": mode, "ok": True})
    except Exception as e:
        return _err(e)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
