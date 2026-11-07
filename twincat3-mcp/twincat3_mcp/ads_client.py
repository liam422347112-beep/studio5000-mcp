"""TwinCAT ADS online helpers (pyads).

Defaults target local runtime simulation:
  AMS NetId 127.0.0.1.1.1 , port 851 (TC3 PLC1)

Writes to non-local targets require TWINCAT_ADS_ALLOW_REMOTE_WRITE=1.
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator

LOCAL_NETID_DEFAULT = "127.0.0.1.1.1"
LOCAL_PORT_DEFAULT = 851  # PORT_TC3PLC1
SYSTEM_PORT = 10000

_LOCAL_NETID_RE = re.compile(r"^127\.0\.0\.1\.\d+\.\d+$")


def _pyads():
    try:
        import pyads  # type: ignore
    except ImportError as e:
        raise ImportError(
            "pyads is required for ADS tools. Install with: pip install 'twincat3-mcp[ads]' or pip install pyads"
        ) from e
    return pyads


def resolve_netid(netid: str | None = None) -> str:
    return (netid or os.environ.get("TWINCAT_AMS_NETID") or LOCAL_NETID_DEFAULT).strip()


def resolve_port(port: int | None = None) -> int:
    if port is not None:
        return int(port)
    env = os.environ.get("TWINCAT_AMS_PORT")
    return int(env) if env else LOCAL_PORT_DEFAULT


def is_local_netid(netid: str) -> bool:
    return bool(_LOCAL_NETID_RE.match(netid.strip()))


def assert_write_allowed(netid: str) -> None:
    if is_local_netid(netid):
        return
    if os.environ.get("TWINCAT_ADS_ALLOW_REMOTE_WRITE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}:
        return
    raise PermissionError(
        "ADS write to non-local NetId blocked. Set TWINCAT_ADS_ALLOW_REMOTE_WRITE=1 after explicit user approval."
    )


@contextmanager
def connection(netid: str | None = None, port: int | None = None) -> Iterator[Any]:
    pyads = _pyads()
    nid = resolve_netid(netid)
    prt = resolve_port(port)
    plc = pyads.Connection(nid, prt)
    plc.open()
    try:
        yield plc
    finally:
        try:
            plc.close()
        except Exception:
            pass


def probe(netid: str | None = None, port: int | None = None) -> dict:
    """Probe local/system + PLC ports and return connection diagnostics."""
    pyads = _pyads()
    nid = resolve_netid(netid)
    prt = resolve_port(port)
    out: dict[str, Any] = {
        "netid": nid,
        "plc_port": prt,
        "local": is_local_netid(nid),
        "pyads_version": getattr(pyads, "__version__", None),
        "system": None,
        "plc": None,
        "hint": None,
    }

    # System service (always useful on local)
    try:
        with connection(nid, SYSTEM_PORT) as sys_plc:
            st = sys_plc.read_state()
            out["system"] = {"port": SYSTEM_PORT, "ads_state": st[0], "device_state": st[1], "ok": True}
    except Exception as e:
        out["system"] = {"port": SYSTEM_PORT, "ok": False, "error": str(e)}

    try:
        with connection(nid, prt) as plc:
            st = plc.read_state()
            out["plc"] = {"port": prt, "ads_state": st[0], "device_state": st[1], "ok": True}
            # AdsState names if available
            try:
                out["plc"]["ads_state_name"] = str(pyads.ADSState(st[0])).split(".")[-1]
            except Exception:
                pass
    except Exception as e:
        out["plc"] = {"port": prt, "ok": False, "error": str(e)}
        if "Target port not found" in str(e) or "(6)" in str(e):
            out["hint"] = (
                "ADS router is up but PLC port is not running. "
                "In TwinCAT XAE: select <Local> target → Activate Configuration → set Run mode. "
                "Then retry ads_info / ads_read."
            )
    return out


def read_symbols(names: list[str], netid: str | None = None, port: int | None = None) -> list[dict]:
    results: list[dict] = []
    with connection(netid, port) as plc:
        for name in names:
            try:
                val = plc.read_by_name(name)
                results.append({"symbol": name, "value": val, "ok": True})
            except Exception as e:
                results.append({"symbol": name, "ok": False, "error": str(e)})
    return results


def write_symbols(values: dict[str, Any], netid: str | None = None, port: int | None = None) -> list[dict]:
    nid = resolve_netid(netid)
    assert_write_allowed(nid)
    results: list[dict] = []
    with connection(nid, port) as plc:
        for name, value in values.items():
            try:
                plc.write_by_name(name, value)
                # read-back for confirmation when possible
                try:
                    rb = plc.read_by_name(name)
                except Exception:
                    rb = None
                results.append({"symbol": name, "written": value, "readback": rb, "ok": True})
            except Exception as e:
                results.append({"symbol": name, "written": value, "ok": False, "error": str(e)})
    return results


def list_symbols(netid: str | None = None, port: int | None = None, name_filter: str | None = None, limit: int = 300) -> dict:
    with connection(netid, port) as plc:
        syms = plc.get_all_symbols()
        rows = []
        nf = name_filter.lower() if name_filter else None
        for s in syms:
            name = getattr(s, "name", str(s))
            if nf and nf not in name.lower():
                continue
            rows.append(
                {
                    "name": name,
                    "symbol_type": getattr(s, "symbol_type", None),
                    "comment": getattr(s, "comment", None),
                }
            )
            if len(rows) >= limit:
                break
        return {"count_returned": len(rows), "total_available": len(syms), "symbols": rows}


def get_symbol_info(name: str, netid: str | None = None, port: int | None = None) -> dict:
    with connection(netid, port) as plc:
        # Prefer Connection.get_symbol when available
        if hasattr(plc, "get_symbol"):
            sym = plc.get_symbol(name)
            return {
                "name": getattr(sym, "name", name),
                "symbol_type": getattr(sym, "symbol_type", None),
                "comment": getattr(sym, "comment", None),
                "index_group": getattr(sym, "index_group", None),
                "index_offset": getattr(sym, "index_offset", None),
            }
        info = plc.read_symbol_info(name) if hasattr(plc, "read_symbol_info") else None
        return {"name": name, "info": str(info)}
