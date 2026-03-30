# probe_inductance_coil.py

## Summary
`probe_inductance_coil.py` is the fork's replacement for (and extension of) the upstream `probe.py` module. It re-implements `ProbeCommandHelper`, `ProbeEndstopWrapper`, and `ProbePointsHelper`, adapting them to work with the `InductanceCoil` frequency sensor instead of a simple endstop. Beyond standard probe commands (`PROBE`, `PROBE_ACCURACY`, `PROBE_CALIBRATE`, `Z_OFFSET_APPLY_PROBE`), it adds commands for XYZ offset calibration between multiple extruders (`PROBE_XYZ_OFFSET_CALIBRATE`), bed-contact detection (`PROBE_BED_CONTACT`), and inductance coil trigger frequency override (`SET_PROBE_TRIG_FREQ`). It also introduces a configurable circle-mode probing pattern (in addition to the standard rectangular grid), Decimal-precision circle-centre calculation, and per-probe XYZ offset persistence via a JSON config file.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Upstream `probe.py` defines `ProbeCommandHelper`, `ProbeEndstopWrapper`, `ProbePointsHelper` | Fork replaces these with extended versions in `probe_inductance_coil.py` that integrate with `InductanceCoil` frequency-based triggering, add XYZ offset calibration, and support circle/rectangle probe patterns | U1 uses an LC coil probe instead of a switch; multi-extruder offset calibration and alternative probing patterns are required for the U1's tool-changer architecture |

## Additions

### New Classes (Fork-Exclusive)
- **`ProbeCommandHelper`** (extended vs upstream) — Adds commands:
  - `PROBE_BED_CONTACT` — Probe until bed contact without recording position.
  - `SET_PROBE_TRIG_FREQ` — Override inductance coil trigger frequency for the next probe.
  - `INDUCTANCE_COIL_PROBE_QUERY` — Query current sensor frequency.
  - `PROBE_XYZ_OFFSET_CALIBRATE` (`PROBE_XYZ_OFFSET_CALIBRATE_ADVANCED`) — Automated multi-extruder XYZ offset calibration sequence.
- **`ExtruderOffsetCalAbort`** — Exception used to abort offset calibration.

### New Functions
- `find_circle_center(A, B, C)` — Uses Decimal precision arithmetic to find the circumcentre of three XY points (used in circle-mode bed levelling).
- `calc_probe_z_average(positions, method, axis)` — Mean/median averaging for probe results.
- `run_single_probe(probe_obj, gcmd)` — Helper to execute a single probe move and return the position.

### New Config Options (on probe section)
- `probe_mode` (0=rectangle, 1=circle) — Probing pattern shape.
- `z_offset_config_file` — Path to JSON file persisting per-extruder XYZ offsets.
- Various XYZ-offset calibration geometry parameters.

### Constants
- `MAX_OFFSET_DELTA_X/Y/Z = 0.8/0.8/0.5` mm — Maximum allowed per-step offset correction during XYZ calibration.
- `RECTANGLE_PROBE_MODE = 0`, `CIRCLE_PROBE_MODE = 1`

### Probe Endpoint
- `PROBE_XYZ_OFFSET_CALIBRATE` — Drives the toolhead through a multi-step sequence: home, move to calibration position, probe multiple points on a calibration target, compute offsets, optionally save to JSON.

## Removals / Overrides
- The fork's `probe_inductance_coil.py` effectively replaces the upstream `probe.py` extra. The standard `[probe]` config section maps to `ProbeEndstopWrapper` defined here, not upstream's version.
- Circle-mode probing and XYZ multi-extruder offset calibration do not exist in any form in upstream Klipper.

## Risks / Compatibility Notes
- Any config or macro that directly uses upstream `probe.py`-specific internals (e.g., imports from `extras.probe`) may break.
- The XYZ offset calibration workflow (`PROBE_XYZ_OFFSET_CALIBRATE`) is deeply coupled to the U1's tool-changer hardware (extruder docking, calibration target geometry).
- Circle-mode probing (`find_circle_center`) is only valid for exactly 3 points; passing fewer or more will raise an error.
- Relies on `queuefile.sync_write_file` for atomic JSON saves — a fork-specific extension.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Z-Probe support
+# Copyright (C) 2017-2024  Kevin O'Connor <kevin@koconnor.net>
+# (Fork heavily modified by Snapmaker)
+import logging, copy, time, os
+import pins, queuefile
+from . import manual_probe, inductance_coil
+from decimal import Decimal, getcontext
+
+RECTANGLE_PROBE_MODE = 0
+CIRCLE_PROBE_MODE    = 1
+MAX_OFFSET_DELTA_X   = 0.8
+MAX_OFFSET_DELTA_Y   = 0.8
+MAX_OFFSET_DELTA_Z   = 0.5
+
+def find_circle_center(A, B, C): ...   # Decimal-precision circumcentre
+def calc_probe_z_average(positions, method='average', axis=2): ...
+
+class ProbeCommandHelper:
+    def __init__(self, config, probe, query_endstop=None):
+        ...
+        gcode.register_command('PROBE_BED_CONTACT', ...)
+        gcode.register_command('SET_PROBE_TRIG_FREQ', ...)
+        gcode.register_command('INDUCTANCE_COIL_PROBE_QUERY', ...)
+        gcode.register_command('PROBE_XYZ_OFFSET_CALIBRATE', ...)
```
</details>
