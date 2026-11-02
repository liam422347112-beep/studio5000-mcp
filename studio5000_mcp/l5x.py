"""Offline editing of Studio 5000 (v35) L5X export files.

Works on full-project exports and on partial exports (Program / Routine / Rung
targets). All writes keep CDATA sections and back up the original file once
as <file>.bak before the first modification.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field

from lxml import etree

ATOMIC_TYPES = {"BOOL", "SINT", "INT", "DINT", "LINT", "USINT", "UINT", "UDINT",
                "ULINT", "REAL", "LREAL"}

# Instructions whose operands are labels/routines/keywords, not tags.
_NON_TAG_OPERAND_INSTR = {"JSR", "SBR", "RET", "JMP", "LBL", "GSV", "SSV", "AFI", "NOP",
                          "TND", "MCR", "UID", "UIE", "EVENT", "IOT"}


class L5XError(Exception):
    pass


@dataclass
class L5XDoc:
    path: str
    tree: etree._ElementTree
    root: etree._Element = field(init=False)

    def __post_init__(self):
        self.root = self.tree.getroot()
        if self.root.tag != "RSLogix5000Content":
            raise L5XError(f"{self.path} is not an L5X file (root <{self.root.tag}>)")

    @property
    def controller(self) -> etree._Element:
        c = self.root.find("Controller")
        if c is None:
            raise L5XError("No <Controller> element found")
        return c

    # ---------- lookup ----------
    def program(self, name: str) -> etree._Element:
        for p in self.root.iterfind(".//Programs/Program"):
            if p.get("Name", "").lower() == name.lower():
                return p
        raise L5XError(f"Program '{name}' not found. Available: {', '.join(self.program_names())}")

    def program_names(self) -> list[str]:
        return [p.get("Name") for p in self.root.iterfind(".//Programs/Program")]

    def routine(self, program: str, routine: str) -> etree._Element:
        prog = self.program(program)
        for r in prog.iterfind("Routines/Routine"):
            if r.get("Name", "").lower() == routine.lower():
                return r
        names = [r.get("Name") for r in prog.iterfind("Routines/Routine")]
        raise L5XError(f"Routine '{routine}' not found in program '{program}'. Available: {', '.join(names)}")

    def tags_container(self, program: str | None) -> etree._Element:
        parent = self.program(program) if program else self.controller
        tags = parent.find("Tags")
        if tags is None:
            tags = etree.Element("Tags")
            # Tags must precede Routines inside a Program, and DataTypes/Modules/AOIs
            # precede Tags in a Controller; insert before the first known follower.
            followers = ("Routines", "ChildPrograms") if program else ("Programs", "Tasks")
            anchor = next((parent.find(f) for f in followers if parent.find(f) is not None), None)
            if anchor is not None:
                anchor.addprevious(tags)
            else:
                parent.append(tags)
        return tags

    def known_tag_names(self, program: str | None) -> set[str]:
        names = {t.get("Name", "").lower() for t in self.controller.iterfind("Tags/Tag")}
        if program:
            try:
                names |= {t.get("Name", "").lower() for t in self.program(program).iterfind("Tags/Tag")}
            except L5XError:
                pass
        return names

    # ---------- save ----------
    def save(self, out_path: str | None = None) -> str:
        target = out_path or self.path
        if target == self.path and os.path.exists(target) and not os.path.exists(target + ".bak"):
            shutil.copy2(target, target + ".bak")
        self.tree.write(target, xml_declaration=True, encoding="UTF-8", standalone=True)
        return target


def load(path: str) -> L5XDoc:
    if not os.path.isfile(path):
        raise L5XError(f"File not found: {path}")
    parser = etree.XMLParser(strip_cdata=False, remove_blank_text=False, huge_tree=True)
    return L5XDoc(path, etree.parse(path, parser))


def _cdata_text(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _set_cdata(parent: etree._Element, tag: str, text: str, before: str | None = None) -> None:
    el = parent.find(tag)
    if el is None:
        el = etree.Element(tag)
        anchor = parent.find(before) if before else None
        if anchor is not None:
            anchor.addprevious(el)
        else:
            parent.append(el)
    el.text = etree.CDATA(text)


# ---------- read ----------
def summary(path: str) -> dict:
    doc = load(path)
    c = doc.controller
    tasks = []
    for t in c.iterfind("Tasks/Task"):
        tasks.append({
            "name": t.get("Name"), "type": t.get("Type"), "rate_ms": t.get("Rate"),
            "priority": t.get("Priority"),
            "programs": [s.get("Name") for s in t.iterfind("ScheduledPrograms/ScheduledProgram")],
        })
    programs = []
    for p in doc.root.iterfind(".//Programs/Program"):
        routines = []
        for r in p.iterfind("Routines/Routine"):
            kind = r.get("Type")
            size = len(r.findall("RLLContent/Rung")) if kind == "RLL" else len(r.findall("STContent/Line"))
            routines.append({"name": r.get("Name"), "type": kind, "rungs_or_lines": size})
        programs.append({
            "name": p.get("Name"), "main_routine": p.get("MainRoutineName"),
            "disabled": p.get("Disabled") == "true", "tag_count": len(p.findall("Tags/Tag")),
            "routines": routines,
        })
    return {
        "file": path,
        "target_type": doc.root.get("TargetType"),
        "target_name": doc.root.get("TargetName"),
        "software_revision": doc.root.get("SoftwareRevision"),
        "controller": c.get("Name"),
        "processor": c.get("ProcessorType"),
        "major_rev": c.get("MajorRev"),
        "controller_tag_count": len(c.findall("Tags/Tag")),
        "udts": [d.get("Name") for d in c.iterfind("DataTypes/DataType")],
        "aois": [a.get("Name") for a in c.iterfind("AddOnInstructionDefinitions/AddOnInstructionDefinition")],
        "tasks": tasks,
        "programs": programs,
    }


def get_routine(path: str, program: str, routine: str, start: int = 0, count: int = 200) -> dict:
    doc = load(path)
    r = doc.routine(program, routine)
    kind = r.get("Type")
    out: dict = {"program": program, "routine": r.get("Name"), "type": kind}
    if kind == "RLL":
        rungs = r.findall("RLLContent/Rung")
        out["total_rungs"] = len(rungs)
        out["rungs"] = [{
            "number": int(g.get("Number", i)),
            "comment": _cdata_text(g.find("Comment")),
            "text": _cdata_text(g.find("Text")),
        } for i, g in enumerate(rungs)][start:start + count]
    elif kind == "ST":
        lines = r.findall("STContent/Line")
        out["total_lines"] = len(lines)
        out["lines"] = [{"number": int(l.get("Number", i)), "text": l.text or ""}
                        for i, l in enumerate(lines)][start:start + count]
    else:
        out["note"] = f"{kind} routines are returned as raw XML."
        out["xml"] = etree.tostring(r, encoding="unicode")[:20000]
    return out


def list_tags(path: str, program: str | None = None, name_filter: str | None = None) -> list[dict]:
    doc = load(path)
    parent = doc.program(program) if program else doc.controller
    rx = re.compile(name_filter, re.I) if name_filter else None
    tags = []
    for t in parent.iterfind("Tags/Tag"):
        if rx and not rx.search(t.get("Name", "")):
            continue
        tags.append({
            "name": t.get("Name"), "data_type": t.get("DataType"), "tag_type": t.get("TagType"),
            "dimensions": t.get("Dimensions"), "alias_for": t.get("AliasFor"),
            "description": _cdata_text(t.find("Description")),
        })
    return tags


# ---------- validation ----------
def _split_top_level(args: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def validate_rung(text: str, known_tags: set[str] | None = None) -> dict:
    """Structural checks plus a best-effort unknown-tag warning list."""
    errors, warnings = [], []
    t = text.strip()
    if not t:
        errors.append("Rung text is empty")
    if t and not t.endswith(";"):
        errors.append("Rung text must end with ';'")
    for o, c in (("(", ")"), ("[", "]")):
        depth = 0
        for ch in t:
            depth += (ch == o) - (ch == c)
            if depth < 0:
                break
        if depth != 0:
            errors.append(f"Unbalanced '{o}{c}'")

    instructions = []
    if not errors and known_tags is not None:
        for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\(", t):
            instr = m.group(1)
            # find matching close paren for this instruction's operand list
            i, depth = m.end(), 1
            while i < len(t) and depth:
                depth += (t[i] == "(") - (t[i] == ")")
                i += 1
            operands = t[m.end():i - 1]
            instructions.append(instr)
            if instr.upper() in _NON_TAG_OPERAND_INSTR or instr.upper() in ("CPT", "CMP", "FAL", "FSC"):
                continue
            for op in _split_top_level(operands):
                if not op or op == "?" or re.fullmatch(r"[-+]?[\d.#_eE]+", op) or op.startswith(("'", '"')):
                    continue
                base = re.split(r"[.\[]", op, maxsplit=1)[0]
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_:]*", base):
                    base_l = base.lower()
                    if base_l.startswith("program:"):
                        continue
                    if base_l not in known_tags:
                        warnings.append(f"{instr}: operand '{op}' references unknown tag '{base}'")
    return {"ok": not errors, "errors": errors, "warnings": sorted(set(warnings)),
            "instructions": instructions}


# ---------- modify ----------
def _renumber(container: etree._Element, child: str) -> None:
    for i, el in enumerate(container.findall(child)):
        el.set("Number", str(i))


def edit_rung(path: str, program: str, routine: str, action: str, number: int | None = None,
              text: str | None = None, comment: str | None = None, out_path: str | None = None,
              force: bool = False) -> dict:
    """action: replace | insert | append | delete."""
    doc = load(path)
    r = doc.routine(program, routine)
    if r.get("Type") != "RLL":
        raise L5XError(f"Routine '{routine}' is {r.get('Type')}, not ladder (RLL)")
    content = r.find("RLLContent")
    if content is None:
        content = etree.SubElement(r, "RLLContent")
    rungs = content.findall("Rung")
    action = action.lower()

    validation = None
    if action != "delete":
        if text is None:
            raise L5XError("text is required for replace/insert/append")
        validation = validate_rung(text, doc.known_tag_names(program))
        if not validation["ok"]:
            raise L5XError(f"Rung validation failed: {validation['errors']}")
        if validation["warnings"] and not force:
            raise L5XError("Rung references unknown tags (create them first or pass force=true): "
                           + "; ".join(validation["warnings"]))

    def need_index() -> int:
        if number is None or not 0 <= number < len(rungs):
            raise L5XError(f"Rung number {number} out of range (0..{len(rungs) - 1})")
        return number

    if action == "delete":
        content.remove(rungs[need_index()])
    elif action == "replace":
        rung = rungs[need_index()]
        _set_cdata(rung, "Text", text)
        if comment is not None:
            if comment:
                _set_cdata(rung, "Comment", comment, before="Text")
            elif rung.find("Comment") is not None:
                rung.remove(rung.find("Comment"))
    elif action in ("insert", "append"):
        rung = etree.Element("Rung", Number="0", Type="N")
        if comment:
            _set_cdata(rung, "Comment", comment)
        _set_cdata(rung, "Text", text)
        if action == "append" or number is None or number >= len(rungs):
            content.append(rung)
        else:
            rungs[max(number, 0)].addprevious(rung)
    else:
        raise L5XError(f"Unknown action '{action}'")

    _renumber(content, "Rung")
    saved = doc.save(out_path)
    return {"saved": saved, "action": action, "total_rungs": len(content.findall("Rung")),
            "warnings": validation["warnings"] if validation else []}


def set_st_routine(path: str, program: str, routine: str, code: str, out_path: str | None = None) -> dict:
    doc = load(path)
    r = doc.routine(program, routine)
    if r.get("Type") != "ST":
        raise L5XError(f"Routine '{routine}' is {r.get('Type')}, not structured text")
    content = r.find("STContent")
    if content is not None:
        r.remove(content)
    content = etree.SubElement(r, "STContent")
    lines = code.splitlines() or [""]
    for i, line in enumerate(lines):
        el = etree.SubElement(content, "Line", Number=str(i))
        el.text = etree.CDATA(line)
    return {"saved": doc.save(out_path), "total_lines": len(lines)}


def add_routine(path: str, program: str, name: str, routine_type: str = "RLL",
                description: str | None = None, out_path: str | None = None) -> dict:
    routine_type = routine_type.upper()
    if routine_type not in ("RLL", "ST"):
        raise L5XError("Only RLL and ST routines can be created")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", name):
        raise L5XError(f"Invalid routine name '{name}'")
    doc = load(path)
    prog = doc.program(program)
    routines = prog.find("Routines")
    if routines is None:
        routines = etree.SubElement(prog, "Routines")
    if any(r.get("Name", "").lower() == name.lower() for r in routines.iterfind("Routine")):
        raise L5XError(f"Routine '{name}' already exists in '{program}'")
    r = etree.SubElement(routines, "Routine", Name=name, Type=routine_type)
    if description:
        _set_cdata(r, "Description", description)
    if routine_type == "RLL":
        rll = etree.SubElement(r, "RLLContent")
        rung = etree.SubElement(rll, "Rung", Number="0", Type="N")
        _set_cdata(rung, "Text", "NOP();")
    else:
        st = etree.SubElement(r, "STContent")
        line = etree.SubElement(st, "Line", Number="0")
        line.text = etree.CDATA("")
    return {"saved": doc.save(out_path), "routine": name, "type": routine_type,
            "note": "Call it from the main routine with JSR(" + name + ",0); for it to execute."}


def add_tag(path: str, name: str, data_type: str, program: str | None = None,
            dimensions: str | None = None, description: str | None = None,
            initial_value: str | None = None, out_path: str | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", name):
        raise L5XError(f"Invalid tag name '{name}'")
    doc = load(path)
    if name.lower() in {t.get("Name", "").lower() for t in doc.tags_container(program).iterfind("Tag")}:
        raise L5XError(f"Tag '{name}' already exists in {'program ' + program if program else 'controller scope'}")
    dt = data_type.upper() if data_type.upper() in ATOMIC_TYPES else data_type
    tag = etree.SubElement(doc.tags_container(program), "Tag", Name=name, TagType="Base", DataType=dt)
    if dimensions:
        tag.set("Dimensions", dimensions)
    if dt in ATOMIC_TYPES:
        tag.set("Radix", "Float" if dt in ("REAL", "LREAL") else "Decimal")
    tag.set("Constant", "false")
    tag.set("ExternalAccess", "Read/Write")
    if description:
        _set_cdata(tag, "Description", description)
    if dt in ATOMIC_TYPES and not dimensions:
        value = initial_value if initial_value is not None else ("0.0" if dt in ("REAL", "LREAL") else "0")
        data = etree.SubElement(tag, "Data", Format="Decorated")
        etree.SubElement(data, "DataValue", DataType=dt, Radix=tag.get("Radix"), Value=str(value))
    return {"saved": doc.save(out_path), "tag": name, "data_type": dt,
            "scope": f"Program:{program}" if program else "Controller"}


def set_tag_value(path: str, name: str, value: str, program: str | None = None,
                  out_path: str | None = None) -> dict:
    """Set the stored value of an atomic base tag or one element of a 1-D atomic array.

    `name` is 'Tag' or 'Tag[3]'. Updates both the L5K and Decorated data so they stay consistent.
    """
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", name.strip())
    if not m:
        raise L5XError(f"Unsupported tag reference '{name}' (use Tag or Tag[n])")
    base, idx = m.group(1), m.group(2)
    doc = load(path)
    tag = next((t for t in doc.tags_container(program).iterfind("Tag")
                if t.get("Name", "").lower() == base.lower()), None)
    if tag is None:
        raise L5XError(f"Tag '{base}' not found")
    dt = tag.get("DataType", "")
    if dt not in ATOMIC_TYPES or tag.get("TagType") != "Base":
        raise L5XError(f"'{base}' is {tag.get('TagType')} {dt}; only atomic base tags are supported")
    dims = tag.get("Dimensions")
    if bool(dims) != (idx is not None):
        raise L5XError(f"'{base}' {'is an array; give an index' if dims else 'is not an array'}")
    if dims and (" " in dims.strip() or not int(idx) < int(dims)):
        raise L5XError(f"Index {idx} invalid for dimensions '{dims}' (1-D arrays only)")
    if dt == "BOOL":
        value = {"true": "1", "false": "0"}.get(str(value).lower(), str(value))
    float(value)  # raises ValueError on non-numeric input

    old = None
    for data in tag.iterfind("Data"):
        fmt = data.get("Format")
        if fmt == "L5K":
            raw = (data.text or "").strip()
            if idx is None:
                old = old or raw
                data.text = etree.CDATA(str(value))
            else:
                items = [x.strip() for x in raw.strip("[]").replace("\n", "").split(",")]
                if len(items) != int(dims):
                    raise L5XError(f"L5K data of '{base}' has {len(items)} items, expected {dims}")
                old = old or items[int(idx)]
                items[int(idx)] = str(value)
                data.text = etree.CDATA("[" + ",".join(items) + "]")
        elif fmt == "Decorated":
            el = data.find("DataValue") if idx is None else \
                data.find(f"Array/Element[@Index='[{idx}]']")
            if el is None:
                raise L5XError(f"Decorated data for '{name}' not found")
            old = old or el.get("Value")
            el.set("Value", str(value))
    if old is None:
        raise L5XError(f"Tag '{base}' has no stored data")
    return {"saved": doc.save(out_path), "tag": name, "old": old, "new": str(value)}


# Controller catalogs that share the 5580/5380 firmware family (ProductType 14). Used to retarget a
# project for Logix Echo testing (Echo ships 1756-L8x firmware for v35) and back again.
CONTROLLERS = {
    "1756-L81E": (164, "ICP", "10"), "1756-L82E": (165, "ICP", "10"), "1756-L83E": (166, "ICP", "10"),
    "1756-L84E": (167, "ICP", "10"), "1756-L85E": (168, "ICP", "10"),
    "5069-L310ER": (188, "5069", "32"), "5069-L320ER": (189, "5069", "32"), "5069-L330ER": (190, "5069", "32"),
    "5069-L310ERM": (191, "5069", "32"), "5069-L320ERM": (192, "5069", "32"), "5069-L330ERM": (193, "5069", "32"),
    "5069-L340ERM": (194, "5069", "32"), "5069-L350ERM": (195, "5069", "32"),
}


def set_controller_type(path: str, catalog: str, out_path: str | None = None) -> dict:
    """Change the controller catalog (e.g. 5069-L330ERM <-> 1756-L81E) in a full-project L5X.

    Rewrites ProcessorType, the Local module's catalog/product code and its backplane port. The
    firmware revision and all logic, tags and I/O modules are kept. Only the Local module changes,
    so converting back restores the original controller definition.
    """
    if catalog not in CONTROLLERS:
        raise L5XError(f"Unsupported controller '{catalog}'. Known: {', '.join(sorted(CONTROLLERS))}")
    code, port_type, bus = CONTROLLERS[catalog]
    doc = load(path)
    c = doc.controller
    old = c.get("ProcessorType")
    local = c.find("Modules/Module[@Name='Local']")
    if local is None:
        raise L5XError("Local module not found")
    c.set("ProcessorType", catalog)
    local.set("CatalogNumber", catalog)
    local.set("ProductCode", str(code))
    bp = local.find("Ports/Port[@Id='1']")
    if bp is not None:
        bp.set("Type", port_type)
        b = bp.find("Bus")
        if b is not None:
            b.set("Size", bus)
    # 5069-only controller attribute; 1756 controllers reject it on import.
    if catalog.startswith("1756"):
        c.attrib.pop("EtherNetIPMode", None)
    elif old and old.startswith("1756") and c.get("EtherNetIPMode") is None:
        c.set("EtherNetIPMode", "A1/A2: Linear/DLR")
    return {"saved": doc.save(out_path), "from": old, "to": catalog}


def clone_module(path: str, template: str, name: str, address: str, out_path: str | None = None,
                 **attrs: str) -> dict:
    """Add an Ethernet module by copying an existing one (same schema), with a new name/IP.

    Extra keyword arguments override Module attributes (e.g. Vendor, ProductCode) or, with a
    `conn_` prefix, attributes of its first Connection (e.g. conn_InputSize='64').
    Comments and stored I/O data are dropped from the copy.
    """
    import copy as _copy
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", name):
        raise L5XError(f"Invalid module name '{name}'")
    doc = load(path)
    mods = doc.controller.find("Modules")
    if any(m.get("Name", "").lower() == name.lower() for m in mods.iterfind("Module")):
        raise L5XError(f"Module '{name}' already exists")
    src = mods.find(f"Module[@Name='{template}']")
    if src is None:
        raise L5XError(f"Template module '{template}' not found")
    m = _copy.deepcopy(src)
    m.set("Name", name)
    for k, v in attrs.items():
        if not k.startswith("conn_"):
            m.set(k, str(v))
    port = m.find("Ports/Port[@Type='Ethernet']")
    if port is None:
        raise L5XError(f"Template '{template}' has no Ethernet port")
    port.set("Address", address)
    for c in list(m.iter("Comments")):
        c.getparent().remove(c)
    conn = m.find("Communications/Connections/Connection")
    if conn is not None:
        for k, v in attrs.items():
            if k.startswith("conn_"):
                conn.set(k[5:], str(v))
        for tag in conn:  # sizes may differ from the template: let Logix rebuild default data
            for d in list(tag.iterfind("Data")):
                tag.remove(d)
    src.addnext(m)
    return {"saved": doc.save(out_path), "module": name, "address": address, "template": template}


def delete_aoi(path: str, name: str, out_path: str | None = None) -> dict:
    """Delete an Add-On Instruction definition. Refuses if any tag or routine still uses it."""
    doc = load(path)
    defs = doc.controller.find("AddOnInstructionDefinitions")
    aoi = next((a for a in defs.iterfind("AddOnInstructionDefinition") if a.get("Name") == name), None) \
        if defs is not None else None
    if aoi is None:
        raise L5XError(f"AOI '{name}' not found")
    if doc.root.xpath(f".//Tag[@DataType='{name}']|.//LocalTag[@DataType='{name}']|.//Parameter[@DataType='{name}']"):
        raise L5XError(f"AOI '{name}' is still used by tags")
    rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"\(")
    for el in doc.root.iter("Text", "Line"):
        if el.getparent() is not None and aoi in el.iterancestors():
            continue
        if rx.search(el.text or ""):
            raise L5XError(f"AOI '{name}' is still called from logic")
    defs.remove(aoi)
    return {"saved": doc.save(out_path), "deleted_aoi": name}


def delete_tag(path: str, name: str, program: str | None = None, out_path: str | None = None) -> dict:
    doc = load(path)
    container = doc.tags_container(program)
    for t in container.iterfind("Tag"):
        if t.get("Name", "").lower() == name.lower():
            container.remove(t)
            return {"saved": doc.save(out_path), "deleted": name}
    raise L5XError(f"Tag '{name}' not found")
