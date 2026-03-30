# defect_detection.py

## Summary
`defect_detection.py` implements `DefectDetection`, a Klipper extra that uses an on-board camera (via MQTT JSON-RPC) to detect four categories of print defects in real time: dirty bed before printing, noodle stringing above the print, residue on the bed surface, and a dirty nozzle. Each detection type has independently configurable enable/disable, a sliding-window history, and a high/low sensitivity setting. When a defect is confirmed the print is paused via `pause_resume.send_pause_command()` and an exception event is raised. A configurable `ignore_detect_layer` suppresses detection for the first N layers. Detection state and configuration are persisted in `defect_detection.json`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: AI-based real-time print defect detection using MQTT camera service, with four defect categories and sliding-window confirmation | U1 has an optional cavity camera; this module provides automated quality monitoring without user intervention |

## Additions

### Classes
- **`DefectDetection`** — Klipper extra loaded as `[defect_detection]`.

### G-code Commands
- **`DEFECT_DETECTION_CONFIG`** — Set detection parameters (enable/disable specific checks, sensitivity, window sizes) at runtime; persists to JSON.
- **`DEFECT_DETECTION_START`** — Reset internal state and arm detection for the current layer.
- **`DEFECT_DETECTION_DETECT`** — Trigger a single detection round (sends camera JSON-RPC request, blocks for result).
- **`DEFECT_DETECTION_DETECT_BED`** — Specifically detect dirty-bed or residue on the build surface.
- **`DEFECT_DETECTION_DETECT_NOZZLE`** — Specifically detect a dirty nozzle.

### Webhook Endpoint
- `defect_detection/config` — REST-style config update endpoint (same as `DEFECT_DETECTION_CONFIG` G-code).

### Config Options (in `[defect_detection]` section)
- `debug_mode` (bool, default False)
- `bed_detect_pos_x/y` (float) — XY position for bed defect detection camera shot.
- `bed_detect_probe_distance` (float, default 50 mm) — Z height for bed camera shot.
- `ignore_detect_layer` (int, default 30) — Skip detection for this many initial layers.
- `clean_bed_threshold_high/low` — Confidence thresholds for clean-bed detection.
- `residue_threshold_high/low`, `noodle_threshold_high/low`, `nozzle_threshold_high/low` — Per-category thresholds.

### Runtime Config (persisted in `defect_detection.json`)
- `main_enable` (bool) — Master enable.
- `sen_high_factor = 0.2`, `sen_low_factor = 0.5` — Global sensitivity multipliers.
- Per-category config blocks: `clean_bed`, `noodle`, `residue`, `nozzle` — each with `enable`, `check_window`, and `sensitivity`.

### Detection Categories and Confirm Codes
- `CONFIRM_DIRTY_BED = 1`, `CONFIRM_NOODLE = 2`, `CONFIRM_RESIDUE = 3`, `CONFIRM_DIRTY_NOZZLE = 4`

### MQTT Topics
- `camera/request`, `camera/response`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `mqtt` extra, `print_task_config`, and an on-board camera service implementing the `camera.*` JSON-RPC methods.
- `DEFECT_DETECTION_DETECT` and `DEFECT_DETECTION_DETECT_BED` are synchronous (use `send_request_with_response` with 5 s timeout), blocking the G-code thread.
- The `ignore_detect_start_layer` tracking logic assumes `print_stats.info_current_layer` is populated — requires fork-modified `print_stats`.
- Sliding-window history (`check_noodle_result`, `check_residue_result`) is a plain Python list with no size cap, only reset on print start.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, os, copy
+from .jsonrpc import *
+
+TIME_INTERVAL    = 3.5
+REQUEST_TIMEOUT  = 5.0
+
+CONFIRM_DIRTY_BED    = 1
+CONFIRM_NOODLE       = 2
+CONFIRM_RESIDUE      = 3
+CONFIRM_DIRTY_NOZZLE = 4
+
+class DefectDetection:
+    def __init__(self, config):
+        ...
+        self.gcode.register_command("DEFECT_DETECTION_CONFIG", ...)
+        self.gcode.register_command("DEFECT_DETECTION_START", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT_BED", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT_NOZZLE", ...)
+        webhooks.register_endpoint("defect_detection/config", ...)
+
+def load_config(config):
+    return DefectDetection(config)
```
</details>
