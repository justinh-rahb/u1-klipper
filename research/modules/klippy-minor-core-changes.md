# Minor Core Changes (pins.py, mathutil.py, queuelogger.py, msgproto.py)

Upstream files with small diffs (fewer than ~20 substantive lines changed) are batched here.

---

## pins.py

### Summary
The only change is that `pins.error` now inherits from `CodedException` (via `from coded_exception import CodedException`) instead of the plain `Exception`. This makes all pin-configuration errors structurally typed so they can be routed through the `exception_manager`.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class error(Exception)` | `class error(CodedException)` | Uniform structured error reporting |

### Additions
- `from coded_exception import CodedException` import.

### Removals / Overrides
- None.

### Risks / Compatibility Notes
- Any code catching `pins.error` by type still works. Code catching bare `Exception` also still works. However, `isinstance(e, CodedException)` will now be `True` for pin errors.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/pins.py
+++ b/klippy/pins.py
@@ -6,0 +7 @@
+from coded_exception import CodedException
@@ -8 +9 @@
-class error(Exception):
+class error(CodedException):
```

</details>

---

## mathutil.py

### Summary
Two 3×3 matrix helper functions (`matrix_det` and `matrix_inv`) that exist in upstream Klipper have been removed from the fork. No new code was added to replace them. All other vector/matrix utilities (`matrix_cross`, `matrix_dot`, `matrix_mul`) remain. The removal is likely a code-cleanliness decision: none of the Snapmaker-specific extras modules use these functions.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `matrix_det(a)` computes 3×3 determinant | Function removed | Not used by any Snapmaker module |
| `matrix_inv(a)` computes 3×3 inverse using cofactors | Function removed | Not used by any Snapmaker module |

### Additions
- None.

### Removals / Overrides
- `matrix_det(a)` — upstream function removed.
- `matrix_inv(a)` — upstream function removed.

### Risks / Compatibility Notes
- Any extra module that calls `mathutil.matrix_det` or `mathutil.matrix_inv` will raise `AttributeError` at runtime. Stock Klipper extras that use these (e.g. certain bed-levelling helpers) would be broken if ported without re-adding the functions.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/mathutil.py
+++ b/klippy/mathutil.py
@@ -138,15 +137,0 @@
-######################################################################
-# Matrix helper functions for 3x3 matrices
-######################################################################
-
-def matrix_det(a):
-    x0, x1, x2 = a
-    return matrix_dot(x0, matrix_cross(x1, x2))
-
-def matrix_inv(a):
-    x0, x1, x2 = a
-    inv_det = 1. / matrix_det(a)
-    return [matrix_mul(matrix_cross(x1, x2), inv_det),
-            matrix_mul(matrix_cross(x2, x0), inv_det),
-            matrix_mul(matrix_cross(x0, x1), inv_det)]
```

</details>

---

## queuelogger.py

### Summary
The log rotation strategy has been changed from time-based (`TimedRotatingFileHandler` rotating at midnight, keeping 5 files) to size-based (`RotatingFileHandler` rotating at 10 MiB, keeping 15 files). Additionally, a custom `MillisecondFormatter` has been added to include milliseconds in every log timestamp (`HH:MM:SS.mmm`). The `setup_bg_logging` function now accepts a `maxBytes` parameter. These changes are consistent with an embedded system where wall-clock time may be unreliable but log verbosity is high.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `TimedRotatingFileHandler` rotates at midnight, keeps 5 backups | `RotatingFileHandler` rotates at 10 MiB, keeps 15 backups | Size-based rotation is more predictable on embedded systems |
| Timestamps use default `logging.Formatter` (no milliseconds) | `MillisecondFormatter` appends `.mmm` to every timestamp | Millisecond precision aids debugging of real-time events |
| `setup_bg_logging(filename, debuglevel)` | `setup_bg_logging(filename, debuglevel, maxBytes=FILE_SIZE)` | Allows caller to override log file size limit |

### Additions
- `FILE_SIZE = 10 * 1024 * 1024` (10 MiB) and `FILE_COUNT = 15` constants.
- `MillisecondFormatter` class — overrides `formatTime` to produce `HH:MM:SS.mmm` timestamps.

### Removals / Overrides
- `TimedRotatingFileHandler` base class replaced by `RotatingFileHandler`.
- `doRollover` still overridden but now calls `RotatingFileHandler.doRollover`.

### Risks / Compatibility Notes
- Log files no longer rotate at midnight; a long-running print could produce a single large file up to 10 MiB before rotation.
- 15 backups × 10 MiB = up to 150 MiB of log storage. On a memory-constrained device this could be significant.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/queuelogger.py
+++ b/klippy/queuelogger.py
@@ -7,0 +8,13 @@
+FILE_SIZE  = 10 * 1024 * 1024
+FILE_COUNT = 15
+
+class MillisecondFormatter(logging.Formatter):
+    def formatTime(self, record, datefmt=None):
+        ...
+        return "%s.%03d" % (s, (record.msecs % 1000))
+
@@ -24,4 +37,7 @@
-class QueueListener(logging.handlers.TimedRotatingFileHandler):
-    def __init__(self, filename):
-        logging.handlers.TimedRotatingFileHandler.__init__(
-            self, filename, when='midnight', backupCount=5)
+class QueueListener(logging.handlers.RotatingFileHandler):
+    def __init__(self, filename, maxBytes=FILE_SIZE, backupCount=FILE_COUNT):
+        logging.handlers.RotatingFileHandler.__init__(
+            self, filename, maxBytes=maxBytes, backupCount=backupCount)
+        formatter = MillisecondFormatter("%(asctime)s:%(message)s")
+        self.setFormatter(formatter)
```

</details>

---

## msgproto.py

### Summary
Two changes: (1) `msgproto.error` now inherits from `CodedException` instead of `Exception`, consistent with `pins.error` and `gcode.CommandError`; (2) the `create_dummy_response` method on `MessageParser` has been removed entirely; (3) a minor fix changes an empty-list return (`return []`) to an empty-string return (`return ""`) in the command-argument encoding path. The `create_dummy_response` removal is related to the removal of `DummyResponse` in `mcu.py`—the fork no longer supports the file-output debugging mode that used it.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class error(Exception)` | `class error(CodedException)` | Uniform structured error reporting |
| `MessageParser.create_dummy_response(msgname, params)` exists | Method removed | `DummyResponse` in `mcu.py` was also removed; file-output debug mode not supported |
| Command argument encoding returns `[]` on empty | Returns `""` | Likely a downstream consumers fix |

### Additions
- `from coded_exception import CodedException` import.

### Removals / Overrides
- `MessageParser.create_dummy_response(msgname, params={})` — 20-line method removed.

### Risks / Compatibility Notes
- Any code that calls `msgparser.create_dummy_response()` will raise `AttributeError`. This only mattered for the `DummyResponse` class in `mcu.py` which is also gone.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/msgproto.py
+++ b/klippy/msgproto.py
@@ -6,0 +7 @@
+from coded_exception import CodedException
@@ -26 +27 @@
-class error(Exception):
+class error(CodedException):
@@ -327 +328 @@
-            return []
+            return ""
@@ -356,20 +356,0 @@
-    def create_dummy_response(self, msgname, params={}):
-        ...
```

</details>
