"""Build EM16_SealingDown into a working copy of the Damin_10 L5X.

Clones Sealing (2198-C4075-ERS) + EM14 axis mechanical params, adds program
EM16_SealingDown with LIM(master_angle±10) → time-based MAM (distance in Seconds),
gated by G_SealAllowRun. Resetting/home only returns to zero; PrepareExecution is immediate.
"""
from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

from lxml import etree

from studio5000_mcp import l5x

SRC = Path(r"D:\BaiduSyncdisk\Openclaw\studiomcp\studio5000-mcp\_local\e2e\CounterHost_20261107_141938.L5X")
OUT = Path(r"D:\BaiduSyncdisk\Openclaw\studiomcp\studio5000-mcp\_local\e2e\Damin_EM16_SealingDown.L5X")
MODULE = "SealingDown"
MODULE_IP = "192.168.10.85"
AXIS = "EM16_SealingDown"
PROG = "EM16_SealingDown"
STOP_EVT = "EM16_StopEvent"


def _cdata(parent: etree._Element, tag: str, text: str) -> None:
    el = etree.SubElement(parent, tag)
    el.text = etree.CDATA(text)


def _set_bool_member(tag_el: etree._Element, name: str, value: str) -> None:
    for m in tag_el.iterfind(".//DataValueMember"):
        if m.get("Name") == name and m.get("DataType") == "BOOL":
            m.set("Value", value)


def _add_real(doc: l5x.L5XDoc, name: str, value: str, desc: str) -> None:
    tags = doc.tags_container(None)
    if any(t.get("Name") == name for t in tags.iterfind("Tag")):
        return
    tag = etree.SubElement(
        tags, "Tag", Name=name, TagType="Base", DataType="REAL",
        Radix="Float", Constant="false", ExternalAccess="Read/Write")
    _cdata(tag, "Description", desc)
    data = etree.SubElement(tag, "Data", Format="Decorated")
    etree.SubElement(data, "DataValue", DataType="REAL", Radix="Float", Value=value)


def _add_bool(doc: l5x.L5XDoc, name: str, value: str, desc: str) -> None:
    tags = doc.tags_container(None)
    if any(t.get("Name") == name for t in tags.iterfind("Tag")):
        return
    tag = etree.SubElement(
        tags, "Tag", Name=name, TagType="Base", DataType="BOOL",
        Radix="Decimal", Constant="false", ExternalAccess="Read/Write")
    _cdata(tag, "Description", desc)
    data = etree.SubElement(tag, "Data", Format="Decorated")
    etree.SubElement(data, "DataValue", DataType="BOOL", Value=value)


def _add_dint(doc: l5x.L5XDoc, name: str) -> None:
    tags = doc.tags_container(None)
    if any(t.get("Name") == name for t in tags.iterfind("Tag")):
        return
    tag = etree.SubElement(
        tags, "Tag", Name=name, TagType="Base", DataType="DINT",
        Radix="Decimal", Constant="false", ExternalAccess="Read/Write")
    data = etree.SubElement(tag, "Data", Format="Decorated")
    etree.SubElement(data, "DataValue", DataType="DINT", Radix="Decimal", Value="0")


def _replace_rung_text(routine: etree._Element, number: int, text: str, comment: str | None = None) -> None:
    rll = routine.find("RLLContent")
    rung = next(r for r in rll.iterfind("Rung") if r.get("Number") == str(number))
    if comment is not None:
        c = rung.find("Comment")
        if c is None:
            c = etree.Element("Comment")
            rung.insert(0, c)
        c.text = etree.CDATA(comment)
    t = rung.find("Text")
    if t is None:
        t = etree.SubElement(rung, "Text")
    t.text = etree.CDATA(text)


def _clear_extra_rungs(routine: etree._Element, keep: int) -> None:
    rll = routine.find("RLLContent")
    for rung in list(rll.iterfind("Rung")):
        if int(rung.get("Number", "0")) >= keep:
            rll.remove(rung)


def _append_rung(routine: etree._Element, text: str, comment: str = "") -> None:
    rll = routine.find("RLLContent")
    n = len(list(rll.iterfind("Rung")))
    rung = etree.SubElement(rll, "Rung", Number=str(n), Type="N")
    if comment:
        _cdata(rung, "Comment", comment)
    _cdata(rung, "Text", text)


