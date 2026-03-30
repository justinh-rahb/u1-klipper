# extruder_calibration.py

## Summary
`extruder_calibration.py` implements `ExtruderParkCalibration`, which calibrates the XY park (docking) position of each extruder on the U1's tool-changer carriage. It probes the mechanical slot/aperture that each extruder docks into using the fork's probe framework (`probe_inductance_coil.run_single_probe`), measures the contact position from two sides, and computes the centre point. For `probe_mode=1` (two-sided), it drives the probe in one direction, records first contact, reverses and records second contact, then averages for the true centre. Results are validated against optional `theoretical_position` and `tolerance` bounds. On success, results are written to a calibration log and can be persisted to the extruder backup config.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automated tool-changer dock-slot probing to calibrate extruder XY park positions | U1 is a tool-changer printer; each extruder must be precisely calibrated to its dock slot; upstream Klipper has no tool-changer docking calibration |

## Additions

### Classes
- **`ExtruderParkCalibrationStep`** — State constants: `PROBING_IDLE`, `PROBING_START`, `PROBING_COMPLETE`, `PROBING_ERROR`.
- **`ExtruderParkCalibration`** — Klipper extra loaded as `[extruder_calibration]`.

### G-code Commands
- **`CALIBRATE_EXTRUDER_PARK_POSITION [ENABLE_THEORETICAL_CHECK=1] [extruder_START_X=<f>] [extruder_START_Y=<f>] ...`** — Run the full calibration sequence for all configured extruders. Supports per-extruder start position overrides via G-code parameters.
- **`PROBE_SINGLE_POINT`** — Single probing move for debugging/testing.

### Key Config Options (per extruder section)
- `extruder_start_position` — XY start position for this extruder's probe (required for each extruder).
- `extruder_probe_aperture` — Width of the dock slot (float, default 5.3 mm).
- `extruder_probe_direction` — Initial probe direction (0 or 1).
- `extruder_reverse_distance` — Distance to reverse between first and second contact.
- `extruder_probe_dist` — Total probe travel distance.
- `extruder_result_offset` — Fixed offset applied to the computed position.
- `extruder_theoretical_position` — Expected result; used for bounds checking.
- `extruder_tolerance` — Max deviation from theoretical before raising an error.
- `extruder_probe_mode` (0=single-side, 1=two-sided)
- `extruder_polarity_invert` — Invert probe trigger polarity.
- `extruder_y_cal_second_position` — Optional second position for Y-axis calibration.

### Shared Config Options
- `speed`, `probe_fast_speed`, `lift_speed` — Motion speeds.
- `accel` — Probe acceleration.
- `samples`, `sample_retract_dist`, `samples_tolerance`, `samples_tolerance_retries`
- `save_result` — Whether to persist calibration results to JSON.
- `y_cal_enable` — Enable Y-axis secondary calibration.
- `analog_output_pin`, `analog_range`, `analog_pullup_resistor` — ADC button for laser-based position sensing.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires extruder objects with `get_extruder_activate_status()` and `cmd_SWITCH_EXTRUDER_ADVANCED()` — fork-specific extruder methods.
- Calibration log directory falls back to `/tmp/calibration_data` if no virtual_sdcard is found — a path that may be unavailable or undesirable.
- The two-sided probing algorithm assumes the slot is symmetric and perfectly aligned with the probe axis; any angular misalignment will introduce systematic error.
- `probe_mode` configuration key is accidentally read as `'_probe_mode'` (with underscore prefix) for the per-extruder override — likely a bug.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Extruder Park Calibration module for Klipper
+import logging, os, queuefile, copy
+from . import probe, probe_inductance_coil
+
+class ExtruderParkCalibrationStep:
+    PROBING_IDLE = "idle"; PROBING_START = "probing"
+    PROBING_COMPLETE = "complete"; PROBING_ERROR = "error"
+
+class ExtruderParkCalibration:
+    def __init__(self, config):
+        ...
+        # Read per-extruder positions from config
+        for i in range(99):
+            section = 'extruder' if not i else 'extruder%d' % i
+            pos = config.getlists(section + '_start_position', ...)
+            if pos is not None:
+                self.extruder_start_positions[section] = ...
+            else:
+                break
+        self.gcode.register_command(
+            'CALIBRATE_EXTRUDER_PARK_POSITION', ...)
+        self.gcode.register_command('PROBE_SINGLE_POINT', ...)
+
+def load_config(config):
+    return ExtruderParkCalibration(config)
```
</details>
