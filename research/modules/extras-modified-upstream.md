# Major Upstream-Modified Extras

## Summary
Five upstream Klipper extras have been significantly rewritten in the fork to support Snapmaker U1 hardware features. The most extensive change is `virtual_sdcard.py`, which gains a comprehensive power-loss recovery (PLR) subsystem. `heaters.py` adds per-heater dynamic power limits and PID profiles. `probe.py` reverts newer upstream abstractions. `bed_mesh.py` integrates the inductance coil probe and adds new G-code commands. `resonance_tester.py` removes Z-axis vibration support and adds a fast state-machine calibration mode.

---

## `virtual_sdcard.py` — Power-Loss Recovery Engine

### Summary
The upstream virtual SD card module handles G-code file streaming from a directory. The fork transforms it into a comprehensive print job supervisor that continuously snapshots the full printer state (temperatures, positions, flow rates, fan speeds, mesh, tool assignments, pressure advance, object exclusions) to `/home/lava/printer_data/klippy/` so that a print can resume after power loss or shutdown.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Simple G-code line streaming from `path` directory | Same streaming plus continuous state serialisation to 10 JSON environment files | Power-loss recovery for U1 hardware |
| No tool-change awareness | Tracks `T0`–`T31` tool commands, pre-extrude logic, `NO_PRE_EXTRUDE_COMMANDS` set | U1 has up to 4 extruders (T0–T3) with complex tool-change protocol |
| G-code line not tracked | `self.lines` counter, `self.current_line_gcode`, per-line parsing via embedded `GCodeParser` | Needed to seek to resume line on recovery |
| No shutdown handler | Registers `klippy:shutdown` → `handle_shutdown()` | Flush PLR state on unexpected shutdown |
| Standard `_reset_file()` | `exit_to_idle(rm_pl_env_file)`, `_pl_recovery_reset_file()`, `_reset_file()` with PLR cleanup | Maintain separation between normal end vs recovery reset |
| No MCU flash interaction | Registers `power_loss_check:mcu_update_complete` → `handle_get_mcu_pl_flash_data()`, calls `notify_mcu_enable_power_loss()` | Reads/writes stepper Z position to MCU flash via `power_loss_check` |

### Additions
**New constants (all paths under `/home/lava/printer_data/klippy/`):**
- `PL_RECORD_FILE_DIR`, `PL_PRINT_FILE_ENV`, `PL_PRINT_FILE_MOVE_ENV`, `PL_PRINT_TEMPERATURE_ENV`, `PL_PRINT_FLOW_AND_SPEED_FACTOR_ENV`, `PL_PRINT_PRESSURE_ADVANCE_ENV`, `PL_PRINT_LAYER_INFO_ENV`, `PL_PRINT_FAN_INFO_ENV`, `PL_PRINT_Z_ADJUST_POSITION_ENV`, `PL_PRINT_OBJECTS_ENV`, `PL_PRINT_EXCLUDE_OBJECTS_ENV`
- `MAX_TOOL_NUMBER = 32`, `GENERIC_MOVE_GCODE`, `TOOL_CHANGE_COMMANDS`, `NO_PRE_EXTRUDE_COMMANDS`, `USE_REALTIME_TEMP_GCODE`

**New G-code commands:**
- `SDCARD_PRINT_TEST` — internal test hook
- `SDCARD_PRINT_PL_RESTORE` — trigger power-loss restore sequence
- `SDCARD_PRINT_PL_CLEAR_ENV` — clear all PLR environment files

**New public methods (PLR API used by other modules):**
- `record_pl_print_file_env()`, `force_record_pl_print_file_env()`, `get_pl_print_file_env()`
- `record_pl_print_temperature_env()`, `get_pl_print_temperature_env()`
- `record_pl_print_flow_and_speed_factor()`, `get_pl_print_flow_and_speed_factor()`
- `record_pl_print_pressure_advance()`, `get_pl_print_pressure_advance()`
- `record_pl_print_layer_info()`, `get_pl_print_layer_info()`
- `record_pl_print_fan_env()`, `get_pl_print_fan_env()`
- `record_pl_print_z_adjust_position()`, `get_pl_print_z_adjust_position()`, `rm_pl_print_z_adjust_position()`
- `record_pl_print_file_move_env()`, `parse_power_loss_move_env()`, `pl_find_latest_move_env()`
- `record_pl_print_objects_env()`, `get_pl_print_objects_env()`
- `record_pl_print_exclude_objects_env()`, `get_pl_print_exclude_objects_env()`
- `notify_mcu_enable_power_loss()`, `config_pl_allow_save_env()`
- `backup_print_env_info()`, `power_loss_info_check()`, `rm_power_loss_info()`
- `restore_print()`, `pl_bed_mesh_restore()`, `flush_pl_print_env()`
- `save_environment_data()` — atomic write via `queuefile`
- `get_pl_env_flag()`, `_valid_power_loss_condition()`, `_valid_power_loss_condition_with_pause()`
- `wait_until_not_homing()`

