"""MCP server: TwinCAT 3 offline PLC project inspect / edit.

v0 focuses on filesystem TwinCAT XML objects (.tsproj / .plcproj / .TcPOU / .TcDUT / .TcGVL).
ADS online read/write is reserved for a later optional extra (`pip install twincat3-mcp[ads]`).
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import project, tcxml

mcp = FastMCP("twincat3")


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


def _err(e: Exception) -> str:
    return _j({"error": type(e).__name__, "message": str(e)})


@mcp.tool()
def tc_project_summary(path: str) -> str:
    """Summarize a TwinCAT solution or PLC project: .tsproj path, PLC projects, object counts.

    `path` may be a .tsproj, a .plcproj, or a folder containing them.
    """
    try:
        return _j(project.summary(path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_list_objects(path: str, kind: str | None = None, name_filter: str | None = None) -> str:
    """List TwinCAT compile objects from a .tsproj / .plcproj / folder.

    kind: POU | DUT | GVL (optional). name_filter matches object name or relative path.
    """
    try:
        return _j(project.list_objects(path, kind=kind, name_filter=name_filter))
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_get_object(path: str) -> str:
    """Read a .TcPOU / .TcDUT / .TcGVL: name, declaration ST, implementation ST (if any)."""
    try:
        return _j(tcxml.get_object(path))
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_backup(path: str) -> str:
    """Create a timestamped .bak copy next to a TwinCAT object or project file before editing."""
    try:
        return _j({"path": path, "backup": tcxml.backup(path)})
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_set_declaration(path: str, code: str, make_backup: bool = True) -> str:
    """Replace the Declaration CDATA of a TwinCAT object. Creates a timestamped backup by default.

    Do not reformat unrelated XML. Pass the full declaration text including TYPE/PROGRAM/FUNCTION_BLOCK header.
    """
    try:
        return _j(tcxml.set_declaration(path, code, make_backup=make_backup))
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_set_implementation(path: str, code: str, make_backup: bool = True) -> str:
    """Replace Implementation/ST CDATA of a .TcPOU (or create ST node if missing). Backup by default."""
    try:
        return _j(tcxml.set_implementation(path, code, make_backup=make_backup))
    except Exception as e:
        return _err(e)


@mcp.tool()
def tc_search(path: str, pattern: str, kind: str | None = None, limit: int = 200) -> str:
    """Regex search across TwinCAT object declaration/implementation text under a project path."""
    try:
        return _j(project.search_project(path, pattern, kind=kind, limit=limit))
    except Exception as e:
        return _err(e)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
