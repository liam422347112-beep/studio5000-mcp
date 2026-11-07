---
name: twincat3-mcp
description: >-
  General TwinCAT 3 PLC workflow via the twincat3-mcp server (offline .tsproj /
  .plcproj / .TcPOU / .TcDUT / .TcGVL inspect and edit). Use when working with
  TwinCAT projects, Structured Text in TcPlcObject files, or twincat3-mcp tools.
  For JOYO packaging + FactoryTalk Optix delivery rules, also load
  twincat3-optix-engineering.
---

# twincat3-mcp (general)

Companion skill for the **twincat3-mcp** MCP server. Prefer this for TwinCAT PLC file work. Machine/Optix-specific rules live in `twincat3-optix-engineering`.

## Hard rule

**Backup before edit** — before changing any `.tsproj` / `.plcproj` / `.TcPOU` / `.TcDUT` / `.TcGVL`, call `tc_backup` (or rely on `tc_set_*` default `make_backup=true`). Never silent-overwrite the user’s golden project.

## Safety

- Prefer timestamped working copies for broad refactors.
- Preserve XML/CDATA structure; do not pretty-print or bulk-reformat TwinCAT XML.
- PowerShell may mojibake Chinese; verify UTF-8 before rewriting text.
- After PLC edits, state clearly if TwinCAT XAE Build / activate is still required.
- ADS online write (future) only against requested targets — never invent production downloads.

## Default toolchain (v0 offline)

1. `tc_project_summary(path)` — find `.tsproj` / PLC projects / object counts  
2. `tc_list_objects` / `tc_search` — locate POU/DUT/GVL  
3. `tc_get_object` — read Declaration + Implementation ST  
4. `tc_set_declaration` / `tc_set_implementation` — scoped ST edits (backup on)  
5. Ask user to Build/Activate in TwinCAT XAE when runtime proof is needed  

## Tool map

| Tool | Purpose |
|------|---------|
| `tc_project_summary` | Solution / PLC overview |
| `tc_list_objects` | List Compile includes (filter by kind/name) |
| `tc_get_object` | Read ST declaration / implementation |
| `tc_backup` | Timestamped `.bak` |
| `tc_set_declaration` | Replace Declaration CDATA |
| `tc_set_implementation` | Replace Implementation/ST CDATA |
| `tc_search` | Regex across object ST text |

## Practical notes

- `.tsproj` can be huge / awkward XML — prefer `PrjFilePath` discovery + `.plcproj` Compile list, then edit individual object files.
- DUT/GVL usually have Declaration only; POU has Implementation/ST.
- Keep edits scoped to the symbols requested. Do not “clean up” unrelated POUs.
- For PackML / servo / Optix HMI delivery, load `twincat3-optix-engineering` and follow its project `AGENTS.md`.

## Completion

Report tools used, files changed, backups created, and what still needs TwinCAT XAE Build/Activate.
