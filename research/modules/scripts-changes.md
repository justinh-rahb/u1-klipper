# scripts/ — Script Changes

## Summary
The fork's `scripts/` directory is a snapshot of upstream Klipper scripts from the fork's base point, with three significant changes: `buildcommands.py` removes the `klippy/.version` file version fallback; `calibrate_shaper.py` is simplified to remove multi-dataset CSV support, matching the simplified `shaper_calibrate.py` API; and `graph_accelerometer.py` drops CSV output and simplifies its plotting API. Three upstream-only scripts are absent. All other scripts in the fork are functionally identical to their upstream counterparts at the fork's base commit.

## Changed From Upstream

### `scripts/buildcommands.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `file_version()` reads `klippy/.version` file to get version string | Removed; always uses `version = "?"` | Fork manages versioning differently; `.version` file may not exist in U1 deployment |

**Key diff:**
```diff
-def file_version():
-    if not os.path.exists('klippy/.version'):
-        return ""
-    ver = check_output("cat klippy/.version").strip()
-    return ver
-    version = file_version()
-    if not version:
-        version = "?"
+    version = "?"
```

### `scripts/calibrate_shaper.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Accepts CSV pre-processed frequency data or raw accelerometer data | Only accepts raw accelerometer data | Matches simplified `shaper_calibrate.py` API (no named datasets) |
| `import csv` | Removed | No CSV reading needed |
| `process_accelerometer_data(logname, data)` | `process_accelerometer_data(data)` — no `name` param | Matches fork's `shaper_calibrate.CalibrationData` API (name removed) |
| `CalibrationData(logname, ...)` named datasets | `CalibrationData(freq_bins, psd_sum, ...)` | API revert to match fork's `shaper_calibrate.py` |
| Multi-axis CSV output | Single-axis PSD only | Z-axis removed from resonance testing |

### `scripts/graph_accelerometer.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `plot_accel(opts, datas, lognames)` | `plot_accel(datas, lognames)` — `opts` removed | Simplified CLI handling |
| `calc_freq_response(name, data, max_freq)` | `calc_freq_response(data, max_freq)` — no `name` | Matches shaper_calibrate name removal |
| `plot_frequency(opts, datas, lognames, max_freq, axis)` | `plot_frequency(datas, lognames, max_freq)` | No opts; no axis param (Z removed) |
| `plot_specgram(opts, data, logname, max_freq, axis)` | `plot_specgram(data, logname, max_freq, axis)` | No opts |
| `write_frequency_response(lognames, datas, output)` | Present but simplified | |
| `import csv, importlib, optparse, os, sys` | `import importlib, optparse, os, sys` — no `csv` | CSV writing removed |
| `plot_compare_frequency()` absent | `plot_compare_frequency(datas, lognames, max_freq, axis)` added | New comparison plot function for U1 multi-extruder shaper comparison |

### CI/Install Scripts (minor)
Several CI scripts (`scripts/ci-build.sh`, `scripts/install-*.sh`) have minor divergences from upstream reflecting the fork's build environment (AT32 cross-compiler instead of ARM Cortex-M):
- `PKGS` list adds `pv libmpfr-dev libgmp-dev libmpc-dev texinfo bison flex` for building the RISC-V cross-compiler
- PRU toolchain URL updated (different archive naming)
- OR1K toolchain changed to use musl-cross variant

## Additions
- `scripts/graph_accelerometer.py`: `plot_compare_frequency(datas, lognames, max_freq, axis)` — new function for comparing frequency responses across multiple extruders

## Removals / Overrides
- `scripts/buildcommands.py`: `file_version()` function removed
- `scripts/calibrate_shaper.py`: CSV reading path, multi-dataset handling, `import csv`
- `scripts/graph_accelerometer.py`: `opts` parameter from multiple functions

**Upstream-only scripts not present in fork:**
- `scripts/check-software-div.sh` — compiler software division check
- `scripts/filter_workbench.ipynb` — Jupyter notebook for filter analysis
- `scripts/tests-requirements.txt` — Python test dependencies list

## Risks / Compatibility Notes
- `buildcommands.py` always reports `version = "?"` — `FIRMWARE_VERSION` in Klipper's startup log will always show `?` on fork builds
- `calibrate_shaper.py` will not accept pre-processed frequency CSV files that upstream expects — Z-axis data is silently ignored
- The missing `tests-requirements.txt` means the fork's test suite (`scripts/test_klippy.py`) cannot be set up from the scripts directory alone
- Any user running `scripts/graph_accelerometer.py` with upstream-style arguments (passing `opts` as first arg) will get incorrect results

## Raw Diff
<details>
<summary>View Diff (buildcommands.py)</summary>

```diff
-# Obtain version info from "klippy/.version" file
-def file_version():
-    if not os.path.exists('klippy/.version'):
-        logging.debug("No 'klippy/.version' file/directory found")
-        return ""
-    ver = check_output("cat klippy/.version").strip()
-    logging.debug("Got klippy version: %s" % (repr(ver),))
-    return ver
 ...
-        version = file_version()
-        if not version:
-            version = "?"
+        version = "?"
```
</details>
