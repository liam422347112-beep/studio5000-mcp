"""Minimal Python client for the Logix Designer SDK service (LdSdkServer, gRPC on localhost:53204).

The message/service schema (LSDKMessages.pb) was recovered from the descriptor embedded in
RockwellAutomation.LogixDesigner.LogixProject.CSClient 1.1.599, the client shipped with v35.
The server requires a Logix Designer SDK license; without it Open() fails with "No valid license".
"""
from __future__ import annotations

import os
import struct
import zlib

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

SDK_ADDRESS = os.environ.get("LDSDK_ADDRESS", "localhost:53204")
_CHUNK = 30000  # server caps inbound messages at ~31 KB

_fd = descriptor_pb2.FileDescriptorProto()
with open(os.path.join(os.path.dirname(__file__), "LSDKMessages.pb"), "rb") as f:
    _fd.ParseFromString(f.read())
_pool = descriptor_pool.DescriptorPool()
_file = _pool.Add(_fd)
_service = _file.services_by_name["LogixSDK"]
M = {m.name: message_factory.GetMessageClass(_pool.FindMessageTypeByName("LSDKMessages." + m.name))
     for m in _fd.message_type}

MODES = {"Run": 0, "Program": 1, "Test": 2}
MERGE_MODES = {"Inhibit": 0, "Attempt": 1, "Required": 2}
DATA_TYPES = {"BYTE_ARRAY": 0, "BOOL": 1, "SINT": 2, "INT": 3, "DINT": 4, "LINT": 5, "USINT": 6,
              "UINT": 7, "UDINT": 8, "ULINT": 9, "STRING": 10, "REAL": 11, "LREAL": 12}
_PACK = {"BOOL": "<?", "SINT": "<b", "INT": "<h", "DINT": "<i", "LINT": "<q", "USINT": "<B",
         "UINT": "<H", "UDINT": "<I", "ULINT": "<Q", "REAL": "<f", "LREAL": "<d"}


class SdkError(Exception):
    pass


class LogixSdk:
    def __init__(self, address: str = SDK_ADDRESS, timeout: float = 900):
        self.timeout = timeout
        self.channel = grpc.insecure_channel(address)
        self.projects: dict[str, str] = {}  # acd path -> project key

    def _call(self, name: str, request, client_stream: bool = False) -> list:
        method = _service.methods_by_name[name]
        out = M[method.output_type.name]
        path = f"/LSDKMessages.LogixSDK/{name}"
        factory = self.channel.stream_stream if client_stream else self.channel.unary_stream
        rpc = factory(path, request_serializer=lambda m: m.SerializeToString(),
                      response_deserializer=out.FromString)
        data, status = [], []
        try:
            for resp in rpc(request, timeout=self.timeout):
                kind = resp.WhichOneof("SubMessage")
                if kind == "Result" and resp.Result.ResultValue != 0:
                    raise SdkError(f"{name} failed: {resp.Result.ResultMessage}")
                if kind == "Data":
                    data.append(resp.Data)
                elif kind == "Status" and resp.Status.WhichOneof("StatusValue") == "StatusMessage":
                    status.append(resp.Status.StatusMessage)
        except grpc.RpcError as e:
            raise SdkError(f"{name}: LdSdkServer unreachable or errored ({e.code().name}: {e.details()})") from e
        return data

    def _key(self, acd_path: str) -> str:
        acd_path = os.path.abspath(acd_path)
        if acd_path not in self.projects:
            self.open(acd_path)
        return self.projects[acd_path]

    def open(self, acd_path: str) -> str:
        acd_path = os.path.abspath(acd_path)
        with open(acd_path, "rb") as f:
            content = f.read()

        def chunks():
            yield M["ProjectOpenRequest"](UserToken="")
            for i in range(0, len(content), _CHUNK):
                yield M["ProjectOpenRequest"](Content=content[i:i + _CHUNK])
            yield M["ProjectOpenRequest"](Crc32=zlib.crc32(content) & 0xFFFFFFFF)

        data = self._call("Open", chunks(), client_stream=True)
        key = next((d.StringValue for d in data if d.WhichOneof("DataValue") == "StringValue"), None)
        if not key:
            raise SdkError("Open returned no project key")
        self.projects[acd_path] = key
        return key

    def _project_req(self, acd_path: str):
        return M["ProjectRequest"](Key=self._key(acd_path))

    def close(self, acd_path: str) -> None:
        acd_path = os.path.abspath(acd_path)
        if acd_path in self.projects:
            self._call("Close", M["ProjectRequest"](Key=self.projects.pop(acd_path)))

    def save(self, acd_path: str) -> str:
        """Server-side save, then write the returned ACD content back to the local file."""
        data = self._call("Save", self._project_req(acd_path))
        blob = b"".join(d.FileContent for d in data if d.WhichOneof("DataValue") == "FileContent")
        if blob:
            tmp = acd_path + ".sdktmp"
            with open(tmp, "wb") as f:
                f.write(blob)
            os.replace(tmp, acd_path)
        return acd_path

    def get_comm_path(self, acd_path: str) -> str:
        data = self._call("GetCommPath", self._project_req(acd_path))
        return next((d.StringValue for d in data), "")

    def set_comm_path(self, acd_path: str, comm_path: str) -> None:
        self._call("SetCommPath", M["ProjectPathRequest"](Key=self._key(acd_path), Path=comm_path))

    def read_mode(self, acd_path: str) -> int:
        data = self._call("ReadControllerMode", self._project_req(acd_path))
        return next((d.Uint32Value for d in data), -1)

    def change_mode(self, acd_path: str, mode: str) -> None:
        self._call("ChangeControllerMode", M["ChangeModeRequest"](Key=self._key(acd_path), Mode=MODES[mode]))

    def download(self, acd_path: str) -> None:
        self._call("Download", self._project_req(acd_path))

    def upload(self, acd_path: str, merge_mode: str = "Inhibit") -> None:
        self._call("Upload", M["UploadModeRequest"](Key=self._key(acd_path), Mode=MERGE_MODES[merge_mode]))

    def get_tag(self, acd_path: str, tag: str, data_type: str, online: bool):
        data = self._call("GetTagValue", M["GetTagValueRequest"](
            Key=self._key(acd_path), TagPath=tag, mode=int(online), type=DATA_TYPES[data_type]))
        if not data:
            return None
        d = data[0]
        kind = d.WhichOneof("DataValue")
        raw = getattr(d, kind)
        if kind == "BytesValue" and data_type in _PACK:
            return struct.unpack(_PACK[data_type], raw[:struct.calcsize(_PACK[data_type])])[0]
        if kind == "BytesValue" and data_type == "STRING":
            return raw.decode("utf-8", "replace")
        return raw

    def set_tag(self, acd_path: str, tag: str, data_type: str, value, online: bool) -> None:
        if data_type in _PACK:
            raw = struct.pack(_PACK[data_type], value)
        elif data_type == "STRING":
            raw = str(value).encode("utf-8")
        else:
            raise SdkError(f"Unsupported data type {data_type}")
        self._call("SetTagValue", M["SetTagValueRequest"](
            Key=self._key(acd_path), TagPath=tag, TagValue=raw, mode=int(online), type=DATA_TYPES[data_type]))
