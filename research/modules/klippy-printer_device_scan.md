# printer_device_scan.py

## Summary
A fork-exclusive utility script used during initial Snapmaker U1 machine setup to auto-detect and map physical MCU serial ports into `printer.cfg`. It scans USB devices for a CAN adapter (identified by the string `"Geschwister Schneider CAN adapter"`) to locate the main SoC MCU on `/dev/ttyS6`, and then probes `/dev/serial/by-id/` for up to four extruder MCUs identified by the `"usb-Klipper"` prefix. The results are written back into the relevant `[mcu]`/`[mcu E0]`–`[mcu E3]` sections of `printer.cfg`. The file contains substantial `TODO` comments indicating power-cycle and boot-pin sequencing that has not yet been implemented. It has no upstream equivalent and appears to be a standalone provisioning/factory-setup tool rather than a module loaded at runtime.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| N/A — no MCU auto-detection exists in upstream | `scan_mcu_device()` calls `lsusb` and `ls /dev/serial/by-id/` to locate up to 5 MCU serial ports | Automates printer setup for the U1's multi-MCU architecture (1 main + 4 extruder MCUs) |
| N/A | `update_printer_cfg()` reads and surgically rewrites `printer.cfg` to add/update `serial:` options | Avoids requiring manual config editing during provisioning |

## Additions
- `run_shell_command(command)` — thin wrapper around `subprocess.run`; returns `[returncode, stdout, stderr]`.
- `scan_mcu_device()` — detects up to 5 MCU serial paths and returns `[scan_count, main_mcu_path, e0_path, e1_path, e2_path, e3_path]`:
  - Main MCU: searches `lsusb` output for `SOC_MCU_STRING = "Geschwister Schneider CAN adapter"`; assigns `/dev/ttyS6`.
  - Extruder MCUs E0–E3: searches `/dev/serial/by-id/` for entries containing `EXTRUDER_MCU_STRING = "usb-Klipper"`.
- `update_printer_cfg(cfg_file_path, info_list, section_name_list, option)` — reads `printer.cfg` line-by-line, adding missing sections/options and updating out-of-date values for the `serial:` option in `[mcu]`, `[mcu E0]`, `[mcu E1]`, `[mcu E2]`, `[mcu E3]`.
- Module constants: `CFG_MCU_SECTION_NAME`, `SCAN_RESULT_MAP_INDEX`, `OPTION_NAME = 'serial'`.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- **Incomplete implementation**: boot-pin configuration and power-cycle sequencing are all stubbed out with `TODO` / `pass`. The current scan is passive (no hardware toggling), meaning it will only detect MCUs that are already powered and enumerated.
- Hardcodes `/dev/ttyS6` for the main MCU — this will silently produce a wrong path on any board where the SoC UART is mapped differently.
- `update_printer_cfg` uses a line-by-line text replacement strategy that may corrupt config files with unusual formatting or multi-line values.
- The file's `__main__` block calls `scan_mcu_device()` but the `update_printer_cfg` call is commented out, so running it directly makes no persistent change.
- Not loaded by any `[module]` section in the normal printer startup path; it is invoked externally during provisioning.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/printer_device_scan.py
@@ -0,0 +1,~110 @@
+# New file – no upstream equivalent
+SOC_MCU_STRING = "Geschwister Schneider CAN adapter"
+EXTRUDER_MCU_STRING = "usb-Klipper"
+
+def scan_mcu_device():
+    # scans lsusb + /dev/serial/by-id/ for up to 5 MCU serial ports
+    # TODO: power-cycle and boot-pin sequencing not yet implemented
+    ...
+
+def update_printer_cfg(cfg_file_path, info_list, section_name_list, option):
+    # surgically rewrites [mcu] / [mcu E0..E3] serial: options
+    ...
```

</details>
