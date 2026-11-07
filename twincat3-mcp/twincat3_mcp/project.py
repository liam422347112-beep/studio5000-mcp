"""TwinCAT solution / PLC project discovery."""
from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from . import tcxml

_MSBUILD_NS = {"msb": "http://schemas.microsoft.com/developer/msbuild/2003"}


def _find_tsproj(path: Path) -> Path | None:
    if path.is_file() and path.suffix.lower() == ".tsproj":
        return path
    if path.is_dir():
        hits = sorted(path.glob("*.tsproj")) + sorted(path.rglob("*.tsproj"))
        return hits[0] if hits else None
    return None


def _find_plcproj(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".plcproj":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.plcproj"))
    return []


def plcproj_compiles(plcproj: Path) -> list[dict]:
    tree = etree.parse(str(plcproj))
    root = tree.getroot()
    # With or without default xmlns
    items = root.findall(".//msb:Compile", _MSBUILD_NS)
    if not items:
        items = root.findall(".//{http://schemas.microsoft.com/developer/msbuild/2003}Compile")
    if not items:
        items = root.findall(".//Compile")
    out: list[dict] = []
    base = plcproj.parent
    for it in items:
        rel = it.get("Include") or ""
        if not rel:
            continue
        full = (base / rel).resolve()
        kind = tcxml.object_kind(full) or Path(rel).suffix.lstrip(".").upper()
        out.append({"include": rel.replace("\\", "/"), "path": str(full), "kind": kind, "exists": full.is_file()})
    return out


def tsproj_plc_projects(tsproj: Path) -> list[dict]:
    # TwinCAT tsproj is large / not always strict XML-friendly; regex PrjFilePath
    text = tsproj.read_text(encoding="utf-8", errors="replace")
    found: list[dict] = []
    for m in re.finditer(
        r'Name="([^"]+)"[^>]*PrjFilePath="([^"]+\.plcproj)"|PrjFilePath="([^"]+\.plcproj)"[^>]*Name="([^"]+)"',
        text,
        re.I,
    ):
        if m.group(1) and m.group(2):
            name, rel = m.group(1), m.group(2)
        else:
            rel, name = m.group(3), m.group(4)
        full = (tsproj.parent / rel.replace("\\", "/")).resolve()
        found.append({"name": name, "prj_file": rel.replace("\\", "/"), "path": str(full), "exists": full.is_file()})
    # de-dupe by path
    seen: set[str] = set()
    uniq: list[dict] = []
    for f in found:
        if f["path"] in seen:
            continue
        seen.add(f["path"])
        uniq.append(f)
    return uniq


def summary(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    ts = _find_tsproj(p)
    plc_list = _find_plcproj(p if p.is_dir() else p.parent)
    if ts:
        from_ts = tsproj_plc_projects(ts)
        # merge
        by = {x["path"]: x for x in from_ts}
        for pl in plc_list:
            by.setdefault(str(pl.resolve()), {"name": pl.stem, "prj_file": pl.name, "path": str(pl.resolve()), "exists": True})
        plc_projects = list(by.values())
    else:
        plc_projects = [
            {"name": pl.stem, "prj_file": pl.name, "path": str(pl.resolve()), "exists": True} for pl in plc_list
        ]

    objects: list[dict] = []
    counts = {"POU": 0, "DUT": 0, "GVL": 0, "other": 0}
    for pl in plc_projects:
        if not pl.get("exists"):
            continue
        for c in plcproj_compiles(Path(pl["path"])):
            objects.append({**c, "plc": pl["name"]})
            k = c["kind"]
            if k in counts:
                counts[k] += 1
            else:
                counts["other"] += 1

    return {
        "root": str(p.resolve()),
        "tsproj": str(ts.resolve()) if ts else None,
        "plc_projects": plc_projects,
        "object_counts": counts,
        "object_total": len(objects),
    }


def list_objects(path: str | Path, kind: str | None = None, name_filter: str | None = None) -> list[dict]:
    p = Path(path)
    plc_paths: list[Path] = []
    if p.suffix.lower() == ".plcproj":
        plc_paths = [p]
    elif p.suffix.lower() == ".tsproj":
        plc_paths = [Path(x["path"]) for x in tsproj_plc_projects(p) if x.get("exists")]
    else:
        s = summary(p)
        plc_paths = [Path(x["path"]) for x in s["plc_projects"] if x.get("exists")]

    kind_u = kind.upper() if kind else None
    nf = name_filter.lower() if name_filter else None
    out: list[dict] = []
    for pl in plc_paths:
        for c in plcproj_compiles(pl):
            if kind_u and c["kind"].upper() != kind_u:
                continue
            name = Path(c["include"]).stem
            if nf and nf not in name.lower() and nf not in c["include"].lower():
                continue
            out.append({**c, "name": name, "plcproj": str(pl)})
    if nf:
        # Prefer exact stem match, then prefix, then substring
        def _rank(o: dict) -> tuple[int, str]:
            n = o["name"].lower()
            if n == nf:
                return (0, n)
            if n.startswith(nf):
                return (1, n)
            return (2, n)

        out.sort(key=_rank)
    return out


def search_project(path: str | Path, pattern: str, kind: str | None = None, limit: int = 200) -> list[dict]:
    objs = list_objects(path, kind=kind)
    hits: list[dict] = []
    for o in objs:
        if not o.get("exists"):
            continue
        for h in tcxml.search_in_object(o["path"], pattern):
            hits.append({"object": o["name"], "path": o["path"], "kind": o["kind"], **h})
            if len(hits) >= limit:
                return hits
    return hits