**New embedded class `GCodeParser`:** Stateful per-line G-code parser used during streaming to track positions, speeds, temperatures, flow factors, and objects for PLR snapshotting.

### Risks / Compatibility Notes
- Hard-coded path `/home/lava/printer_data/klippy/` — fails on non-U1 systems unless `printer.get_snapmaker_config_dir()` fallback works
- Uses `queuefile` (fork-exclusive) for async atomic JSON writes
- Depends on `power_loss_check` extra (fork-exclusive); `power_loss_check:mcu_update_complete` event will never fire on upstream
- The `GCodeParser` duplicates some gcode parsing logic, creating a maintenance risk if upstream `gcode.py` changes its command format
- `SDCARD_PRINT_PL_RESTORE` bypasses normal `SDCARD_RESET_FILE` flow — callers must use the correct restore sequence

### Raw Diff
<details>
<summary>View Diff (first 120 lines)</summary>

```diff
--- a/klippy/extras/virtual_sdcard.py
+++ b/klippy/extras/virtual_sdcard.py
+import json, re, copy, tarfile, threading, queuefile
+MAX_TOOL_NUMBER = 32
+GENERIC_MOVE_GCODE = {'G0', 'G1', 'G2', 'G3'}
+TOOL_CHANGE_COMMANDS = {f'T{i}' for i in range(MAX_TOOL_NUMBER)}
+NO_PRE_EXTRUDE_COMMANDS = TOOL_CHANGE_COMMANDS | {'BED_MESH_CALIBRATE'}
+USE_REALTIME_TEMP_GCODE = {'BED_MESH_CALIBRATE'}
+PL_RECORD_FILE_DIR = "/home/lava/printer_data/klippy"
+PL_PRINT_FILE_ENV = "pl_print_file_env.json"
+# ... 9 more PL_PRINT_*_ENV constants ...
+        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
+        self.printer.register_event_handler("power_loss_check:mcu_update_complete",
+                                            self.handle_get_mcu_pl_flash_data)
+        self.pl_switch = False
+        self.pl_mcu_flash_valid_line = 0xFFFFFFFF
+        self.pl_mcu_flash_stepper_z_pos = 0xFFFFFFFF
+        self.pl_mcu_flash_resume_line = 0xFFFFFFFF
```
</details>

---

## `heaters.py` — Dynamic Power Limits & PID Profiles

### Summary
The fork modifies the core heater control module to add per-heater dynamic maximum power limits (enabling reduced power in idle/active states) and a JSON-backed PID profile store (`SET_PID_PROFILE`). It also relaxes the fault detection timeout from 3 s to 7 s, adds temperature overshoot allowances, and changes the PWM update threshold variable name.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `MAX_HEAT_TIME = 3.0` (PWM output watchdog) | `MAX_HEAT_TIME = 7.0` | U1 extruders have higher thermal mass; 3 s caused false watchdog trips |
| `MAX_MAINTHREAD_TIME = 5.0`, `QUELL_STALE_TIME = 7.0` | Removed; replaced with `READ_TIME_TOL = 0.45`, `MIN_UPDATE_RATIO = 0.15` | Different sensor update scheduling approach |
| `MIN_PWM_CHANGE_RATIO = 0.05` | `pwm_min_set_diff` config option (default 0.05) | Made configurable per-heater |
| Fixed `min_temp`/`max_temp` bounds | `min_temp_overshoot` and `max_temp_overshoot` config options expand bounds | Allows small thermal excursion without fault during tool changes |
| Single fixed `max_power` | `idle_hold_max_power`, `active_hold_max_power` config options + `set_dynamic_max_power()` | U1 uses lower power for idle extruders to reduce heat creep |
| No PID profile management | `SET_PID_PROFILE HEATER=<name> [PROFILE=<name>]` G-code + JSON file backing | Allows pre-calibrated PID sets per material/tool |

