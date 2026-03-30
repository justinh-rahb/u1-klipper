# exception_manager.py

## Summary
A fork-exclusive Klipper module that provides a centralised, structured error-reporting bus between the klippy host process and the Moonraker API layer. `ExceptionManager` maintains an in-memory list of active exceptions (keyed by `id`, `index`, `code` triples), optionally persists them to `exception_persistent.json` in the Snapmaker config directory, and forwards them to Moonraker via `webhooks.call_remote_method('raise_exception', ...)`. It also registers four G-code commands (`RAISE_EXCEPTION`, `CLEAR_EXCEPTION`, `QUERY_EXCEPTION`, `RM_EXCEPTION_PERSISTENT_FILE`) for manual inspection and testing. The module has no upstream counterpart; it is the back-end that `klippy.py`'s `raise_structured_code_exception` and `raise_coded_exception` helpers delegate to.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No structured exception bus exists | `ExceptionManager` bridges klippy exceptions to Moonraker via `webhooks.call_remote_method` | Allows the UI to display user-friendly error codes without parsing log strings |
| Errors are not persisted across restarts | Non-oneshot exceptions with `is_persistent=1` are written to `exception_persistent.json` and replayed on startup | Preserves error state (e.g. power-loss events) through firmware restarts |
| N/A | `ExceptionList` class enumerates all Snapmaker module IDs (522–2052) and error codes | Provides a single source of truth for the numeric error taxonomy |

## Additions
- `ExceptionList` class — module-ID and error-code constants:
  - `MODULE_ID_MOTION=522`, `MODULE_ID_TOOLHEAD=523`, `MODULE_ID_CAMERA=524`, `MODULE_ID_FEEDING=525`, `MODULE_ID_HEATER_BED=526`, `MODULE_ID_CAVITY=527`, `MODULE_ID_HOMING=528`, `MODULE_ID_GCODE=529`, `MODULE_ID_PROBE_OR_CALIBRATION=530`, `MODULE_ID_PRINT_FILE=531`, `MODULE_ID_DEFECT_DETECTION=532`, `MODULE_ID_SYSTEM=2052`.
- `ExceptionManager` class:
  - `__init__` — loads persisted exceptions from `exception_persistent.json`, registers G-code commands, starts timers.
  - `_parse_structured_code(coded_string)` — static; parses `LLLL-IIII-NNNN-CCCC` → `dict`.
  - `_parse_basic_code(coded_string)` — static; parses `IIII-NNNN-CCCC` → `dict`.
  - `raise_exception_async(id, index, code, message, oneshot, level, is_persistent, action)` — queues an exception for delivery on the reactor thread.
  - `raise_exception(id, index, code, message, oneshot, level, is_persistent)` — delivers immediately; deduplicates non-oneshot exceptions; calls `webhooks.call_remote_method('raise_exception', ...)`.
  - `clear_exception(id, index, code, gcmd)` — removes from in-memory list, clears persistence, calls `webhooks.call_remote_method('clear_exception', ...)`.
  - `has_exception(id, index, code)` → bool.
  - `get_status(eventtime)` → `{'exceptions': [...]}` for Moonraker subscriptions.
  - `save_persistent_exception` / `clear_persistent_exception` / `remove_persistent_exceptions` — JSON file I/O via `queuefile`.
- G-code commands:
  - `RAISE_EXCEPTION ID=<n> INDEX=<n> CODE=<n> [ONESHOT=1] [LEVEL=3] [IS_PERSISTENT=0] [MSG=<text>]`
  - `CLEAR_EXCEPTION ID=<n> INDEX=<n> CODE=<n>`
  - `QUERY_EXCEPTION` — prints all active exceptions in `LLLL-IIII-NNNN-CCCC` format.
  - `RM_EXCEPTION_PERSISTENT_FILE` — clears all persisted exceptions.
- `add_early_printer_objects(printer)` — installs `ExceptionManager` at printer startup.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `allow_moonraker_throw` is set only after `webhooks.has_remote_method('raise_exception')` returns `True`. During the first ~1 second of startup, exceptions are silently dropped to Moonraker (but still logged).
- Persistence file path is derived from `printer.get_snapmaker_config_dir()` which is a fork-only method on `Printer`. This file will not be created in stock Klipper.
- The `_handle_async_exception` timer uses a 1 ms delay between queued exceptions; a storm of exceptions (e.g. ADC spam) will cause many timer callbacks.
- `clear_exception` always calls `clear_persistent_exception` even when the exception is not in `self.exceptions`, which results in a redundant file I/O path.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/exception_manager.py
@@ -0,0 +1,~230 @@
+# New file – no upstream equivalent
+class ExceptionList:
+    MODULE_ID_MOTION = 522
+    MODULE_ID_GCODE  = 529
+    ...
+
+class ExceptionManager:
+    def __init__(self, printer): ...
+    def raise_exception_async(...): ...
+    def raise_exception(...): ...
+    def clear_exception(...): ...
+    def get_status(eventtime): ...
+    # G-code: RAISE_EXCEPTION, CLEAR_EXCEPTION, QUERY_EXCEPTION,
+    #         RM_EXCEPTION_PERSISTENT_FILE
+
+def add_early_printer_objects(printer):
+    printer.add_object('exception_manager', ExceptionManager(printer))
```

</details>
