# klippy.py

## Summary
`klippy.py` is the main host process entry point and the `Printer` class that wires together all subsystems. The fork has heavily extended this file to support Snapmaker U1's multi-MCU hardware architecture (1 main MCU + up to 4 extruder MCUs with independent power rails), the structured exception system, and various Snapmaker-specific operational concerns. Key additions include: hardware power rail control (`set_extruder_power`, `set_main_mcu_power`), a JSON config helper API (`load_snapmaker_config_file`, `update_snapmaker_config_file`), the structured exception dispatch bridge (`raise_structured_code_exception`, `raise_coded_exception`, `clear_structured_code_exception`), a JSON message extraction helper (`extract_encoded_message`, `extract_coded_message_field`), process-level real-time scheduling (`set_sched_fifo`), user switching (`switch_user_group`), and firmware version reporting from `/etc/FULLVERSION`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `Printer.__init__` registers `gcode` and `webhooks` for early init | Also registers `exception_manager` | Exception infrastructure must be available before other modules |
| On `klippy:connect` error: `_set_state(str(e) + message_restart)` | Wraps error in a JSON coded-message (`"0003-0522-0000-0003/0004"`) and calls `raise_structured_code_exception` | Feeds structured errors to the Moonraker error bus |
| On MCU shutdown error: `_set_state(msg)` | Wraps with `"0003-0522-0000-0005"` code; sends structured exception | Same |
| `klippy:ready` callbacks run inside `reactor.assert_no_pause()` | `assert_no_pause()` context manager removed; callbacks run unguarded | `assert_no_pause()` was removed from the fork's reactor |
| `invoke_shutdown` sets state and runs handlers in `assert_no_pause` | Adds per-MCU coded exceptions for "Timer too close", "Shutdown due to webhooks", "Shutdown due to M112"; notifies `virtual_sdcard` to record print state; emits `klippy:notify_mcu_shutdown` event | Rich error classification for UI |
| Startup reads `util.get_device_info()` and `util.get_linux_version()` | Both calls removed; version comes from `/etc/FULLVERSION` via `util.get_full_firmware_version()` | Snapmaker firmware ships a canonical version file |
| No CLI `--user` or `--factory` options | `-u/--user` (default `"lava"`) and `-f/--factory` flags added | Process must drop root to the `lava` user after binding hardware |
| Main process starts without RT priority | `set_sched_fifo()` sets `SCHED_FIFO` priority 10 after startup | Reduces jitter on the Snapmaker SoC |
| `queuefile` not initialised | `queuefile.setup_bg_file_operations()` called in `main()`, torn down in cleanup | Background file I/O for config and exception persistence |

## Additions

**`Printer` methods (new):**
- `get_config_dir()` — returns the directory of the active config file.
- `get_snapmaker_config_dir(dir_name="snapmaker")` — returns (creating if needed) a `snapmaker/` subdirectory of the config dir.
- `set_extruder_power(state, extruder=['all'])` — controls `HEAD_MCU_POWER` GPIO via `lava_io set` shell command; also sets `HEAD_MCU*_BOOT` lines.
- `set_main_mcu_power(state)` — controls `MAIN_MCU_POWER` GPIO via `lava_io set`.
- `check_extruder_config_permission()` — checks for `.allow_extruder_modification` marker file in config or USB disk.
- `is_valid_json_format(obj)` → bool.
- `load_snapmaker_config_file(path, default_config, format, create_if_not_exist)` — JSON config loader with defaults merging and `queuefile`-based creation.
- `update_snapmaker_config_file(path, config_info, default_config, format)` — atomic JSON config writer via `queuefile.async_write_file`.
- `extract_encoded_message(message)` — extracts the first `{...}` JSON object from a string.
- `extract_coded_message_field(input_data, field_name='msg')` — returns the `msg` field from an embedded JSON object, or the raw string if none.
- `raise_structured_code_exception(structured_code, message, oneshot, is_persistent, action)` — parses a `LLLL-IIII-NNNN-CCCC` code and calls `exception_manager.raise_exception_async`.
- `clear_structured_code_exception(structured_code)` — calls `exception_manager.clear_exception`.
- `clear_exception(id, index, code)` — direct delegation to `exception_manager`.
- `raise_coded_exception(exception, parse_coded_msg)` — extracts structured fields from a `CodedException` (with optional embedded JSON parsing) and dispatches to `exception_manager`.

**Module-level functions (new):**
- `set_sched_fifo()` — sets `SCHED_FIFO` priority 10 using `ctypes` and `libc.sched_setscheduler`.
- `switch_user_group(user_name)` — drops root to the named user via `os.setreuid`/`os.setregid`/`os.setgroups`.

**CLI options (new):**
- `-u/--user` (`default="lava"`) — user to switch to after startup.
- `-f/--factory` — enables factory mode (stored in `start_args['factory_mode']`).

## Removals / Overrides
- `start_args['device']` and `start_args['linux_version']` fields removed; `get_device_info()` and `get_linux_version()` no longer called.
- `reactor.assert_no_pause()` context manager removed from `klippy:ready` callback dispatch and `invoke_shutdown` handler dispatch.
- `klippy:analyze_shutdown` event removed from handler registration (replaced by direct exception dispatch in `invoke_shutdown`).

## Risks / Compatibility Notes
- `set_extruder_power` and `set_main_mcu_power` call `os.system("lava_io set ...")` — these will silently fail on any machine that does not have the `lava_io` binary on `PATH`.
- `switch_user_group` only works when Klipper starts as `root`. Running as a non-root user with `-u lava` will emit a warning and continue as-is.
- `set_sched_fifo()` requires `CAP_SYS_NICE`; on systems without it the call fails and logs a warning, with no fallback.
- Error codes `"0003-0522-0000-0003"` through `"0003-0522-0000-0005"` are hardcoded in `_connect`. If the exception taxonomy changes in `exception_manager.py`, these codes will be stale.
- Power-cycling MCUs in `invoke_shutdown` via `virtual_sdcard.force_record_pl_print_file_env` adds latency to the shutdown path on every MCU shutdown, not just power-loss events.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/klippy.py
+++ b/klippy/klippy.py
@@ -7,9 +7,11 @@
-import sys, os, gc, optparse, logging, time, collections, importlib
-import util, reactor, queuelogger, msgproto
-import gcode, configfile, pins, mcu, toolhead, webhooks
+import sys, os, gc, optparse, logging, time, collections, importlib, json, copy, re
+import pwd, grp
+import util, reactor, queuelogger, msgproto, queuefile
+import gcode, configfile, pins, mcu, toolhead, webhooks, exception_manager, \
+       coded_exception, printer_device_scan

 # New Printer methods: get_config_dir, set_extruder_power, set_main_mcu_power,
 # get_snapmaker_config_dir, check_extruder_config_permission,
 # load_snapmaker_config_file, update_snapmaker_config_file,
 # extract_encoded_message, extract_coded_message_field,
 # raise_structured_code_exception, clear_structured_code_exception,
 # clear_exception, raise_coded_exception

 # New module-level: set_sched_fifo, switch_user_group
 # New CLI: -u/--user, -f/--factory
```

</details>
