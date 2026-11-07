# twincat3-mcp

MCP server for **TwinCAT 3** PLC project inspect/edit on Windows.

**v0 (now):** offline filesystem tools for `.tsproj` / `.plcproj` / `.TcPOU` / `.TcDUT` / `.TcGVL`  
**Later:** optional ADS symbol read/write (`pip install twincat3-mcp[ads]`)

## Requirements

- Windows 10/11
- Python 3.11+
- TwinCAT 3 XAE (for Build/Activate; not required for offline file tools)

## Install

```powershell
cd D:\BaiduSyncdisk\Openclaw\studiomcp\twincat3-mcp
py -3.12 -m pip install -e .
```

## Cursor MCP config

```json
{
  "mcpServers": {
    "twincat3": {
      "command": "py",
      "args": ["-3.12", "-m", "twincat3_mcp"],
      "cwd": "d:/BaiduSyncdisk/Openclaw/studiomcp/twincat3-mcp"
    }
  }
}
```

## Agent skill

[`skills/twincat3-mcp/SKILL.md`](skills/twincat3-mcp/SKILL.md) — general MCP workflow.

JOYO / Optix packaging rules: use existing `twincat3-optix-engineering` skill alongside this one.

### Hard rule

Backup before any TwinCAT XML/ST edit (`tc_backup` or `make_backup=true` on setters).

## Quick tool flow

```text
tc_project_summary → tc_list_objects / tc_search
→ tc_get_object → tc_set_declaration | tc_set_implementation
→ user Build/Activate in TwinCAT XAE
```

## License

MIT — see [LICENSE](LICENSE).
