# coded_exception.py

## Summary
A fork-exclusive module that introduces `CodedException`, a structured exception base class used throughout the Snapmaker U1 firmware layer. Every exception carries a machine-readable identity tuple (`id`, `index`, `code`), a severity `level`, behavioural flags (`oneshot`, `is_persistent`, `proactive_report`), and an optional `action` string. This allows the host software stack (Klipper → exception_manager → Moonraker) to route, deduplicate, and persist errors in a structured way rather than relying on free-form strings. Upstream Klipper has no equivalent; all errors are plain `Exception` subclasses or `configparser.Error`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Errors are plain Python `Exception` subclasses with a free-form string message | `CodedException` carries `id`, `index`, `code`, `level`, `oneshot`, `is_persistent`, `proactive_report` metadata | Enables structured error reporting to Moonraker/UI without string parsing |
| No error identity system | Errors have a numeric identity in the format `LLLL-IIII-NNNN-CCCC` (level-id-index-code) | Enables deduplication and persistence across restarts |
| N/A — new file | `from_exception()` class method wraps any plain exception in a `CodedException` | Lets older code that raises plain exceptions interoperate with the new system |

## Additions
- `CodedException` class — extends `Exception` with structured metadata fields.
  - Constructor parameters: `message`, `action`, `id`, `index`, `code`, `oneshot`, `level`, `is_persistent`, `proactive_report`
  - Default values: `id=522`, `index=0`, `code=0`, `level=3`, `oneshot=1`, `is_persistent=0`, `proactive_report=1`, `action='cancel'`
- `CodedException.to_dict()` — serialises all instance attributes to a `dict`.
- `CodedException.structured_code()` — returns the full `LLLL-IIII-NNNN-CCCC` string representation.
- `CodedException.basic_structured_code()` — returns the shorter `IIII-NNNN-CCCC` form used in persistence keys.
- `CodedException.from_exception(exc, **kwargs)` — class method that either returns `exc` unchanged if it is already a `CodedException`, or wraps a plain exception in a new `CodedException` with optional field overrides.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `gcode.CommandError`, `configfile.ConfigError`, `pins.error`, and `msgproto.error` all inherit from `CodedException`. Any code that catches `Exception` broadly will still work, but code specifically catching the original `Exception` types will now receive objects with extra fields.
- Default `id=522` maps to `MODULE_ID_MOTION` in `exception_manager.py`. If an exception is raised without overriding `id`, it will always appear as a motion-subsystem error in the UI.
- `proactive_report=1` means exceptions propagate to Moonraker by default. Setting it to `0` silences the report without preventing the exception from propagating in Python.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/coded_exception.py
@@ -0,0 +1,74 @@
+DEFAULT_ACTION = 'cancel'
+DEFAULT_MESSAGE = 'class CodedException'
+DEFAULT_ID = 522
+DEFAULT_INDEX = 0
+DEFAULT_CODE = 0
+DEFAULT_ONESHOT = 1
+DEFAULT_LEVEL = 3
+DEFAULT_PERSISTENT = 0
+DEFAULT_PROACTIVE_REPORT = 1
+
+class CodedException(Exception):
+    default_action = DEFAULT_ACTION
+    default_id = DEFAULT_ID
+    ...
+    def __init__(self, message, action, id, index, code, oneshot, level,
+                 is_persistent, proactive_report): ...
+    def to_dict(self) -> dict: ...
+    def structured_code(self) -> str: ...
+    def basic_structured_code(self) -> str: ...
+    @classmethod
+    def from_exception(cls, exc: Exception, **kwargs): ...
```

</details>
