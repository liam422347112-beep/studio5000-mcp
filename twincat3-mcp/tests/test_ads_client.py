from __future__ import annotations

import os

import pytest

from twincat3_mcp import ads_client


def test_resolve_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TWINCAT_AMS_NETID", raising=False)
    monkeypatch.delenv("TWINCAT_AMS_PORT", raising=False)
    assert ads_client.resolve_netid(None) == "127.0.0.1.1.1"
    assert ads_client.resolve_port(None) == 851
    assert ads_client.is_local_netid("127.0.0.1.1.1")
    assert not ads_client.is_local_netid("192.168.10.40.1.1")


def test_remote_write_gated(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TWINCAT_ADS_ALLOW_REMOTE_WRITE", raising=False)
    with pytest.raises(PermissionError):
        ads_client.assert_write_allowed("192.168.10.40.1.1")
    monkeypatch.setenv("TWINCAT_ADS_ALLOW_REMOTE_WRITE", "1")
    ads_client.assert_write_allowed("192.168.10.40.1.1")


def test_probe_local_system():
    info = ads_client.probe()
    assert info["netid"] == "127.0.0.1.1.1"
    # System service should answer when TwinCAT is installed
    assert info["system"] is not None
    if info["system"].get("ok"):
        assert info["system"]["port"] == 10000
    # PLC may be down if no config activated — still a valid probe result
    assert "plc" in info