### Additions
**New config options** (per `[extruder]`/`[heater_bed]` section):
- `min_temp_overshoot`: float, default 0 — extends min_temp check downward
- `max_temp_overshoot`: float, default 0 — extends max_temp check upward
- `idle_hold_max_power`: float 0–1, optional — max PWM when heater is idle
- `active_hold_max_power`: float 0–1, optional — max PWM when heater is printing
- `pwm_min_set_diff`: float, default 0.05 — minimum PWM delta before update
- `allow_pid_calibrate`: bool, default True — whether `PID_CALIBRATE` is permitted

**New G-code command:**
- `SET_PID_PROFILE HEATER=<name> PROFILE=<name>` — load a named PID profile from JSON

**New methods:**
- `get_dynamic_max_power()` / `set_dynamic_max_power(power, delay_increase=True)`
- `cmd_SET_PID_PROFILE()`, `set_pid_profile()`
- `_load_heater_pid_profiles_from_json()`, `_save_heater_pid_profiles_to_json()`
- `_validate_pid_profile()`
- `update_pending_extruder()`, `remove_pending_extruder()` — heating queue management

### Risks / Compatibility Notes
- `MAX_HEAT_TIME = 7.0` means the PWM watchdog allows 7 s between heater callbacks; upstream uses 3 s — this increases risk of thermal runaway going undetected on non-U1 hardware
- `allow_pid_calibrate = False` silently prevents `PID_CALIBRATE` without error; could confuse users unaware of the option
- PID profile JSON format is undocumented; if the JSON is corrupted, heater init will fail

### Raw Diff
<details>
<summary>View Diff (key additions)</summary>

```diff
-MAX_HEAT_TIME = 3.0
+MAX_HEAT_TIME = 7.0
+        min_temp_overshoot = config.getfloat('min_temp_overshoot', 0, minval=0)
+        max_temp_overshoot = config.getfloat('max_temp_overshoot', 0, minval=0)
+        self.sensor.setup_minmax(self.min_temp - min_temp_overshoot,
+                                 self.max_temp + max_temp_overshoot)
+        self.idle_hold_max_power = config.getfloat('idle_hold_max_power', None, above=0., maxval=1.)
+        self.active_hold_max_power = config.getfloat('active_hold_max_power', None, above=0., maxval=1.)
+        self.allow_pid_calibrate = config.getboolean('allow_pid_calibrate', True)
+        gcode.register_mux_command("SET_PID_PROFILE", "HEATER",
+                                   short_name, self.cmd_SET_PID_PROFILE, ...)
```
</details>

---

## `probe.py` — ProbeResult Removal & API Simplification

### Summary
The fork reverts upstream's introduction of `manual_probe.ProbeResult` namedtuple and the `can_set_z_offset` guard on `PROBE_CALIBRATE`/`Z_OFFSET_APPLY_PROBE`. It returns plain `list` from `_calc_mean_position()` instead of a named tuple, and simplifies `ProbeSessionHelper.__init__`.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `_calc_mean_position()` returns `ProbeResult` namedtuple with `.bed_x`/`.bed_y`/`.bed_z` | Returns plain `list` of 3 floats indexed by `[2]` etc. | Fork diverged before ProbeResult was introduced |
| `ProbeSessionHelper.__init__` takes `can_set_z_offset=True` flag | No `can_set_z_offset` param; `PROBE_CALIBRATE`/`Z_OFFSET_APPLY_PROBE` always registered | Fork does not use the can_set_z_offset gate |
| `self.last_probe_position = gcode.Coord(...)` | `self.probe_calibrate_z = 0.` | Simpler scalar tracking |
| `self.probe_calibrate_info` dict | Removed | Not needed without ProbeResult |

### Additions
- `probing_coil_move(mcu_probe, pos, speed)` — custom move method used by inductance coil probe (calls `homing.probing_coil_move`)

### Removals / Overrides
- `ProbeResult` namedtuple usage (replaced with plain list)
- `can_set_z_offset` constructor parameter
- `self.probe_calibrate_info` tracking dict

### Risks / Compatibility Notes
- Any plugin calling `result.bed_z` on a probe result will get `AttributeError` — incompatible with upstream extras that expect `ProbeResult`
- The `position[2]` indexing is fragile if position list length ever changes

