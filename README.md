# Openclaw PLC MCP workspace

Multi-MCP workspace for industrial engineering agents.

| Folder | Status | Description |
|--------|--------|-------------|
| [`studio5000-mcp/`](studio5000-mcp/) | Ready | Studio 5000 Logix Designer v35 + Logix Echo MCP + skill |
| [`twincat3-mcp/`](twincat3-mcp/) | v0 Ready | TwinCAT 3 offline PLC MCP + general skill (ADS later) |

## TwinCAT v0 tools

`tc_project_summary` · `tc_list_objects` · `tc_get_object` · `tc_backup` · `tc_set_declaration` · `tc_set_implementation` · `tc_search`

## Local artifacts

- `studio5000-mcp/_local/` — golden ACD + Echo intermediates (gitignored)
- TwinCAT projects stay in your machine folders (e.g. `BackLine/PLC/...`); MCP takes paths as arguments
