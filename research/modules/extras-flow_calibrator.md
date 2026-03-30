# flow_calibrator.py

## Summary
`flow_calibrator.py` implements `FlowCalibrator`, which performs automated pressure-advance (K factor) calibration by printing a test pattern and measuring the motor acceleration-time data via Klipper's `motion_report` trapeziodal queue. Two algorithms are supported: binary search (`DICHOTOMY`) and linear regression (`LINEAR_FITTING`). The module monitors extruder trapezoid move events (`trapq:extruder`) to capture acceleration ramps, feeds them to a compiled Cython extension (`flow_calculator`) for analysis, and persists the resulting K value to `flow_calibrator.json`. During printing it can run in-print calibration on each extruder and record whether calibration was performed for that print job.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automated in-print pressure-advance K calibration using acceleration-time data and a Cython flow calculator | U1 supports per-filament K-value auto-tuning at print start; upstream Klipper requires manual pressure advance tuning |

## Additions

### Classes
- **`AbortCalibration`** — Custom exception with a `message` field for clean calibration abort paths.
- **`AccelTimeQueryHelper`** — Collects `trapq:extruder` bulk sensor samples and extracts `(time, duration, start_velocity, acceleration)` tuples. Can write CSV for analysis.
- **`FlowCalibrator`** — Main extra loaded as `[flow_calibrator]`.

### G-code Commands
- **`FLOW_CALIBRATE`** — Run a full automatic K-factor calibration for the active extruder (prints test pattern, measures, applies result).
- **`FLOW_MEASURE_K`** — Measure K factor from existing printed pattern (no new print, just measurement).
- **`ACCEL_TIME_MEASURE`** — Start/stop raw acceleration-time data capture; writes CSV for offline analysis.
- **`FLOW_RESET_K`** — Reset all extruder K values to defaults and save.
- **`FLOW_APPLY_CALIBRATE_K`** — Apply the last calibrated K value to the extruder's pressure advance setting.

### Config Options
- `config_name` — JSON config file name (default `flow_calibrator.json`).
- `debug` (int, 0/1) — Enable debug mode (bypasses some guards).

### Persisted Config (`flow_calibrator.json`)
- `factor` — Dict mapping extruder names to K values: `{'extruder': 0.02, 'extruder1': 0.02, ...}`.
- `env` — Calibration environment parameters: `k_min`, `k_max`, `k_step`, `start_vel`, `start_dist`, `slow_vel`, `slow_dist`, `fast_vel`, `fast_dist`, `accel`, `loop`.

### Dependencies
- `flow_calculator` — Cython extension module (built by `extras/setup.py`).
- `motion_report.PrinterMotionReport` — For trapq sample subscription.

### Event Handlers
- `virtual_sdcard:reset_file` — Clears in-print calibration state.
- `pause_resume:cancel` — Aborts calibration.
- `filament_switch_sensor:runout` — Sets abort reason to `ABORT_REASON_FILAMENT_RUNOUT`.
- `filament_entangle_detect:tangled` — Sets abort reason to `ABORT_REASON_FILAMENT_TANGLED`.

### Abort Reasons
- `cancel_by_user`, `filament_runout`, `out_of_range`, `filament_tangled`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `flow_calculator` Cython extension to be compiled; without it the module fails to import. The `extras/setup.py` file handles the build.
- Requires `numpy` (`import numpy as np`) — not a standard Klipper dependency.
- Requires `queuefile` — a fork-specific Python extension.
- In-print calibration (`_calibrated_in_printing`) tracks state per print but does not handle multi-extruder sequential calibration robustly; only one calibration can be in progress at a time.
- The `_apply_k` method at startup calls `_set_pressure_advance` for all extruders in `extruder_list`, which is a fork-added printer object.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, multiprocessing, os, time, pathlib, queuefile
+from . import motion_report
+from . import flow_calculator
+import numpy as np, json
+
+ALGORITHM_TYPE_DICHOTOMY       = 'DICHOTOMY'
+ALGORITHM_TYPE_LINEAR_FITTING  = 'LINEAR_FITTING'
+
+DEFAULT_K = {'extruder': 0.02, 'extruder1': 0.02, 'extruder2': 0.02, 'extruder3': 0.02}
+DEFAULT_ENV = {'k_min': 0.005, 'k_max': 0.065, 'start_vel': 4, ...}
+
+class FlowCalibrator(object):
+    def __init__(self, config):
+        ...
+        self._gcode.register_command('FLOW_CALIBRATE', ...)
+        self._gcode.register_command('FLOW_MEASURE_K', ...)
+        self._gcode.register_command('ACCEL_TIME_MEASURE', ...)
+        self._gcode.register_command('FLOW_RESET_K', ...)
+        self._gcode.register_command('FLOW_APPLY_CALIBRATE_K', ...)
+
+def load_config(config):
+    return FlowCalibrator(config)
```
</details>
