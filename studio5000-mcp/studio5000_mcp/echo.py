"""Online access to a FactoryTalk Logix Echo emulated controller over EtherNet/IP (pylogix).

Writes are refused unless the target identifies itself as an Echo emulator
("Emulate" in the CIP product name). Set STUDIO5000_MCP_ALLOW_REAL_PLC=1 to lift that guard.
"""
from __future__ import annotations

import os
import time

from pylogix import PLC

ECHO_IP = os.environ.get("ECHO_IP", "127.0.0.1")
ECHO_SLOT = int(os.environ.get("ECHO_SLOT", "0"))
ALLOW_REAL_PLC = os.environ.get("STUDIO5000_MCP_ALLOW_REAL_PLC") == "1"


class EchoError(Exception):
    pass


def _plc(ip: str | None, slot: int | None) -> PLC:
    c = PLC(ip or ECHO_IP, ECHO_SLOT if slot is None else slot)
    c.SocketTimeout = 5.0
    return c


def info(ip: str | None = None, slot: int | None = None) -> dict:
    with _plc(ip, slot) as c:
        r = c.GetDeviceProperties()
        if r.Status != "Success":
            raise EchoError(f"No controller at {c.IPAddress} slot {c.ProcessorSlot}: {r.Status}")
        p = r.Value
        t = c.GetPLCTime()
        return {"ip": c.IPAddress, "slot": c.ProcessorSlot, "product": p.ProductName,
                "revision": p.Revision, "serial": p.SerialNumber, "status_word": p.Status,
                "is_emulator": "emulate" in (p.ProductName or "").lower(),
                "controller_time": str(t.Value) if t.Status == "Success" else None}


def _assert_emulator(c: PLC) -> None:
    if ALLOW_REAL_PLC:
        return
    p = c.GetDeviceProperties()
    name = (p.Value.ProductName if p.Status == "Success" else "") or ""
    if "emulate" not in name.lower():
        raise EchoError(f"Refusing to write: target '{name or 'unknown'}' is not a Logix Echo emulator. "
                        "Set STUDIO5000_MCP_ALLOW_REAL_PLC=1 to override.")


def list_programs(ip: str | None = None, slot: int | None = None) -> list[str]:
    with _plc(ip, slot) as c:
        r = c.GetProgramsList()
        if r.Status != "Success":
            raise EchoError(r.Status)
        return r.Value


def list_tags(program: str | None = None, name_filter: str | None = None, ip: str | None = None,
              slot: int | None = None, limit: int = 500) -> list[dict]:
    with _plc(ip, slot) as c:
        if program:
            prog = program if program.startswith("Program:") else f"Program:{program}"
            r = c.GetProgramTagList(prog)
        else:
            r = c.GetTagList(False)
        if r.Status != "Success":
            raise EchoError(r.Status)
        nf = (name_filter or "").lower()
        tags = [{"name": t.TagName, "data_type": t.DataType, "array": bool(t.Array),
                 "struct": bool(t.Struct), "size": t.Size}
                for t in r.Value if nf in t.TagName.lower()]
        return tags[:limit]


def read(tags: list[str], ip: str | None = None, slot: int | None = None) -> list[dict]:
    with _plc(ip, slot) as c:
        res = c.Read(list(tags))
        res = res if isinstance(res, list) else [res]
        return [{"tag": r.TagName, "value": r.Value, "status": r.Status} for r in res]


def _coerce(value):
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "false"):
            return low == "true"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value


def write(values: dict, ip: str | None = None, slot: int | None = None) -> list[dict]:
    with _plc(ip, slot) as c:
        _assert_emulator(c)
        res = c.Write([(k, _coerce(v)) for k, v in values.items()])
        res = res if isinstance(res, list) else [res]
        return [{"tag": r.TagName, "value": r.Value, "status": r.Status} for r in res]


def _matches(actual, op: str, expected) -> bool:
    expected = _coerce(expected)
    if isinstance(actual, bool) or isinstance(expected, bool):
        actual, expected = bool(actual), bool(expected)
    ops = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">": lambda a, b: a > b,
           ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b}
    if op == "~=":
        return abs(float(actual) - float(expected)) <= 1e-3 * max(1.0, abs(float(expected)))
    if op not in ops:
        raise EchoError(f"Unknown operator '{op}'")
    try:
        return ops[op](actual, expected)
    except TypeError:
        return False


def run_test(steps: list[dict], ip: str | None = None, slot: int | None = None,
             poll_ms: int = 50) -> dict:
    """Execute a test sequence against the running emulator.

    Step forms:
      {"write": {"Tag": value, ...}}
      {"wait_ms": 500}
      {"expect": {"tag": "X", "op": "==", "value": 1, "timeout_ms": 2000}}
          (polls until true or timeout; op in == != > >= < <= ~=)
      {"read": ["TagA", "TagB"]}
    """
    log, passed, failed = [], 0, 0
    with _plc(ip, slot) as c:
        if any("write" in s for s in steps):
            _assert_emulator(c)
        for i, step in enumerate(steps):
            if "write" in step:
                res = c.Write([(k, _coerce(v)) for k, v in step["write"].items()])
                res = res if isinstance(res, list) else [res]
                bad = [r.TagName for r in res if r.Status != "Success"]
                log.append({"step": i, "write": step["write"], "ok": not bad,
                            **({"errors": [f"{r.TagName}: {r.Status}" for r in res if r.Status != "Success"]} if bad else {})})
                if bad:
                    failed += 1
            elif "wait_ms" in step:
                time.sleep(step["wait_ms"] / 1000)
                log.append({"step": i, "wait_ms": step["wait_ms"]})
            elif "read" in step:
                res = c.Read(list(step["read"]))
                res = res if isinstance(res, list) else [res]
                log.append({"step": i, "read": {r.TagName: (r.Value if r.Status == "Success" else r.Status) for r in res}})
            elif "expect" in step:
                e = step["expect"]
                op, timeout = e.get("op", "=="), e.get("timeout_ms", 1000) / 1000
                deadline = time.monotonic() + timeout
                t0 = time.monotonic()
                while True:
                    r = c.Read(e["tag"])
                    ok = r.Status == "Success" and _matches(r.Value, op, e["value"])
                    if ok or time.monotonic() >= deadline:
                        break
                    time.sleep(poll_ms / 1000)
                entry = {"step": i, "expect": f"{e['tag']} {op} {e['value']}", "actual": r.Value,
                         "status": r.Status, "pass": ok, "elapsed_ms": round((time.monotonic() - t0) * 1000)}
                log.append(entry)
                passed += ok
                failed += not ok
                if not ok and step.get("stop_on_fail", True):
                    log.append({"aborted_after_step": i})
                    break
            else:
                raise EchoError(f"Step {i} has no recognised action: {step}")
    return {"passed": passed, "failed": failed, "success": failed == 0, "log": log}
