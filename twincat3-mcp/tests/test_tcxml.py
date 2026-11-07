from __future__ import annotations

import shutil
from pathlib import Path

from twincat3_mcp import tcxml

FIXTURE = Path(__file__).parent / "fixtures" / "SampleFB.TcPOU"


def test_get_object(tmp_path: Path):
    p = tmp_path / "SampleFB.TcPOU"
    shutil.copy2(FIXTURE, p)
    info = tcxml.get_object(p)
    assert info["name"] == "SampleFB"
    assert info["kind"] == "POU"
    assert "FUNCTION_BLOCK SampleFB" in info["declaration"]
    assert "nCnt := nCnt + 1" in (info["implementation"] or "")


def test_set_implementation_roundtrip(tmp_path: Path):
    p = tmp_path / "SampleFB.TcPOU"
    shutil.copy2(FIXTURE, p)
    new_st = "bDone := bEnable;\n"
    r = tcxml.set_implementation(p, new_st, make_backup=True)
    assert r["backup"]
    assert Path(r["backup"]).is_file()
    info = tcxml.get_object(p)
    assert info["implementation"].strip() == "bDone := bEnable;"


def test_search(tmp_path: Path):
    p = tmp_path / "SampleFB.TcPOU"
    shutil.copy2(FIXTURE, p)
    hits = tcxml.search_in_object(p, r"nCnt")
    assert any(h["section"] == "declaration" for h in hits)
    assert any(h["section"] == "implementation" for h in hits)
