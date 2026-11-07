# twincat3-mcp

MCP server for **TwinCAT 3** PLC engineering on Windows.

- **Offline:** `.tsproj` / `.plcproj` / `.TcPOU` / `.TcDUT` / `.TcGVL` inspect & edit  
- **Online ADS:** symbol read/write for **local simulation** (default) or remote (write-gated)

## Requirements

- Windows 10/11 + TwinCAT 3 (TcSysSrv)
- Python 3.11+
- For ADS prove-out: XAE **Activate Configuration** + **Run** on `<Local>` (PLC port 851)

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
      "cwd": "d:/BaiduSyncdisk/Openclaw/studiomcp/twincat3-mcp",
      "env": {
        "TWINCAT_AMS_NETID": "127.0.0.1.1.1",
        "TWINCAT_AMS_PORT": "851"
      }
    }
  }
}
```

Remote writes also need `"TWINCAT_ADS_ALLOW_REMOTE_WRITE": "1"` after explicit approval.

## Agent skill

[`skills/twincat3-mcp/SKILL.md`](skills/twincat3-mcp/SKILL.md)

### Hard rule

Backup before TwinCAT XML/ST file edits.

## Local simulation flow

```text
XAE <Local> → Activate → Run
→ ads_info (system + plc ports)
→ ads_list_symbols / ads_read / ads_write
```

If `ads_info.plc.ok=false` with ADS error 6: PLC runtime not started — Activate/Run first.

## Offline + online tools

| Area | Tools |
|------|--------|
| Files | `tc_project_summary`, `tc_list_objects`, `tc_get_object`, `tc_backup`, `tc_set_*`, `tc_search` |
| ADS | `ads_info`, `ads_read`, `ads_write`, `ads_list_symbols`, `ads_symbol_info` |

## License

MIT — see [LICENSE](LICENSE).
