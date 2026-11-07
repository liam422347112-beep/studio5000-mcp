---
name: twincat3-mcp
description: >-
  TwinCAT 3 PLC workflow via twincat3-mcp: offline .tsproj/.plcproj/.TcPOU edit
  and ADS online symbol read/write for local simulation or remote targets. Use
  when working with TwinCAT projects, local Run-mode prove-out, ADS tags, or
  twincat3-mcp tools. For JOYO packaging + FactoryTalk Optix delivery rules,
  also load twincat3-optix-engineering.
---

# twincat3-mcp (general)

Companion skill for the **twincat3-mcp** MCP server.

## Hard rule

**Backup before file edit** — before changing `.tsproj` / `.plcproj` / `.TcPOU` / `.TcDUT` / `.TcGVL`, use `tc_backup` (or `tc_set_*` with `make_backup=true`).

## Safety

- Preserve TwinCAT XML/CDATA; no bulk reformat.
- ADS **local** writes (`127.0.0.1.*.*`) allowed for simulation prove-out.
- ADS **remote** writes require env `TWINCAT_ADS_ALLOW_REMOTE_WRITE=1` **and** explicit user approval. Never invent production downloads.
- After offline ST edits, Build/Activate in TwinCAT XAE before expecting ADS symbols to match.

## Local simulation prove-out

1. TwinCAT XAE → target **`<Local>`**
2. **Activate Configuration** (loads Boot project)
3. Switch to **Run** mode (not Config) — PLC ADS port **851** must be up
4. `ads_info()` — expect `system.ok=true`; `plc.ok=true` when Run
5. If `plc.ok=false` with “Target port not found (6)”: Activate + Run, then retry
6. `ads_list_symbols` / `ads_read` / `ads_write` against symbol names (e.g. `GVL_x.y`)

Defaults: NetId `127.0.0.1.1.1`, port `851` (override with tool args or `TWINCAT_AMS_NETID` / `TWINCAT_AMS_PORT`).

## Offline toolchain

1. `tc_project_summary` → `tc_list_objects` / `tc_search`
2. `tc_get_object` → `tc_set_declaration` / `tc_set_implementation`
3. User Build/Activate/Run → ADS prove-out

## Tool map

| Tool | Purpose |
|------|---------|
| `tc_project_summary` | Solution / PLC overview |
| `tc_list_objects` | List Compile includes |
| `tc_get_object` | Read Declaration / Implementation ST |
| `tc_backup` | Timestamped `.bak` |
| `tc_set_declaration` | Replace Declaration CDATA |
| `tc_set_implementation` | Replace Implementation/ST |
| `tc_search` | Regex across ST text |
| `ads_info` | Probe system+PLC ADS ports / Run hints |
| `ads_read` | Read symbols by name |
| `ads_write` | Write symbols by name (remote gated) |
| `ads_list_symbols` | Browse PLC symbol table |
| `ads_symbol_info` | One-symbol metadata |

## Completion

Report offline files/backups changed, `ads_info` state, and live read/write evidence. Note if XAE Activate/Run is still required.
