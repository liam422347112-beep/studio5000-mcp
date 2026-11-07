"""TwinCAT TcPlcObject (.TcPOU / .TcDUT / .TcGVL) helpers.

Preserve XML/CDATA structure; never pretty-print the whole document.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

from lxml import etree

OBJECT_EXTS = {".tcpou": "POU", ".tcdut": "DUT", ".tcgvl": "GVL", ".tcio": "IO"}


def _parse(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
    return etree.parse(str(path), parser)


def backup(path: str | Path) -> str:
    p = Path(path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = p.with_name(f"{p.stem}_{stamp}{p.suffix}.bak")
    shutil.copy2(p, dest)
    return str(dest)


def object_kind(path: str | Path) -> str | None:
    return OBJECT_EXTS.get(Path(path).suffix.lower())


def get_object(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    tree = _parse(p)
    root = tree.getroot()
    kind = object_kind(p) or "Unknown"
    # Child element is POU / DUT / GVL / ...
    obj = None
    for child in root:
        if isinstance(child.tag, str) and not child.tag.startswith("{"):
            obj = child
            break
        if isinstance(child.tag, str):
            obj = child
            break
    if obj is None:
        raise ValueError(f"No TwinCAT object node in {p}")

    decl = obj.find("Declaration")
    impl_st = obj.find("Implementation/ST")
    # Some objects only have Declaration (DUT/GVL)
    declaration = (decl.text or "") if decl is not None else ""
    implementation = (impl_st.text or "") if impl_st is not None else None

    return {
        "path": str(p.resolve()),
        "kind": kind,
        "name": obj.get("Name"),
        "id": obj.get("Id"),
        "product_version": root.get("ProductVersion"),
        "tcplc_version": root.get("Version"),
        "declaration": declaration,
        "implementation": implementation,
        "has_implementation": impl_st is not None,
    }


def _set_cdata_text(el: etree._Element, text: str) -> None:
    # Keep as text; lxml serializes CDATA sections if we wrap properly via CDATA
    el.text = etree.CDATA(text if text is not None else "")


def set_declaration(path: str | Path, code: str, *, make_backup: bool = True) -> dict:
    p = Path(path)
    bak = backup(p) if make_backup else None
    tree = _parse(p)
    root = tree.getroot()
    obj = next(c for c in root if isinstance(c.tag, str))
    decl = obj.find("Declaration")
    if decl is None:
        decl = etree.SubElement(obj, "Declaration")
    _set_cdata_text(decl, code)
    tree.write(str(p), xml_declaration=True, encoding="utf-8", standalone=None)
    # lxml may write encoding differently; normalize header is ok for TwinCAT
    return {"path": str(p.resolve()), "backup": bak, "section": "Declaration", "chars": len(code)}


def set_implementation(path: str | Path, code: str, *, make_backup: bool = True) -> dict:
    p = Path(path)
    bak = backup(p) if make_backup else None
    tree = _parse(p)
    root = tree.getroot()
    obj = next(c for c in root if isinstance(c.tag, str))
    impl = obj.find("Implementation")
    if impl is None:
        impl = etree.SubElement(obj, "Implementation")
    st = impl.find("ST")
    if st is None:
        st = etree.SubElement(impl, "ST")
    _set_cdata_text(st, code)
    tree.write(str(p), xml_declaration=True, encoding="utf-8", standalone=None)
    return {"path": str(p.resolve()), "backup": bak, "section": "Implementation/ST", "chars": len(code)}


def search_in_object(path: str | Path, pattern: str, ignore_case: bool = True) -> list[dict]:
    info = get_object(path)
    flags = re.I if ignore_case else 0
    rx = re.compile(pattern, flags)
    hits: list[dict] = []
    for section, text in (
        ("declaration", info.get("declaration") or ""),
        ("implementation", info.get("implementation") or ""),
    ):
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                hits.append({"section": section, "line": i, "text": line.rstrip()})
    return hits
