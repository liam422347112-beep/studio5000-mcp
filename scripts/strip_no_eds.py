"""Temporarily remove no-EDS device modules and programs that depend on them.

Devices without usable EDS lose IO tags on L5X import/export, which blocks Echo verify.
"""
from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from studio5000_mcp import l5x

PATH = Path(r"D:\BaiduSyncdisk\Openclaw\studiomcp\_local\e2e\Damin_EM16_SealingDown_Echo.L5X")

NO_EDS_MODULES = {"weight_plc", "Festo", "ArrangleIO", "PressureF", "Host", "SecondCount"}
DELETE_PROGRAMS = {"EM13_SpaceFeeder01", "EM30_IO_Status"}
# Patterns that reference those modules' produced tags / names in remaining logic
REF_RX = re.compile(
    r"\b(weight_plc|Festo|ArrangleIO|PressureF|Host|SecondCount)(:|\.|\b)",
    re.I,
)


def _program_of(el: etree._Element) -> etree._Element | None:
    p = el
    while p is not None:
        if p.tag == "Program":
            return p
        p = p.getparent()
    return None


def strip() -> dict:
    doc = l5x.load(str(PATH))
    report: dict = {"removed_modules": [], "removed_programs": [], "nopped_rungs": [], "nopped_lines": []}

    # 1) Delete dependent programs first
    programs = doc.controller.find("Programs")
    for prog in list(programs.iterfind("Program")):
        name = prog.get("Name")
        if name in DELETE_PROGRAMS:
            programs.remove(prog)
            report["removed_programs"].append(name)

    # Unschedule deleted programs
    for task in doc.controller.iterfind("Tasks/Task"):
        sp = task.find("ScheduledPrograms")
        if sp is None:
            continue
        for p in list(sp.iterfind("ScheduledProgram")):
            if p.get("Name") in DELETE_PROGRAMS:
                sp.remove(p)

    # 2) Remove no-EDS modules (and their children under Ethernet adapters if nested)
    mods = doc.controller.find("Modules")
    for m in list(mods.iterfind("Module")):
        if (m.get("Name") or "") in NO_EDS_MODULES:
            report["removed_modules"].append(m.get("Name"))
            mods.remove(m)

    # Nested modules under remaining parents may also be named; walk all descendants
    for m in list(doc.controller.iterfind(".//Modules/Module")):
        if (m.get("Name") or "") in NO_EDS_MODULES:
            parent = m.getparent()
            if parent is not None:
                report["removed_modules"].append(m.get("Name"))
                parent.remove(m)

    # 3) In remaining programs, NOP any rung/line still referencing those devices
    for el in list(doc.root.iter("Text")):
        if not el.text or not REF_RX.search(el.text):
            continue
        prog = _program_of(el)
        if prog is None:
            continue
        rung = el.getparent()
        if rung is None or rung.tag != "Rung":
            continue
        el.text = etree.CDATA("NOP();")
        c = rung.find("Comment")
        if c is None:
            c = etree.Element("Comment")
            rung.insert(0, c)
        c.text = etree.CDATA("Temporarily NOP — referenced device without EDS (import/export loses IO).")
        report["nopped_rungs"].append(f"{prog.get('Name')}/Rung{rung.get('Number')}")

    for el in list(doc.root.iter("Line")):
        if not el.text or not REF_RX.search(el.text):
            continue
        prog = _program_of(el)
        if prog is None:
            continue
        # Comment out ST line
        el.text = etree.CDATA("// stripped no-EDS ref: " + el.text.replace("\n", " ")[:120])
        report["nopped_lines"].append(f"{prog.get('Name')}/Line{el.get('Number')}")

    # Deselect EM13/EM30 conditions if present
    for name in ("EM13_Conditions", "EM30_Conditions"):
        tag = next((t for t in doc.controller.iterfind("Tags/Tag") if t.get("Name") == name), None)
        if tag is None:
            continue
        for m in tag.iterfind(".//DataValueMember"):
            if m.get("Name") == "Selected" and m.get("DataType") == "BOOL":
                m.set("Value", "0")

    saved = doc.save()
    report["saved"] = saved
    return report


if __name__ == "__main__":
    import json
    print(json.dumps(strip(), indent=1, ensure_ascii=False))