def build() -> dict:
    shutil.copy2(SRC, OUT)
    doc = l5x.load(str(OUT))

    # --- drive module ---
    info = l5x.clone_module(str(OUT), "Sealing", MODULE, MODULE_IP)
    doc = l5x.load(str(OUT))

    # --- axis tag (same mechanical params, new module channel) ---
    tags = doc.tags_container(None)
    src_axis = next(t for t in tags.iterfind("Tag") if t.get("Name") == "EM14_Sealing")
    if any(t.get("Name") == AXIS for t in tags.iterfind("Tag")):
        raise SystemExit(f"{AXIS} already exists")
    axis = copy.deepcopy(src_axis)
    axis.set("Name", AXIS)
    ap = axis.find("Data/AxisParameters")
    ap.set("MotionModule", f"{MODULE}:Ch1")
    # Keep unique AxisID empty-ish by clearing so Logix assigns on import if present
    if ap.get("AxisID"):
        ap.set("AxisID", "0")
    src_axis.addnext(axis)

    _add_dint(doc, STOP_EVT)
    _add_bool(doc, "HMI_SealingDownActive", "1", "1启用下横封轴 EM16_SealingDown")
    _add_real(doc, "HMI_SealingDownOnDeg", "90.0", "下横封 ON 主轴角度 deg")
    _add_real(doc, "HMI_SealingDownOffDeg", "180.0", "下横封 OFF 主轴角度 deg")
    _add_real(doc, "HMI_SealingDownOnTime", "0.5", "ON 段运行时间 s")
    _add_real(doc, "HMI_SealingDownOnDist", "10.0", "ON 段运行距离 deg")
    _add_real(doc, "HMI_SealingDownOffTime", "0.5", "OFF 段运行时间 s")
    _add_real(doc, "HMI_SealingDownOffDist", "-10.0", "OFF 段运行距离 deg (通常为回程)")
    _add_real(doc, "HMI_SealingDownWin", "10.0", "主轴角度触发窗口半宽 ±deg")

    # --- program: clone EM14 then retarget aliases + simplify run ---
    programs = doc.controller.find("Programs")
    src_prog = doc.program("EM14_Sealing")
    prog = copy.deepcopy(src_prog)
    prog.set("Name", PROG)
    programs.append(prog)

    # Fix program-scoped aliases / names
    rename = {
        "EM14_Conditions": "EM16_Conditions",
        "EM14_Sealing": AXIS,
        "EM14_StopEvent": STOP_EVT,
        "UN01_Recipe.EM14": "UN01_Recipe.EM16",
        "HMI_SealSelect": "HMI_SealingDownActive",  # avoid sharing seal cam select
    }
    for tag in prog.iterfind("Tags/Tag"):
        alias = tag.get("AliasFor")
        if alias in rename:
            tag.set("AliasFor", rename[alias])
        # Drop heavy cam AOI locals we will not use in CM05; keep structure for compile safety
    # Ensure local motion instructions for ON/OFF exist
    local_tags = prog.find("Tags")
    for name in ("MI_MAM_On", "MI_MAM_Off", "Wrk_OnLo", "Wrk_OnHi", "Wrk_OffLo", "Wrk_OffHi",
                 "Wrk_OnTrig", "Wrk_OffTrig", "Wrk_OnDone", "Wrk_OffDone"):
        if any(t.get("Name") == name for t in local_tags.iterfind("Tag")):
            continue
        if name.startswith("MI_"):
            etree.SubElement(local_tags, "Tag", Name=name, TagType="Base",
                             DataType="MOTION_INSTRUCTION", Constant="false", ExternalAccess="Read/Write")
        elif name.startswith("Wrk_") and name.endswith(("Trig", "Done")):
            t = etree.SubElement(local_tags, "Tag", Name=name, TagType="Base", DataType="BOOL",
                                 Radix="Decimal", Constant="false", ExternalAccess="Read/Write")
            d = etree.SubElement(t, "Data", Format="Decorated")
            etree.SubElement(d, "DataValue", DataType="BOOL", Value="0")
        else:
            t = etree.SubElement(local_tags, "Tag", Name=name, TagType="Base", DataType="REAL",
                                 Radix="Float", Constant="false", ExternalAccess="Read/Write")
            d = etree.SubElement(t, "Data", Format="Decorated")
            etree.SubElement(d, "DataValue", DataType="REAL", Radix="Float", Value="0.0")

    # Rewrite CDATA that still hard-codes EM14_Sealing / EM14_Conditions in rungs
    for el in prog.iter("Text", "Line"):
        if el.text:
            s = el.text
            s = s.replace("EM14_Sealing", AXIS)
            s = s.replace("EM14_Conditions", "EM16_Conditions")
            s = s.replace("EM14_StopEvent", STOP_EVT)
            if s != el.text:
                el.text = etree.CDATA(s) if not isinstance(el.text, etree.CDATA) else etree.CDATA(s)

    # Selected: use HMI_SealingDownActive
    main = next(r for r in prog.iterfind("Routines/Routine") if r.get("Name") == "MainRoutine")
    _replace_rung_text(
        main, 1,
        "[XIC(HMI_SealingDownActive) OTE(Out_EMConditions.Selected) ,XIO(HMI_SealingDownActive) OTU(Out_EMConditions.Selected) ];",
        "EM16 selected when HMI_SealingDownActive",
    )
    # StartExecutionDone: pass-through (avoid Sts_Started ↔ Wrk_EM_Executing deadlock)
    _replace_rung_text(
        main, 14,
        "XIC(Inp_Commands.StartExecution)OTE(Out_EMConditions.StartExecutionDone);",
        "StartExecutionDone follows StartExecution",
    )
    # PrepareExecution: immediate done (resetting only needs home)
    _replace_rung_text(
        main, 17,
        "XIC(Inp_Commands.PrepareExecution)OTE(Out_EMConditions.PrepareExecutionDone);",
        "PrepareExecution immediate — no cam generation for EM16",
    )
    # HomeDone: at zero
    _replace_rung_text(
        main, 16,
        "XIC(Inp_Commands.Home)[CMP(ABS(Ref_Axis.ActualPosition)<1) ,CMP(ABS(Ref_Axis.ActualPosition)>359) ]OTE(Out_EMConditions.HomeDone);",
        "Home done when at zero position",
    )

    # CM02 home move stays MAM to 0 (already there)
    cm02 = next(r for r in prog.iterfind("Routines/Routine") if r.get("Name") == "CM02_ServoAxisObject")
    _replace_rung_text(
        cm02, 7,
        "XIC(Inp_Commands.Home)ONS(ONS.3)MAM(Ref_Axis,MI_MAM_Home,2,0,SpaceFeederHomeSpd,Units per sec,1000,Units per sec2,1000,Units per sec2,Trapezoidal,100,100,% of Time,Disabled,Programmed,0,None,0,0);",
        "Resetting: move to zero only",
    )

    # Replace CM05_ServoRun with LIM±10 → time-based MAM
    cm05 = next(r for r in prog.iterfind("Routines/Routine") if r.get("Name") == "CM05_ServoRun")
    _clear_extra_rungs(cm05, 1)
    _replace_rung_text(cm05, 0, "NOP();", "EM16_SealingDown run: LIM(master±Win) → MAM distance in Seconds")
    for name in ("Wrk_InOnWin", "Wrk_InOffWin"):
        if not any(t.get("Name") == name for t in local_tags.iterfind("Tag")):
            t = etree.SubElement(local_tags, "Tag", Name=name, TagType="Base", DataType="BOOL",
                                 Radix="Decimal", Constant="false", ExternalAccess="Read/Write")
            d = etree.SubElement(t, "Data", Format="Decorated")
            etree.SubElement(d, "DataValue", DataType="BOOL", Value="0")

    _append_rung(
        cm05,
        "XIC(Unit01_Auto)XIC(G_SealAllowRun)XIC(HMI_SealingDownActive)"
        "SUB(HMI_SealingDownOnDeg,HMI_SealingDownWin,Wrk_OnLo)ADD(HMI_SealingDownOnDeg,HMI_SealingDownWin,Wrk_OnHi)"
        "LIM(Wrk_OnLo,Ref_MasterAxis.CommandPosition,Wrk_OnHi)OTE(Wrk_InOnWin);",
        "ON window: master angle ± Win",
    )
    _append_rung(
        cm05,
        "XIC(Wrk_InOnWin)ONS(ONS.0)XIO(Wrk_OnDone)OTL(Wrk_OnTrig);",
        "Rising edge into ON window",
    )
    _append_rung(
        cm05,
        "XIO(Wrk_InOnWin)OTU(Wrk_OnDone);",
        "Allow next ON fire after leaving window",
    )
    _append_rung(
        cm05,
        "XIC(Wrk_OnTrig)[ONS(ONS.1) CLR(MI_MAM_On.FLAGS) "
        ",MAM(Ref_Axis,MI_MAM_On,1,HMI_SealingDownOnDist,HMI_SealingDownOnTime,Seconds,"
        "0.2,Seconds,0.2,Seconds,S-Curve,100,100,% of Time,Disabled,Programmed,0,None,0,0) "
        ",XIC(MI_MAM_On.PC) OTL(Wrk_OnDone) OTU(Wrk_OnTrig) ];",
        "ON: incremental MAM distance over OnTime (Seconds)",
    )
    _append_rung(
        cm05,
        "XIC(Unit01_Auto)XIC(G_SealAllowRun)XIC(HMI_SealingDownActive)"
        "SUB(HMI_SealingDownOffDeg,HMI_SealingDownWin,Wrk_OffLo)ADD(HMI_SealingDownOffDeg,HMI_SealingDownWin,Wrk_OffHi)"
        "LIM(Wrk_OffLo,Ref_MasterAxis.CommandPosition,Wrk_OffHi)OTE(Wrk_InOffWin);",
        "OFF window: master angle ± Win",
    )
    _append_rung(
        cm05,
        "XIC(Wrk_InOffWin)ONS(ONS.2)XIO(Wrk_OffDone)OTL(Wrk_OffTrig);",
        "Rising edge into OFF window",
    )
    _append_rung(
        cm05,
        "XIO(Wrk_InOffWin)OTU(Wrk_OffDone);",
        "Allow next OFF fire after leaving window",
    )
    _append_rung(
        cm05,
        "XIC(Wrk_OffTrig)[ONS(ONS.3) CLR(MI_MAM_Off.FLAGS) "
        ",MAM(Ref_Axis,MI_MAM_Off,1,HMI_SealingDownOffDist,HMI_SealingDownOffTime,Seconds,"
        "0.2,Seconds,0.2,Seconds,S-Curve,100,100,% of Time,Disabled,Programmed,0,None,0,0) "
        ",XIC(MI_MAM_Off.PC) OTL(Wrk_OffDone) OTU(Wrk_OffTrig) ];",
        "OFF: incremental MAM distance over OffTime (Seconds)",
    )
    _append_rung(
        cm05,
        "XIC(Inp_Commands.StartExecution)OTE(Sts_Started);",
        "Sts_Started tracks StartExecution (no circular dep on Wrk_EM_Executing)",
    )

    # Mark EM16 selected in controller tag
    cond = next(t for t in tags.iterfind("Tag") if t.get("Name") == "EM16_Conditions")
    _set_bool_member(cond, "Selected", "1")

    # Schedule on Super (same as EM14)
    for task in doc.controller.iterfind("Tasks/Task"):
        if task.get("Name") == "Super":
            sp = task.find("ScheduledPrograms")
            if not any(p.get("Name") == PROG for p in sp.iterfind("ScheduledProgram")):
                # insert after EM14_Sealing if present
                anchor = next((p for p in sp.iterfind("ScheduledProgram") if p.get("Name") == "EM14_Sealing"), None)
                node = etree.Element("ScheduledProgram", Name=PROG)
                if anchor is not None:
                    anchor.addnext(node)
                else:
                    sp.append(node)
            break

    saved = doc.save()
    summary = l5x.summary(str(OUT))
    em16 = next(p for p in summary["programs"] if p["name"] == PROG)
    return {
        "saved": saved,
        "module": info,
        "axis": AXIS,
        "program": em16,
        "processor": summary["processor"],
        "note": "Time-based MAM(Seconds) used for 运行时间+距离; Logix has no MATC opcode in this project style.",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build(), indent=1, default=str))
