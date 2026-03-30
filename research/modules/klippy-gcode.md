# gcode.py

## Summary
`gcode.py` is the G-code parser and command dispatcher. The fork's changes fall into three areas: (1) `CommandError` now inherits from `CodedException` so all G-code errors carry structured error codes; (2) the command parsing and dispatch loop gains thread-local tracking to avoid duplicate exception reporting on nested calls; (3) several minor parsing fixes and one new G-code command (`SWITCH_OF_EXTENDED_EXTRUDER`) are wired through `toolhead`. Additionally, `Coord` is reverted from an upstream-2025 optimised subclass back to a plain `collections.namedtuple`, and the extended-command (`shlex`) regex and parsing are adjusted.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class CommandError(Exception)` | `class CommandError(CodedException)` | All G-code errors carry structured `id`/`code`/`level` |
| `Coord` is an optimised `tuple` subclass with `__slots__` and property accessors | `Coord = collections.namedtuple('Coord', ('x', 'y', 'z', 'e'))` | Reverted to an older simpler implementation |
| `_process_commands` calls handlers directly; a `gcode.command_error` propagates without coded dispatch | Wrapped in `try/finally` with thread-local `_thread_local.in_process_commands`; on error calls `printer.raise_coded_exception(e)` | Prevents duplicate exception reports for nested command calls |
| `get_value` / `get_float` / `get_int` raise plain `CommandError` | Raise `CommandError(..., id=529, code=N, level=3)` | Error codes 529-0 through 529-5 map to GCode module errors |
| Extended command regex: `args_r = re.compile('([A-Z_]+|[A-Z*])')` | Adds `/` to character class: `([A-Z_]+|[A-Z*/])` | Supports file-path parameters in extended commands |
| Command dispatch for `M117`/`M118` uses `' '.join` split then special-cases `M23` | Uses `cmd.startswith("M117 ")` check; dispatches to `cmd[:4]` | Simpler and removes M23 special-case |
| `klippy:analyze_shutdown` event handler `_handle_analyze_shutdown` | Renamed to `_dump_debug`; `klippy:analyze_shutdown` event removed | Fork removed the `analyze_shutdown` event |
| `register_event_handler` calls placed at end of `__init__` | Moved to earlier in `__init__` (before command registrations) | Ordering fix |
| `mux command` registration raises plain `config_error` | Raises `config_error` with embedded JSON coded string (`"0003-0529-0000-0007"`) | Structured error |
| `cmd_default` raises plain error for unknown mux value | Raises `gcmd.error(..., id=529, code=9, level=1)` | Structured error |

## Additions
- `from coded_exception import CodedException` import.
- `_thread_local = threading.local()` module-level thread-local for nested dispatch guard.
- `GCodeCommand.get_raw_command_parameters()` — fork reverts the 2025 upstream refactor; now handles `M117`/`M118` prefix stripping inline.
- `GCodeDispatch._process_commands()` — `is_top_level` guard using `_thread_local.in_process_commands` to suppress duplicate exception reporting.
- `extended_r` compiled regex on `GCodeDispatch` for extended command parsing (replaces `shlex`-only parsing).
- `GCodeDispatch.exception_manager` attribute initialised to `None` in `__init__`.

## Removals / Overrides
- `Coord` optimised tuple subclass (upstream 2025 addition) replaced with `namedtuple`.
- `import operator` replaced by `import threading`.
- `klippy:analyze_shutdown` handler registration removed from `GCodeDispatch.__init__`.
- Upstream 2025 improvements to `GCodeCommand.get_raw_command_parameters` (line-number skipping via slice arithmetic) reverted.
- `register_event_handler` for `klippy:ready` / `klippy:shutdown` moved earlier in `__init__`.

## Risks / Compatibility Notes
- `Coord` is now a `namedtuple`. Upstream 2025 code that uses `Coord.x`, `Coord.y`, `Coord.z`, `Coord.e` as attribute access still works. Code that relies on `Coord` being exactly a `tuple` subclass also works. However, the upstream `Coord.__new__` pads short tuples to length 4; the fork's `namedtuple` requires exactly 4 positional arguments.
- Thread-local `in_process_commands` is never cleaned up if `handler(gcmd)` raises a non-`self.error` exception (caught by the bare `except:` block that calls `invoke_shutdown`). The `finally` block ensures cleanup, so this is safe.
- Error codes `529-0` through `529-9` are hardcoded in `get_value`, `get_float`, `get_int`, `get_raw_command_parameters`, and `cmd_default`. If the GCode module ID changes in `exception_manager.py` (currently `MODULE_ID_GCODE=529`), these will be stale.
- The `M23` special-case in `cmd_default` was removed. If any caller sends `M23 filename`, it will now fall through to the default handler.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/gcode.py
+++ b/klippy/gcode.py
@@ -6 +6 @@
-import os, re, logging, collections, shlex, operator
+import os, re, logging, collections, shlex, threading
+from coded_exception import CodedException
+_thread_local = threading.local()

@@ -8 +12 @@
-class CommandError(Exception):
+class CommandError(CodedException):

@@ -11,11 +15 @@
-class Coord(tuple):
-    __slots__ = ()
-    ...
+Coord = collections.namedtuple('Coord', ('x', 'y', 'z', 'e'))

 # get_value/get_float/get_int: add id=529, code=N, level=3 to errors
 # _process_commands: wrap in try/finally with thread-local guard
 # cmd_default: M117/M118 dispatch simplified; mux error is coded
 # _handle_analyze_shutdown renamed to _dump_debug
```

</details>
