# homing_precise_corexy.py

## Summary
`homing_precise_corexy.py` implements `HomingPreciseCorexy`, a specialised post-homing refinement for CoreXY kinematics on the U1. After a standard G28 homes both XY axes against their endstops, this module performs a diagonal probing move (using the TMC phase position) to precisely determine the stepper phase offset. The phase data is used to sub-step-correct the homed position so that the machine homes to a reproducible electrical phase boundary rather than the less repeatable mechanical endstop. Optionally, a saved calibration origin (`homing_calibrated_origin.json`) can be loaded to further correct the coordinate system. The module also validates the result across multiple probe attempts.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: TMC phase-based post-homing position refinement for CoreXY, with optional calibrated-origin correction and result validation | U1 requires sub-step homing repeatability for multi-extruder tool-change accuracy; standard endstop homing has ±half-step positional jitter |

## Additions

### Classes
- **`HomingPreciseCorexy`** — Klipper extra loaded as `[homing_precise_corexy]`.

### G-code Commands
- **`HOMING_PRECISE_COREXY`** — Run the standard precise homing procedure (uses saved calibrated origin if available).
- **`HOMING_PRECISE_COREXY_ADVANCED`** — Extended version with additional parameters for debugging.
- **`ENTER_HOMING_ORIGIN_CALIBRATION`** — Enter calibration mode to measure and save a new origin.
- **`EXIT_HOMING_ORIGIN_CALIBRATION`** — Exit calibration mode.

### Key Config Options
- `xy_back_offset` (float, default 5 mm) — Back-off distance from endstop before diagonal probing.
- `diagonal_probe_before_delay` (float, s) — Dwell before each diagonal probe.
- `diagonal_probe_samples` (int, ≥2) — Number of probe samples for averaging.
- `diagonal_probe_tolerance` (float) — Max deviation between samples.
- `diagonal_probe_accel` (float) — Probe acceleration.
- `diagonal_probe_speed` (float) — Probe speed.
- `diagonal_probe_retract_speed` (float) — Retract speed.
- `diagonal_probe_tolerance_retries` (int) — Retry count on tolerance failure.
- `diagonal_move_rail` (int, 0=A-motor, 1=B-motor, default 1) — Which CoreXY motor moves during diagonal probe.
- `use_calibration_origin` (bool, default False) — Apply saved origin correction.
- `enable_home_validation` (bool, default False) — Validate result with extra probes.
- `use_float_calc` (bool, default False) — Use floating-point distance calculation instead of integer-phase.
- `validation_retries` (int, default 3)

### Key Methods
- `diagonal_probe(endstops, movepos)` — Executes a `HomingMove` diagonally and returns endstop trigger position + MCU step counts.
- `cal_diagonal_dist(m_steps)` — Computes calibrated A/B motor distances from raw step counts (integer phase method).
- `cal_diagonal_dist_float(m_steps)` — Floating-point alternative.
- `phase_backoff_steps(corexy_rails)` → `(x_steps, y_steps)` — Computes phase-aligned backoff distances.
- `translate_to_ab_grid(c_dist, origin)` — Converts fractional phase distances to integer grid positions.
- `load_calibrated_origin()` — Reads `homing_calibrated_origin.json` from persistent config dir.

### Calibration Data File
`homing_calibrated_origin.json` — Contains version, A/B phase origin values; version must be ≥ `MIN_SUPPORTED_CALIBRATION_VERSION = 2`.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires TMC stepper drivers (tmc2130/2208/2209/2240/2660/5160) for both stepper_x and stepper_y; will raise an error if these are absent.
- The module requires CoreXY kinematics and raises a config error for other kinematics types.
- Only `diagonal_move_rail = 1` (B-motor) is fully tested; the comment in the code notes that `diagonal_move_rail = 0` is "not yet adapted".
- Structured error codes (e.g. `0002-0528-0000-0010`) are Snapmaker-specific and will not be parsed by stock Klipper error handlers.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import math, logging, queuefile, os, json, copy
+import stepper
+from . import homing
+
+HOMING_CALIBRATED_ORIGIN_FILE = "homing_calibrated_origin.json"
+CALIBRATION_DATA_VERSION = 2
+
+class HomingPreciseCorexy:
+    def __init__(self, config):
+        if config.getsection('printer').get('kinematics') != 'corexy':
+            raise config.error("homing_precise_corexy: kinematics must be corexy!!!")
+        ...
+        self.gcode.register_command('HOMING_PRECISE_COREXY', ...)
+        self.gcode.register_command('HOMING_PRECISE_COREXY_ADVANCED', ...)
+        self.gcode.register_command("ENTER_HOMING_ORIGIN_CALIBRATION", ...)
+        self.gcode.register_command("EXIT_HOMING_ORIGIN_CALIBRATION", ...)
+
+    def diagonal_probe(self, endstops, movepos, ...): ...
+    def phase_backoff_steps(self, corexy_rails): ...
+    def load_calibrated_origin(self): ...
+
+def load_config(config):
+    return HomingPreciseCorexy(config)
```
</details>
