"""Client for the FactoryTalk Logix Echo service API (gRPC, localhost:46520).

This is the interface the Echo dashboard uses: list/create emulated controllers and download an
ACD to one. The download is executed by Echo itself through Logix Designer, so it works without
the Logix Designer SDK/COM automation licence.

The message/service schema (EchoServiceApi.pb) was recovered from the descriptor embedded in
RockwellAutomation.FactoryTalkLogixEcho.Api.dll (Echo 3.0.1130).
"""
from __future__ import annotations

import os
import shutil
import time
import urllib.parse
import uuid

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, json_format, message_factory

ECHO_API = os.environ.get("ECHO_API_ADDRESS", "127.0.0.1:46520")

_fd = descriptor_pb2.FileDescriptorProto()
with open(os.path.join(os.path.dirname(__file__), "EchoServiceApi.pb"), "rb") as f:
    _fd.ParseFromString(f.read())
_pool = descriptor_pool.DescriptorPool()
_file = _pool.Add(_fd)
_svc = _file.services_by_name["ServiceApi"]
_PKG = _fd.package

DONE, FAILED, IN_PROGRESS, CANCELED, IDLE = 0, 1, 2, 3, 4
_STATES = {DONE: "DONE", FAILED: "FAILED", IN_PROGRESS: "IN_PROGRESS", CANCELED: "CANCELED", IDLE: "NO_OPERATION"}


class EchoServiceError(Exception):
    pass


def _uuid_bytes(u: str | bytes) -> bytes:
    return u if isinstance(u, bytes) else uuid.UUID(u).bytes_le


def _uuid_str(b: bytes) -> str:
    return str(uuid.UUID(bytes_le=b)) if b else ""


def _grant(path: str, account: str) -> None:
    """Give `account` full control of path (and, for folders, everything created inside)."""
    import subprocess
    perm = "(OI)(CI)F" if os.path.isdir(path) else "F"
    r = subprocess.run(["icacls", path, "/grant", f"{account}:{perm}"], capture_output=True)
    if r.returncode != 0:
        msg = (r.stdout + r.stderr).decode("mbcs", "replace").strip()
        raise EchoServiceError(f"icacls failed on {path}: {msg}")


def _dict(msg) -> dict:
    return json_format.MessageToDict(msg, preserving_proto_field_name=True)