### Raw Diff
<details>
<summary>View Diff (key changes)</summary>

```diff
-        inv_count = 1. / float(len(positions))
-        return manual_probe.ProbeResult(
-            *[sum([pos[i] for pos in positions]) * inv_count for i in range(len(positions[0]))])
+        count = float(len(positions))
+        return [sum([pos[i] for pos in positions]) / count for i in range(3)]
-    z_sorted = sorted(positions, key=(lambda p: p.bed_z))
+    z_sorted = sorted(positions, key=(lambda p: p[2]))
-    def __init__(self, config, probe, query_endstop=None, can_set_z_offset=True):
+    def __init__(self, config, probe, query_endstop=None):
```
</details>

---

## `bed_mesh.py` — Inductance Coil Integration & New Commands

### Summary
The fork integrates the inductance coil probe as an alternative bed-levelling sensor, adds three new G-code commands for the U1 calibration workflow, adds a `BedMeshProbeState` management class, and changes persistent profile storage from Klipper's `save_variables` to custom JSON files (one per profile, stored on disk). It also imports `probe_inductance_coil` (fork-exclusive) and adds an abort mechanism accessible via Moonraker webhooks.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Only standard probe or eddy current probe | Also supports `inductance_coil` probe via `is_inductance_coil_probe` flag | U1 uses inductive probes for bed levelling |
| Single `BedMeshCalibrate` class | Added `BedMeshProbeState` class with state tracking | Multi-step calibration workflow for U1 |
| No webhook abort | `_handle_abort_probe_mesh` registered on `webhooks` endpoint | Allow Moonraker/UI to cancel in-progress mesh calibration |
| No profile file output | `BED_MESH_OUTPUT_FILE` G-code dumps grid to file | Allows logging/saving mesh data externally |
| Profiles saved via Klipper's config system | `_save_profile_custom()` / `_load_profile_custom()` / `_remove_profile_custom()` using JSON files | Fork-specific storage path outside Klipper config |
| No manual levelling check | `check_manual_leveling_needed()`, `BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED` | U1 workflow requires tram check before mesh |
| `import probe` only | `from . import probe, probe_inductance_coil` | Needed for inductance coil probe helper |

### Additions
**New constants:**
- `BED_VERSION_202507_OEM = "/oem/.bed_202507"` — hardware version sentinel file
- `BED_VERSION_202507_UDATA = "/userdata/.bed_202507"` — user data hardware version sentinel

**New exception class:**
- `BedMeshActiveAbort` — raised when bed mesh calibration is aborted mid-run

**New G-code commands:**
- `BED_MESH_OUTPUT_FILE` — dump current mesh interpolated grid to a file
- `BED_MESH_CALIBRATE_PREPARE` — prepare state for upcoming calibration run
- `BED_PRELEVELING_SCAN` — perform pre-levelling inductance scan
- `BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED` — clear the "needs manual levelling" flag

**New webhook endpoint:**
- `handle: _handle_abort_probe_mesh` — cancels active calibration via Moonraker

**New class `BedMeshProbeState`:** Manages state for multi-step calibration sequences including `probe_point_callback()`, `abort_probe()`, `check_manual_leveling_needed()`, `print_probed_matrix()`, and custom profile I/O.

