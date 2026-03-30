# util.py

## Summary
`util.py` provides miscellaneous host-side utilities (version detection, CPU info, build info). The fork's key change is to replace `get_version_from_file()` with `get_full_firmware_version()` which reads `/etc/FULLVERSION` — a Snapmaker-specific file that contains the complete firmware version string. Three helper functions (`_try_read_file`, `get_device_info`, `get_linux_version`) are removed, and several file-read calls are inlined as `try/except` blocks. The rest of the version/build utilities are unchanged.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `_try_read_file(filename, maxsize)` utility for safe reads | Removed; replaced by inline `try/except open(...)` blocks at each call site | Minor refactoring |
| `get_device_info()` reads `/proc/device-tree/model` or `/sys/class/dmi/id/product_name` | Function removed; `start_args['device']` key not set | Not needed on Snapmaker hardware |
| `get_linux_version()` reads `/proc/version` | Function removed | Not logged in startup |
| `git_info["version"] = get_version_from_file(klippy_src)` | `git_info["version"] = get_full_firmware_version()` | Use Snapmaker firmware version |
| No `/etc/FULLVERSION` support | `get_full_firmware_version()` reads `/etc/FULLVERSION`, logs it, falls back to `"?"` | Snapmaker firmware ships a canonical version |

## Additions
- `get_full_firmware_version()` — reads `/etc/FULLVERSION` and returns its content; logs on success, logs error on failure, returns `"?"` on any exception.

## Removals / Overrides
- `_try_read_file(filename, maxsize=32*1024)` — removed; call sites use inline try/except.
- `get_device_info()` — removed.
- `get_linux_version()` — removed.

## Risks / Compatibility Notes
- `get_full_firmware_version()` returns `"?"` on any machine that does not have `/etc/FULLVERSION`. Moonraker and the UI will show `"?"` as the firmware version in those environments.
- `get_device_info()` and `get_linux_version()` are no longer called from `klippy.py`; removing them here is safe but breaks any external code that imports and calls them.
- Inline file-read blocks do not enforce the 32 KiB `maxsize` that `_try_read_file` used for `/proc/cpuinfo`. On systems with very large `/proc/cpuinfo`, this reads the entire file into memory.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/util.py
+++ b/klippy/util.py
@@ -54,9 -54 @@
-def _try_read_file(filename, maxsize=32*1024):
-    try:
-        with open(filename, 'r') as f:
-            return f.read(maxsize)
-    except (IOError, OSError) as e:
-        ...
-        return None

@@ -126,14 @@
-def get_device_info():
-    ...
-def get_linux_version():
-    ...

@@ -235 +225 @@
-    git_info["version"] = get_version_from_file(klippy_src)
+    git_info["version"] = get_full_firmware_version()
+
+def get_full_firmware_version():
+    try:
+        with open("/etc/FULLVERSION", "r") as f:
+            fullver = f.read().strip()
+        logging.info("Full firmware version: %s", fullver)
+        return fullver
+    except Exception as e:
+        logging.error("Error getting full firmware version: %s", e)
+    return "?"
```

</details>
