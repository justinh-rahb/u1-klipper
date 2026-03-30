# filament_entangle_detect.py

## Summary
`filament_entangle_detect.py` implements the `FilamentEntangleDetect` class, which detects filament tangling on the spool by comparing extruder motor movement (via `extruder.find_past_position`) with two optical wheel-encoder pulse counts from the associated `filament_feed` module. A 100 ms periodic timer computes the ratio of actual feed-wheel pulses to expected pulses based on how far the extruder advanced. If the ratio falls below a threshold (indicating the spool stopped turning while the extruder kept moving), a tangle is declared, the print is paused via `PAUSE`, and an exception event is raised. Detection sensitivity and skip length can be tuned per-filament-type, and a user-settable `detect_factor` is persisted to a per-sensor JSON file.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: tangle detection via encoder-vs-extruder motion comparison, with material-specific thresholds and configurable sensitivity | U1 uses a spool holder with dual wheel encoders; tangling is a real failure mode the hardware can detect |

## Additions

### Classes
- **`FilamentEntangleDetect`** — Klipper extra loaded with `load_config_prefix` (section name `[filament_entangle_detect <name>]`).

### G-code Commands
- **`SET_FILAMENT_ENTANGLE_DETECT_FACTOR SENSOR=<name> DETECT_FACTOR=<float>`** — Adjust the per-sensor detection sensitivity factor (minimum 0.5). Persists to `<name>_entangle.json`.

### Key Config Options
- `extruder` — Name of the extruder this sensor monitors.
- `filament_feed` — Name of the associated `filament_feed` instance.
- `skip_length` (float, mm) — Length of filament to extrude before enabling tangle detection after a print starts.

### Detection Logic Constants
- `CHECK_ENTANGLE_INTERVAL = 0.1` s — Timer interval.
- `ENTANGLE_DETECT_LENGTH_DEFAULT = 6.0` mm — Extruder travel per expected encoder pulse (hard filament).
- `ENTANGLE_DETECT_LENGTH_DEFAULT_SOFT = 120.0` mm — Soft filament threshold.
- `ENTANGLE_DETECT_LENGTH_DEFAULT_TPU_*` — TPU-specific variants (60/120/180 mm).
- `ENTANGLE_GLOBAL_SENSITIVITY_HIGH/MEDIUM/LOW = 1.0/1.5/3.0` — Global multipliers selected from `print_task_config['filament_entangle_sen']`.

### Events Consumed
- `print_stats:start` / `print_stats:stop` / `print_stats:paused` — Start/stop/pause the check timer.
- `print_task_config:set_entangle_detect` — Re-arm skip-length when detection is toggled.
- `klippy:ready`, `klippy:shutdown`

### Events Emitted
- `filament_entangle_detect:tangled` — Fired (with extruder index) when a tangle is confirmed; consumed by `flow_calibrator`.
- `print_stats:update_exception_info` — Exception ID 523, code 38.

### Public API
- `skip_entangle_check(skip=False)` — Temporarily disable tangle checking (used by other modules during non-print moves).
- `get_status(eventtime)` — Returns `{'detect_factor': ...}`.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `filament_feed`, `print_task_config`, and `exception_manager` — all fork-exclusive. Will fail silently (`init_ok = False`) if any are absent.
- Uses `extruder.find_past_position(print_time)` which is a fork-added method on the extruder object; not present in upstream.
- Issues `gcode.run_script('\nPAUSE\nM400\n')` from a reactor timer callback — this is a blocking scripted pause that may conflict with upstream pause/resume logic.
- Per-material detection length is tightly coupled to `print_task_config`'s `filament_soft`, `filament_type`, and `filament_sub_type` fields.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, os
+from . import print_task_config
+
+CHECK_ENTANGLE_INTERVAL                     = 0.1
+ENTANGLE_DETECT_LENGTH_DEFAULT              = 6.0
+ENTANGLE_DETECT_LENGTH_DEFAULT_SOFT         = 120.0
+...
+class FilamentEntangleDetect:
+    def __init__(self, config):
+        ...
+        self.gcode.register_mux_command(
+            "SET_FILAMENT_ENTANGLE_DETECT_FACTOR", "SENSOR", self.name,
+            self.cmd_SET_FILAMENT_ENTANGLE_DETECT_FACTOR)
+        self.printer.register_event_handler('print_stats:start',
+                self._handle_start_print_job)
+        self.printer.register_event_handler('print_stats:stop',
+                self._handle_stop_print_job)
+        self.printer.register_event_handler('print_stats:paused',
+                self._handle_pause_print_job)
+        self.printer.register_event_handler('print_task_config:set_entangle_detect',
+                self._handle_set_entangle_detect)
+
+def load_config_prefix(config):
+    return FilamentEntangleDetect(config)
```
</details>