### Risks / Compatibility Notes
- `from . import probe_inductance_coil` will fail on upstream Klipper (module doesn't exist)
- Custom profile JSON files at undocumented paths won't be imported by standard Klipper profile management
- `BedMeshActiveAbort` exception bypasses normal error handling path
- Typo in comments (`retreive commma`) from fork revert of upstream comment fixes

### Raw Diff
<details>
<summary>View Diff (key additions)</summary>

```diff
+import logging, math, json, collections, os, queuefile
+from . import probe, probe_inductance_coil
+BED_VERSION_202507_OEM   = "/oem/.bed_202507"
+BED_VERSION_202507_UDATA = "/userdata/.bed_202507"
+class BedMeshActiveAbort(Exception):
+    pass
+        self.gcode.register_command('BED_MESH_OUTPUT_FILE', ...)
+        self.gcode.register_command('BED_MESH_CALIBRATE_PREPARE', ...)
+        self.gcode.register_command('BED_PRELEVELING_SCAN', ...)
+        self.gcode.register_command('BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED', ...)
+        webhooks.register_endpoint(...)  # abort handler
+        if config.get_prefix_sections("inductance_coil"):
+            self.is_inductance_coil_probe = True
+            self.probe_helper = probe_inductance_coil.ProbePointsHelper(...)
```
</details>

---

## `resonance_tester.py` — Z-Axis Removal & Fast Shaper Calibration

### Summary
The fork removes Z-axis vibration testing (all vibration directions are reduced from 3D to 2D), removes the `SweepingVibrationsTestGenerator` class and `ResonanceTestExecutor` class, renames `VibrationPulseTestGenerator` to `VibrationPulseTest`, and adds a state machine (`STATE_IDLE`/`STATE_SHAPER_CALIBRATING`/`STATE_COMPLETED`/`STATE_FAILED`) plus a new `SM_FAST_SHAPER_CALIBRATE` command for automated one-shot calibration.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Vibration axes are 3D tuples `(x, y, z)` | Vibration axes are 2D tuples `(x, y)` | U1's LIS2DW accelerometers mounted on print heads; Z not relevant for XY corexy shaping |
| `vib_dir` format: `(1., 0., 0.)` for X | `vib_dir` format: `(1., 0.)` for X | Consistent with 2D removal |
| `chip_axis` Z check `if self._vib_dir[2] and 'z' in chip_axis` | Removed Z check | No Z-axis vibration testing |
| `VibrationPulseTestGenerator` class | Renamed to `VibrationPulseTest` | Simplification (no longer "generator" pattern) |
| `SweepingVibrationsTestGenerator` class | Removed | Fork does not support sweep mode |
| `ResonanceTestExecutor` class | Removed | Replaced by simplified state machine approach |
| `import itertools` | Removed | Not needed after removal of zip-grouped chip iteration |
| No state management | `STATE_IDLE/SHAPER_CALIBRATING/COMPLETED/FAILED` string constants + `self.state` | Moonraker can poll `get_status()` to track calibration progress |
| `get_status()` returns basic info | Returns `{'state': ..., ...}` | Exposes state to Fluidd/Mainsail UI |

### Additions
- `STATE_IDLE`, `STATE_SHAPER_CALIBRATING`, `STATE_COMPLETED`, `STATE_FAILED` — state constants
- `SM_FAST_SHAPER_CALIBRATE` G-code command — performs automated X+Y shaper calibration in sequence
- `cmd_SM_FAST_SHAPER_CALIBRATE()` — implementation
- `check_homed()` — pre-check that axes are homed before calibration
- `_run_test()` — internal helper wrapping the calibration sequence
- `get_status()` — now returns `state` field for Moonraker status polling

### Removals / Overrides
- `VibrationPulseTestGenerator` → `VibrationPulseTest` (rename)
- `SweepingVibrationsTestGenerator` class removed
- `ResonanceTestExecutor` class removed
- Z-axis support removed from all vibration direction tuples
- `itertools` import removed

### Risks / Compatibility Notes
- Z-axis shaper tuning completely unavailable — if upstream Z motion compensation features are used with this fork, they will fail silently or error
- `SM_FAST_SHAPER_CALIBRATE` is U1-specific and requires the LIS2DW accelerometers to be properly configured
- Removal of `SweepingVibrationsTestGenerator` means `TEST_RESONANCES SWEEP=1` (if present in user configs) will error

### Raw Diff
<details>
<summary>View Diff (key changes)</summary>

```diff
-import itertools, logging, math, os, time
+import logging, math, os, time
+STATE_IDLE                              = 'idle'
+STATE_SHAPER_CALIBRATING                = 'shaper_calibrating'
+STATE_COMPLETED                         = 'completed'
+STATE_FAILED                            = 'failed'
-class VibrationPulseTestGenerator:
+class VibrationPulseTest:
-class SweepingVibrationsTestGenerator:
-class ResonanceTestExecutor:
-            self._vib_dir = [(1., 0., 0.), (0., 1., 0.), (0., 0., 1.)][ord(axis)-ord('x')]
+            self._vib_dir = (1., 0.) if axis == 'x' else (0., 1.)
-    return TestAxis(vib_dir=(dir_x, dir_y, dir_z))
+    return TestAxis(vib_dir=(dir_x, dir_y))
+        self.gcode.register_command("SM_FAST_SHAPER_CALIBRATE",
+                                    self.cmd_SM_FAST_SHAPER_CALIBRATE, ...)
```
</details>