class EchoService:
    def __init__(self, address: str = ECHO_API, timeout: float = 30):
        self.timeout = timeout
        self.channel = grpc.insecure_channel(address)

    def _call(self, _rpc: str, timeout: float | None = None, **kw):
        m = _svc.methods_by_name[_rpc]
        req = message_factory.GetMessageClass(m.input_type)(**kw)
        out = message_factory.GetMessageClass(m.output_type)
        rpc = self.channel.unary_unary(f"/{_PKG}.ServiceApi/{_rpc}", request_serializer=lambda x: x.SerializeToString(),
                                       response_deserializer=out.FromString)
        try:
            return rpc(req, timeout=timeout or self.timeout)
        except grpc.RpcError as e:
            raise EchoServiceError(f"{_rpc}: {e.code().name} {e.details()}") from e

    # ----- queries -----
    def controllers(self) -> list[dict]:
        out = []
        for ch in _dict(self._call("ListChassis")).get("chassis_list", []):
            for slot in ch.get("slot_assignment_list", []):
                c = self._call("ReadController", uuid=__import__("base64").b64decode(slot["controller_uuid"])).controller
                out.append(self._summary(c))
        return out

    def find(self, name: str) -> dict:
        hits = [c for c in self.controllers() if c["name"].lower() == name.lower()]
        if not hits:
            raise EchoServiceError(f"No Echo controller named '{name}'. Available: "
                                   + ", ".join(c["name"] for c in self.controllers()))
        return hits[0]

    @staticmethod
    def _summary(c) -> dict:
        d = _dict(c)
        return {"name": c.name, "uuid": _uuid_str(c.controller_uuid), "slot": c.slot, "chassis": c.chassis_name,
                "firmware": f"{c.firmware_package_name} {c.firmware_package_version.major}."
                            f"{c.firmware_package_version.minor}",
                "project": c.loaded_project_name, "mode": d.get("mode", "HARD_RUN"),
                "run": c.is_in_run_mode, "faulted": c.is_faulted}

    # ----- snapshots (backup of a controller's project + state) -----
    def snapshot(self, controller: str, name: str, description: str = "") -> dict:
        target = self.find(controller)
        s = self._call("CreateSnapshot", timeout=600, controller_uuids=[_uuid_bytes(target["uuid"])],
                       name=name, description=description).snapshot
        return {"snapshot_uuid": _uuid_str(s.snapshot_uuid), "name": s.name, "controller": target["name"],
                "project": target["project"]}

    def snapshots(self) -> list[dict]:
        return [{"snapshot_uuid": _uuid_str(s.snapshot_uuid), "name": s.name, "description": s.description,
                 "timestamp_s": s.timestamp_s} for s in self._call("ListSnapshots").snapshot_list]

    def set_key_switch(self, controller: str, position: str, timeout: float = 30) -> dict:
        """Turn the emulated key switch: RUN | REMOTE | PROGRAM."""
        pos = {"RUN": 0, "REMOTE": 1, "PROGRAM": 2}[position.upper()]
        target = self.find(controller)
        c = self._call("ReadController", uuid=_uuid_bytes(target["uuid"])).controller
        c.key_switch_position = pos
        self._call("UpdateController", controller=c)
        end = time.time() + timeout
        while time.time() < end:
            s = self._summary(self._call("ReadController", uuid=_uuid_bytes(target["uuid"])).controller)
            if (pos == 2 and not s["run"]) or (pos == 0 and s["run"]) or pos == 1:
                return s
            time.sleep(0.5)
        raise EchoServiceError(f"Key switch did not reach {position} within {timeout:.0f}s")

    # ----- download -----
    def download(self, controller: str, acd_path: str, timeout: float = 900) -> dict:
        """Download an ACD to the named Echo controller and wait for the result."""
        acd_path = os.path.abspath(acd_path)
        if not os.path.isfile(acd_path):
            raise EchoServiceError(f"File not found: {acd_path}")
        target = self.find(controller)
        cu, session = _uuid_bytes(target["uuid"]), uuid.uuid4().bytes_le
        # The service account can only read its own shared storage; stage a copy there.
        # Same as the Echo dashboard's FileHandle: copy the ACD into <shared storage>/<guid>/, grant
        # the storage account and ourselves full control, and pass a file-exchange URI (a plain path
        # is rejected with "cannot access file").
        share = self._call("GetLocalSharedStorageParameters")
        guid = str(uuid.uuid4())
        folder = os.path.join(share.path, guid)
        os.mkdir(folder)  # Users may create folders here; as owner we can then open up the ACL
        name = os.path.basename(acd_path)
        try:
            _grant(folder, os.environ.get("USERNAME", ""))
            _grant(folder, share.username)
            shutil.copyfile(acd_path, os.path.join(folder, name))
            uri = f"x-ft-logix-echo-file-exchange:{guid}/{urllib.parse.quote(name, safe='')}"
            return self._wait_download(cu, session, uri, acd_path, timeout)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def _wait_download(self, cu: bytes, session: bytes, staged: str, acd_path: str, timeout: float) -> dict:
        self._call("Download", controller_uuid=cu, session_uuid=session, path=staged)
        end, fb = time.time() + timeout, {}
        while time.time() < end:
            fb = self._call("GetDownloadFeedback", controller_uuid=cu, session_uuid=session).feedback
            if fb.state in (DONE, FAILED, CANCELED):
                break
            time.sleep(1)
        else:
            raise EchoServiceError(f"Download did not finish within {timeout:.0f}s (progress {fb.progress}%)")
        result = {"state": _STATES.get(fb.state, fb.state), "acd": acd_path, "messages": list(fb.messages),
                  "controller": self._summary(self._call("ReadController", uuid=cu).controller)}
        if fb.state != DONE:
            raise EchoServiceError(f"Download {result['state']}: {' | '.join(fb.messages)}")
        return result
