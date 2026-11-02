import os

import pytest

from studio5000_mcp import gui_client as g
from studio5000_mcp import vdesktop


def test_project_file_from_title():
    assert g.project_file_from_title("Logix Designer - TF10 in Probe.ACD [5069-L330ERM 35.14]") == "Probe.ACD"
    assert g.project_file_from_title("Logix Designer - A in My Project v2.ACD [1756-L85E 35.11]") == "My Project v2.ACD"
    assert g.project_file_from_title("Logix Designer") is None
    assert g.project_file_from_title("") is None


def test_title_matches_is_case_insensitive_on_basename():
    title = "Logix Designer - TF10 in Probe.ACD [5069-L330ERM 35.14]"
    assert g.title_matches(title, r"C:\Temp\probe.acd")
    assert not g.title_matches(title, r"C:\Temp\Probe_reimport.ACD")


def test_prepare_output_missing_file(tmp_path):
    assert g.prepare_output(str(tmp_path / "x.L5X"), overwrite=False) is None


def test_prepare_output_refuses_without_overwrite(tmp_path):
    p = tmp_path / "x.L5X"
    p.write_text("old")
    with pytest.raises(g.GuiError, match="overwrite=true"):
        g.prepare_output(str(p), overwrite=False)
    assert p.read_text() == "old"


def test_prepare_output_moves_aside_and_restore(tmp_path):
    p = tmp_path / "x.L5X"
    p.write_text("old")
    backup = g.prepare_output(str(p), overwrite=True)
    assert backup == str(p) + ".bak" and not p.exists()
    p.write_text("older")  # second overwrite keeps the first backup
    p2 = g.prepare_output(str(p), overwrite=True)
    assert p2 != backup and open(p2).read() == "older"
    g._restore(str(p), p2)
    assert p.read_text() == "older"
    assert open(backup).read() == "old"


def test_import_rejects_bad_extensions(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("x")
    with pytest.raises(g.GuiError, match=r"\.L5X"):
        g.LogixGui()._import(str(src), str(tmp_path / "b.ACD"), False, None, 5)
    with pytest.raises(g.GuiError, match="not found"):
        g.LogixGui()._import(str(tmp_path / "missing.L5X"), str(tmp_path / "b.ACD"), False, None, 5)


class _FakeDesk:
    def __init__(self, n):
        self.number = n


class _FakeView:
    def __init__(self, desk):
        self.desktop = _FakeDesk(desk)
        self.moved_to = None

    def move(self, d):
        self.moved_to = d.number


@pytest.fixture
def fake_vda(monkeypatch):
    import types
    state = {"desktops": 2, "current": 1, "view": _FakeView(1), "created": 0}

    def create():
        state["created"] += 1
        state["desktops"] += 1
    mod = types.SimpleNamespace(
        get_virtual_desktops=lambda: [_FakeDesk(i + 1) for i in range(state["desktops"])],
        VirtualDesktop=type("VD", (), {
            "__init__": lambda self, n: setattr(self, "number", n),
            "current": staticmethod(lambda: _FakeDesk(state["current"])),
            "create": staticmethod(create)}),
        AppView=lambda hwnd: state["view"])
    monkeypatch.setitem(__import__("sys").modules, "pyvda", mod)
    monkeypatch.setattr(vdesktop, "is_cloaked", lambda h: True)
    return state


def test_moves_to_last_desktop_without_switching(fake_vda):
    r = vdesktop.move_to_work_desktop(123)
    assert r["moved"] and fake_vda["view"].moved_to == 2 and r["current"] == 1


def test_creates_second_desktop_when_only_one(fake_vda):
    fake_vda["desktops"] = 1
    vdesktop.move_to_work_desktop(123)
    assert fake_vda["created"] == 1 and fake_vda["view"].moved_to == 2


def test_leaves_window_when_user_watches_work_desktop(fake_vda):
    fake_vda["current"] = 2
    assert not vdesktop.move_to_work_desktop(123)["moved"]
    assert fake_vda["view"].moved_to is None


def test_info_reports_api_failure(monkeypatch):
    import types
    def boom():
        raise RuntimeError("no vda")
    monkeypatch.setitem(__import__("sys").modules, "pyvda", types.SimpleNamespace(get_virtual_desktops=boom))
    assert "error" in vdesktop.info()


@pytest.mark.skipif(not os.environ.get("S5K_GUI_LIVE"), reason="set S5K_GUI_LIVE=<scratch .ACD> to drive Logix Designer")
def test_live_roundtrip(tmp_path):
    acd = os.environ["S5K_GUI_LIVE"]
    gui = g.LogixGui()
    out = gui.export_l5x(acd, str(tmp_path / "rt.L5X"))
    assert out["bytes"] > 0
    imp = gui.import_l5x(out["exported"], str(tmp_path / "rt.ACD"), host_acd=acd)
    assert imp["bytes"] > 0
