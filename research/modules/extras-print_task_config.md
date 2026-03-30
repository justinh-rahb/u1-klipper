# print_task_config.py

## Summary
`print_task_config.py` implements `PrintTaskConfig`, the central per-print-job configuration store for the U1. It persists settings to `print_task.json` and holds filament metadata (vendor, type, sub-type, colour, SKU, official flag), extruder mapping tables (logical-to-physical for up to 32 logical / 4 physical extruders), and feature flags (timelapse, auto bed leveling, flow calibration, shaper calibration, auto-replenish, tangle detection). It integrates with `filament_detect` to auto-populate filament info from RFID reads, with `filament_parameters` to look up print temperatures, and with `filament_feed` to manage automatic filament replenishment during multi-material prints. A reprint-info sub-dict allows the previous job's settings to be restored for reprinting.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: per-job configuration store integrating filament RFID data, multi-extruder mapping, and feature-flag management | U1's tool-changer, RFID filament ID, and optional calibration steps require a structured per-job config that Klipper's standard config system does not provide |

## Additions

### Classes
- **`PrintTaskConfig`** — Klipper extra loaded as `[print_task_config]`.

### G-code Commands
- **`SET_PRINT_EXTRUDER_MAP`** — Set the logical-to-physical extruder mapping table.
- **`GET_PRINT_EXTRUDER_MAP`** — Query the current mapping.
- **`SET_PRINT_FILAMENT_CONFIG`** — Set filament metadata for one or more extruder slots (vendor, type, sub-type, colour, etc.).
- **`GET_PRINT_TASK_CONFIG`** — Dump the full config dict.
- **`SAVE_CURRENT_PRINT_TASK_CONFIG`** — Force a save to `print_task.json`.
- **`RESET_PRINT_TASK_CONFIG`** — Reset all fields to defaults.
- **`LOAD_PRINT_TASK_CONFIG`** — Reload from `print_task.json`.
- **`SET_TIME_LAPSE_CAMERA`** — Enable/disable timelapse flag.
- **`SET_PRINT_AUTO_BED_LEVELING`** — Enable/disable auto bed leveling for this job.
- **`SET_PRINT_PREFERENCES`** — Set multiple preference flags (auto-replenish, tangle detect, sensitivity) in one call.
- **`SET_PRINT_USED_EXTRUDERS`** — Mark which extruders are used in this print job.
- **`SET_REPRINT_INFO`** — Save reprint-info snapshot.
- **`INNER_CHECK_AND_RELOAD_FILAMENT_INFO`** — Internal command to check and reload filament metadata from RFID cache.
- **`INNER_AUTO_REPLENISH_FILAMENT`** — Internal command to execute automatic filament replenishment logic.

### Webhook Endpoint
- `print_task_config/set_print_preferences` — REST endpoint equivalent of `SET_PRINT_PREFERENCES`.

### Config Options (in `print_task.json`)
- `filament_vendor`, `filament_type`, `filament_sub_type` — Per-extruder arrays (4 entries).
- `filament_color` (uint32 ARGB), `filament_color_rgba` (hex string) — Per-extruder colour arrays.
- `filament_official`, `filament_sku`, `filament_edit`, `filament_exist`, `filament_soft` — Per-extruder bool/int arrays.
- `extruder_map_table` — 32-entry logical-to-physical mapping array.
- `extruders_used`, `extruders_replenished` — Per-extruder bool/index arrays.
- `time_lapse_camera`, `auto_bed_leveling`, `flow_calibrate`, `shaper_calibrate` — Boolean feature flags.
- `auto_replenish_filament` — Bool.
- `filament_entangle_detect` — Bool.
- `filament_entangle_sen` — `'low'`|`'medium'`|`'high'`.
- `reprint_info` — Sub-dict mirroring key fields for reprint restoration.

### Events Emitted
- `print_task_config:set_entangle_detect` — Fired when entangle-detect setting changes; consumed by `filament_entangle_detect`.

### Constants
- `LOGICAL_EXTRUDER_NUM = 32`, `PHYSICAL_EXTRUDER_NUM = 4`
- `ENTANGLE_SENSITIVITY_LOW/MEDIUM/HIGH = 'low'/'medium'/'high'`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The RFID callback `_rfid_filament_info_update_cb` silently ignores unofficial RFID data if the slot already has a non-NONE vendor set — may prevent legitimate updates from non-Snapmaker filament.
- The auto-replenishment logic (`INNER_AUTO_REPLENISH_FILAMENT`) calls `reactor.pause()` inside a G-code command handler for potentially long operations.
- The 32-entry logical extruder map is a U1-specific concept; upstream Klipper extruder objects map 1:1 without an indirection table.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# print task config info
+import logging, os, copy, string
+from . import filament_feed
+
+LOGICAL_EXTRUDER_NUM = 32
+PHYSICAL_EXTRUDER_NUM = 4
+PRINT_TASK_CONFIG_FILE = "print_task.json"
+
+DEFAULT_PRINT_TASK_CONFIG = {
+    'filament_vendor': ['NONE'] * 4,
+    'filament_type': ['NONE'] * 4,
+    'extruder_map_table': [0,1,2,3] + [0]*28,
+    'time_lapse_camera': False,
+    'filament_entangle_detect': False,
+    ...
+}
+
+class PrintTaskConfig:
+    def __init__(self, config):
+        ...
+        gcode.register_command("SET_PRINT_EXTRUDER_MAP", ...)
+        gcode.register_command("SET_PRINT_FILAMENT_CONFIG", ...)
+        gcode.register_command("SET_PRINT_PREFERENCES", ...)
+        gcode.register_command("INNER_AUTO_REPLENISH_FILAMENT", ...)
+        webhooks.register_endpoint(
+            "print_task_config/set_print_preferences", ...)
+
+def load_config(config):
+    return PrintTaskConfig(config)
```
</details>
