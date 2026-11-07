# studio5000-mcp

MCP server for **Studio 5000 Logix Designer v35** program editing and **FactoryTalk Logix Echo** testing on Windows.

- Offline **L5X** edit (tags, rungs, routines, controller retarget)
- **GUI** export / import / verify (Logix Designer via UI Automation)
- **Echo** snapshot / download + CIP tag read / write / test (pylogix)
- Optional licensed **SDK / COM** backends when available

## Requirements

- Windows 10/11
- Python 3.11+
- Studio 5000 Logix Designer v35 (for GUI path)
- FactoryTalk Logix Echo (for download / CIP prove-out)

## Install

```powershell
git clone https://github.com/liam422347112-beep/studio5000-mcp.git
cd studio5000-mcp
py -3.12 -m pip install -e .
```

Or from a Release asset: download the source zip / wheel and install.

## Cursor MCP config

```json
{
  "mcpServers": {
    "studio5000-echo": {
      "command": "py",
      "args": ["-3.12", "-m", "studio5000_mcp"],
      "cwd": "d:/path/to/studio5000-mcp",
      "env": {
        "ECHO_IP": "127.0.0.1",
        "ECHO_SLOT": "0"
      }
    }
  }
}
```

## Agent skills

| Skill | Scope |
|-------|--------|
| [`skills/studio5000-mcp`](skills/studio5000-mcp/SKILL.md) | **General** MCP workflow (recommended default) |
| [studio5000-echo-engineering](https://github.com/liam422347112-beep/studio5000-echo-engineering) | PackML / machine Echo bring-up notes |

Copy into Cursor user Agent Store `skills/` or project `.cursor/skills/`.

### Hard rule (general skill)

Before any L5X export/import: if the project has no-EDS Ethernet devices, **ask the user** whether to temporarily strip them for Echo, install EDS first, or cancel. Never silent-strip.

## Quick tool flow

```text
gui_export_l5x → l5x_* edits → l5x_set_controller_type (Echo: 1756-L85E)
→ gui_import_l5x → gui_verify (0 errors)
→ echo_snapshot → echo_download → echo_read / echo_write
```

## Repo layout

```text
studio5000_mcp/   # MCP server package
skills/           # Cursor general skill
scripts/          # optional Echo bring-up helpers (EM16 / no-EDS strip)
tests/
_local/           # gitignored: golden ACD + Echo intermediates (local only)
```

## License

MIT — see [LICENSE](LICENSE).
