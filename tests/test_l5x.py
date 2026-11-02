import shutil
from pathlib import Path

import pytest

from studio5000_mcp import l5x

SAMPLE = Path(r"C:\Users\Public\Documents\Studio 5000\Samples\CF_Read_Write.L5X")

MINI = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="35.00" TargetName="T" TargetType="Controller">
<Controller Use="Target" Name="T" ProcessorType="1756-L85E" MajorRev="35">
<DataTypes/>
<Tags>
<Tag Name="Start" TagType="Base" DataType="BOOL"/>
<Tag Name="Stop" TagType="Base" DataType="BOOL"/>
</Tags>
<Programs>
<Program Name="MainProgram" MainRoutineName="MainRoutine">
<Tags>
<Tag Name="Motor" TagType="Base" DataType="BOOL"/>
</Tags>
<Routines>
<Routine Name="MainRoutine" Type="RLL">
<RLLContent>
<Rung Number="0" Type="N"><Text><![CDATA[XIC(Start)OTE(Motor);]]></Text></Rung>
</RLLContent>
</Routine>
<Routine Name="Calc" Type="ST">
<STContent><Line Number="0"><![CDATA[Motor := 0;]]></Line></STContent>
</Routine>
</Routines>
</Program>
</Programs>
<Tasks><Task Name="MainTask" Type="CONTINUOUS"><ScheduledPrograms><ScheduledProgram Name="MainProgram"/></ScheduledPrograms></Task></Tasks>
</Controller>
</RSLogix5000Content>
"""


@pytest.fixture
def mini(tmp_path):
    p = tmp_path / "mini.L5X"
    p.write_text(MINI, encoding="utf-8")
    return str(p)


def test_summary(mini):
    s = l5x.summary(mini)
    assert s["processor"] == "1756-L85E"
    assert s["programs"][0]["routines"][0] == {"name": "MainRoutine", "type": "RLL", "rungs_or_lines": 1}
    assert s["tasks"][0]["programs"] == ["MainProgram"]


def test_validate_rung():
    known = {"start", "stop", "motor"}
    assert l5x.validate_rung("XIC(Start)[XIO(Stop),XIC(Motor)]OTE(Motor);", known)["ok"]
    assert not l5x.validate_rung("XIC(Start)OTE(Motor)", known)["ok"]
    assert not l5x.validate_rung("XIC(Start(OTE(Motor);", known)["ok"]
    w = l5x.validate_rung("XIC(Ghost.Bit)OTE(Motor);", known)["warnings"]
    assert w and "Ghost" in w[0]
    # literals, program-qualified and member/array references are not flagged
    assert not l5x.validate_rung("MOV(5,Program:Other.X)TON(Motor.T[2],?,?);", {"motor"})["warnings"]


def test_edit_rung_cycle(mini):
    r = l5x.edit_rung(mini, "MainProgram", "MainRoutine", "append",
                      text="XIC(Stop)OTU(Motor);", comment="stop latch")
    assert r["total_rungs"] == 2
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "insert", number=0, text="NOP();")
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "replace", number=1, text="XIC(Start)XIO(Stop)OTE(Motor);")
    rungs = l5x.get_routine(mini, "MainProgram", "MainRoutine")["rungs"]
    assert [g["text"] for g in rungs] == ["NOP();", "XIC(Start)XIO(Stop)OTE(Motor);", "XIC(Stop)OTU(Motor);"]
    assert [g["number"] for g in rungs] == [0, 1, 2]
    assert rungs[2]["comment"] == "stop latch"
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "delete", number=0)
    assert l5x.get_routine(mini, "MainProgram", "MainRoutine")["total_rungs"] == 2
    assert Path(mini + ".bak").read_text(encoding="utf-8") == MINI
    # CDATA preserved on disk
    assert "<![CDATA[XIC(Stop)OTU(Motor);]]>" in Path(mini).read_text(encoding="utf-8")


def test_unknown_tag_rejected_unless_forced(mini):
    with pytest.raises(l5x.L5XError, match="unknown tags"):
        l5x.edit_rung(mini, "MainProgram", "MainRoutine", "append", text="XIC(Nope)OTE(Motor);")
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "append", text="XIC(Nope)OTE(Motor);", force=True)


def test_add_tag_then_use(mini):
    l5x.add_tag(mini, "Count", "dint", program="MainProgram", initial_value="7")
    tags = {t["name"]: t for t in l5x.list_tags(mini, "MainProgram")}
    assert tags["Count"]["data_type"] == "DINT"
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "append", text="ADD(Count,1,Count);")
    with pytest.raises(l5x.L5XError, match="already exists"):
        l5x.add_tag(mini, "count", "DINT", program="MainProgram")
    l5x.delete_tag(mini, "Count", program="MainProgram")
    assert "Count" not in {t["name"] for t in l5x.list_tags(mini, "MainProgram")}


def test_st_and_new_routine(mini):
    l5x.set_st_routine(mini, "MainProgram", "Calc", "IF Start THEN\n  Motor := 1;\nEND_IF;")
    assert l5x.get_routine(mini, "MainProgram", "Calc")["total_lines"] == 3
    l5x.add_routine(mini, "MainProgram", "Alarms", "RLL")
    assert l5x.get_routine(mini, "MainProgram", "Alarms")["rungs"][0]["text"] == "NOP();"
    with pytest.raises(l5x.L5XError):
        l5x.edit_rung(mini, "MainProgram", "Calc", "append", text="NOP();")


def test_out_path_leaves_source_untouched(mini, tmp_path):
    out = str(tmp_path / "out.L5X")
    l5x.edit_rung(mini, "MainProgram", "MainRoutine", "append", text="NOP();", out_path=out)
    assert Path(mini).read_text(encoding="utf-8") == MINI
    assert l5x.get_routine(out, "MainProgram", "MainRoutine")["total_rungs"] == 2


@pytest.mark.skipif(not SAMPLE.exists(), reason="Rockwell sample not installed")
def test_real_sample_roundtrip(tmp_path):
    p = tmp_path / "s.L5X"
    shutil.copy(SAMPLE, p)
    s = l5x.summary(str(p))
    prog = s["programs"][0]
    rll = next(r for r in prog["routines"] if r["type"] == "RLL")
    before = l5x.get_routine(str(p), prog["name"], rll["name"])
    l5x.edit_rung(str(p), prog["name"], rll["name"], "append", text="NOP();")
    after = l5x.get_routine(str(p), prog["name"], rll["name"])
    assert after["total_rungs"] == before["total_rungs"] + 1
    assert after["rungs"][:5] == before["rungs"][:5]
