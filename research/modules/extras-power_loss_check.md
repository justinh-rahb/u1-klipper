# power_loss_check.py

## Summary
`power_loss_check.py` implements `PowerLossCheck`, a Klipper extra that interfaces with a custom MCU firmware command set (`config_power_loss_check`) to monitor mains voltage via a GPIO line, detect power loss events, and support power-loss resume (PLR). The MCU measures the duty cycle of a mains-frequency sense signal to distinguish 110 V (~50% duty in a different voltage range) from 220 V supply, and sets a `power_loss_flag` when the signal disappears. On detection, Klipper is shut down with a structured error code. For 220 V supplies the module can automatically switch the bed heater PID profile (`pid2`). It also queries and stores the MCU's flash-saved stepper positions from the last print for PLR restoration.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: hardware mains-voltage monitoring with 110/220 V auto-detection, MCU-side PLR flash save, and automatic bed PID switching | U1 is sold in both 110 V and 220 V markets; the MCU saves critical position data on power loss; Klipper must read this to enable power-loss resume |

## Additions

### Classes
- **`PowerLossCheck`** — Klipper extra loaded via both `load_config` (as `[power_loss_check]`) and `load_config_prefix` (as `[power_loss_check <name>]`). Multiple instances are tracked in a shared `power_loss_check_list` object.

### G-code Commands (master instance only)
- **`UPDATE_POWER_LOSS_REPORT_INTERVAL INTERVAL=<f>`** — Update MCU reporting interval.
- **`QUERY_POWER_LOSS_CHECK_INFO`** — Query and display current voltage type, duty cycle, and power-loss flag.
- **`ENABLE_POWER_LOSS_REPORT_LOG ENABLE=<0|1>`** — Toggle verbose MCU status output to G-code console.

### G-code Commands (all instances, multiplexed by `NAME=<name>`)
- **`ENABLE_POWER_LOSS NAME=<name> ENABLE=<0|1> [PRINT_FLAG=<u32>] [MOVE_LINE=<u32>]`** — Enable/disable power-loss monitoring on the MCU; sets the print-flag and current move line for PLR.
- **`QUERY_POWER_LOSS_FLASH_VALID NAME=<name>`** — Query MCU flash validity info (last sequence, valid sector count, env flag, saved stepper count).
- **`QUERY_POWER_LOSS_STEPPER_INFO NAME=<name> [TYPE=<u8>] [INDEX=<u8>]`** — Retrieve saved stepper position from flash.

### Key Config Options
- `pin` — GPIO sense pin for mains monitoring (supports invert/pullup).
- `power_loss_trigger_time` (float, default 0.0109 s) — Minimum signal-loss duration before declaring power loss.
- `report_interval` (int, default 0) — MCU periodic report interval in seconds.
- `duty_threshold` (float, default 0.54) — Duty cycle threshold for voltage type detection.
- `debounce_threshold` (int, default 20) — MCU debounce count.
- `type_confirm_threshold` (int, default 3) — Consecutive samples needed to confirm voltage type.
- `bed_pid_control_mode` (str, `'auto_switch'`|`'pid2'`|`'default'`) — Master only: bed PID switching mode.

### MCU Commands Used
- `config_power_loss_check`, `update_report_interval`, `enable_power_loss`
- `query_power_loss_status`, `query_power_loss_flash_valid`, `query_power_loss_stepper_info`

### Events
- `power_loss_check:mcu_update_complete` — Fired after all instances have read their flash data on startup.

### Auto PID Switching
On `klippy:ready`, the master instance starts a timer that monitors `voltage_type` and automatically issues `SET_PID_PROFILE HEATER=heater_bed PROFILE=pid2` when 110 V is detected.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires custom MCU firmware commands not present in upstream Klipper; will fail at MCU identify if the firmware does not support them.
- On power-loss detection, `printer.invoke_shutdown` is called with a JSON-encoded error — a Snapmaker-specific extension of the normal `invoke_shutdown(msg)` API.
- The shared `power_loss_check_list` object uses `printer.add_object` / `printer.lookup_object` without a formal Klipper config section, which is unconventional and may conflict if the object name is reused.
- `ctypes.c_int32` is used to sign-extend MCU stepper position values — correct on all platforms but an unusual pattern in Klipper code.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Power loss detection handling
+import logging, copy, ctypes
+import pins, stepper
+
+class PowerLossCheck:
+    def __init__(self, config):
+        ...
+        self._mcu.add_config_cmd(
+            "config_power_loss_check oid=%d clock=%u power_loss_trigger_time=%u ...")
+        # Register MCU responses
+        self._mcu.register_response(self.handle_report_power_loss_status,
+                            "report_power_loss_status", self._oid)
+        # G-code commands (master)
+        gcode.register_command('UPDATE_POWER_LOSS_REPORT_INTERVAL', ...)
+        gcode.register_command('QUERY_POWER_LOSS_CHECK_INFO', ...)
+        # G-code commands (all instances)
+        gcode.register_mux_command("ENABLE_POWER_LOSS", "NAME", ...)
+        gcode.register_mux_command("QUERY_POWER_LOSS_FLASH_VALID", "NAME", ...)
+
+def load_config(config): ...
+def load_config_prefix(config): ...
```
</details>
