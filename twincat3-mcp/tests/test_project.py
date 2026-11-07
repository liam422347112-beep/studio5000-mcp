from __future__ import annotations

from pathlib import Path

from twincat3_mcp import project

BACKLINE = Path(r"D:\BaiduSyncdisk\Openclaw\BackLine\PLC\StickPackageMachine")


def test_summary_backline():
    if not BACKLINE.is_dir():
        return  # optional integration sample
    s = project.summary(BACKLINE)
    assert s["tsproj"]
    assert s["object_total"] > 10
    assert s["object_counts"]["POU"] >= 1


def test_list_main():
    if not BACKLINE.is_dir():
        return
    objs = project.list_objects(BACKLINE, name_filter="MAIN")
    assert any(o["name"] == "MAIN" for o in objs)
