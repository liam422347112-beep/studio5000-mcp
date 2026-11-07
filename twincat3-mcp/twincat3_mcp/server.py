"""MCP server: TwinCAT 3 offline PLC edit + ADS online read/write.

Offline: .tsproj / .plcproj / .TcPOU / .TcDUT / .TcGVL
Online:  pyads against local simulation (127.0.0.1.1.1:851) or remote (gated writes)
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import ads_client, project, tcxml

mcp = FastMCP("twincat3")


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


def _err(e: Exception) -> str:
    return _j({"error": type(e).__name__, "message": str(e)})


# ======================= Offline project =======================
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


# ======================= ADS online =======================
@mcp.tool()
def ads_info(netid: str | None = None, port: int | None = None) -> str:
    """Probe ADS connectivity for local simulation or a remote target.

    Defaults: NetId 127.0.0.1.1.1 (or env TWINCAT_AMS_NETID), port 851 (TWINCAT_AMS_PORT).
    Reports system port 10000 and PLC port status. If PLC port missing, returns Activate/Run hint.
    """
    try:
        return _j(ads_client.probe(netid, port))
    except Exception as e:
        return _err(e)


@mcp.tool()
def ads_read(symbols: list[str], netid: str | None = None, port: int | None = None) -> str:
    """Read PLC symbols by name over ADS (e.g. ['GVL_Program.bFlag', 'MAIN.nCnt'])."""
    try:
        return _j({"netid": ads_client.resolve_netid(netid), "port": ads_client.resolve_port(port),
                   "results": ads_client.read_symbols(symbols, netid, port)})
    except Exception as e:
        return _err(e)


@mcp.tool()
def ads_write(values: dict[str, Any], netid: str | None = None, port: int | None = None) -> str:
    """Write PLC symbols by name over ADS. Local NetId writes allowed; remote needs TWINCAT_ADS_ALLOW_REMOTE_WRITE=1.

    Example values: {"GVL_Program.bFlag": true, "MAIN.nCnt": 1}
    """
    try:
        return _j({"netid": ads_client.resolve_netid(netid), "port": ads_client.resolve_port(port),
                   "results": ads_client.write_symbols(values, netid, port)})
    except Exception as e:
        return _err(e)


@mcp.tool()
def ads_list_symbols(netid: str | None = None, port: int | None = None,
                     name_filter: str | None = None, limit: int = 300) -> str:
    """List symbol names from the connected PLC (optional name_filter substring). Requires PLC Run on target port."""
    try:
        return _j(ads_client.list_symbols(netid, port, name_filter=name_filter, limit=limit))
    except Exception as e:
        return _err(e)


@mcp.tool()
def ads_symbol_info(name: str, netid: str | None = None, port: int | None = None) -> str:
    """Get ADS symbol metadata for one name (type/comment/index when available)."""
    try:
        return _j(ads_client.get_symbol_info(name, netid, port))
    except Exception as e:
        return _err(e)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
