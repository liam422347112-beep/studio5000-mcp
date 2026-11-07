---
name: studio5000-mcp
description: >-
  General Studio 5000 + FactoryTalk Logix Echo workflow via the studio5000-mcp
  server (L5X edit, GUI export/import/verify, Echo snapshot/download, CIP
  read/write). Use when working with ACD/L5X, Logix Designer v35 GUI automation,
  Echo emulators, or studio5000-mcp tools — not project-specific PackML recipes.
---

# studio5000-mcp (general)

Companion skill for the **studio5000-mcp** MCP server. Prefer this for any Studio 5000 / Echo task. For PackML machine bring-up (JOYO/Damin-style), also load `studio5000-echo-engineering`.

## Hard rule

**No-EDS first** — third-party / generic Ethernet modules without a usable EDS on this PC lose IO tags on L5X export↔import. Before any `gui_export_l5x` / `gui_import_l5x`:

1. Inspect modules for missing EDS.
2. Stop and ask the user:

   > 项目里有无 EDS 设备（列出名称）。L5X 导入/导出后 IO 标签会丢失。请选择：  
   > **A)** 为 Echo 临时删除这些模块及依赖程序/引用（可还原的工作副本）  
   > **B)** 你先在本机手动安装/导入对应 EDS，装好后告诉我再继续导入导出  
   > **C)** 取消本次导入导出

3. Do not silent-strip. Proceed only after A/B/C.

## Safety

- Timestamped working copies; do not overwrite the user’s golden ACD unless asked.
- CIP write / `echo_run_test` → Echo only unless the user explicitly authorizes a real PLC.
- `echo_snapshot` before every `echo_download`.
- GUI automation: leave unexpected dialogs untouched and abort.

## Default toolchain (no SDK/COM licence)

Use unless `logix_backend_status` proves COM/SDK works:

1. `gui_export_l5x` — ACD → L5X  
2. `l5x_*` edits (`summary`, `get_routine`, `edit_rung`, `add_tag`, …)  
3. `l5x_set_controller_type` — Echo 5580 → `1756-L85E` major 35  
4. `gui_import_l5x` — L5X → new ACD  
5. `gui_verify` — 0 errors required  
6. `echo_snapshot` → `echo_download` → `echo_read` / `echo_write` / `echo_run_test`

## Tool map

| Area | Tools |
|------|--------|
| Online Echo CIP | `echo_info`, `echo_list_programs`, `echo_list_tags`, `echo_read`, `echo_write`, `echo_run_test` |
| Echo service | `echo_controllers`, `echo_snapshot`, `echo_download` |
| Offline L5X | `l5x_summary`, `l5x_get_routine`, `l5x_list_tags`, `l5x_validate_rung`, `l5x_edit_rung`, `l5x_add_tag`, `l5x_add_routine`, `l5x_set_st_routine`, `l5x_set_controller_type`, `l5x_clone_module`, … |
| GUI | `gui_status`, `gui_export_l5x`, `gui_import_l5x`, `gui_verify` |
| Licensed backends | `logix_backend_status`, `acd_*` (SDK/COM when available) |

## Practical notes

- Program-scope CIP: `Program:Name.Tag`. Controller tags: bare name.
- Ladder NeutralText ends with `;`; branches `[A,B]`.
- After import, window title may omit `in <file>.ACD` — match ACD stem. Errors pane may be invisible; still readable. Settle ≥3s before re-verify.
- Large L5X: targeted Python replace-in-section if editor patch tools choke, then re-import/verify.
- Free-running wrap proof: write near threshold (e.g. `Cnt=4990`), expect low band — do not watch climb from 0 over CIP.

## Completion

Report tools used, verify error count, download result, and live tag evidence.
