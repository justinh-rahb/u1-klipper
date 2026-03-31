# extruder_config_bak.py

## Summary
`extruder_config_bak.py` implements `ExtruderConfigBak`, a Klipper extra that backs up extruder park position configuration (XY park coordinates and Y idle position) from the Klipper config file to a persistent JSON file (`extruder_config.json` in the `persistent` config directory). This ensures that extruder park calibration data survives a Klipper config reset or firmware update. At load time (`load_config`) it calls `extruder_config_bak()` which reads all `[extruder]`/`[extruder<N>]` sections, extracts `xy_park_position`, `y_idle_position`, and optionally `base_position`, and writes them to the persistent file if it does not already exist. It also handles migration from an older single-file format to the new split-file format (park data vs. base-position data). A `DELETE_EXTRUDER_BACKUP_CONFIG` command allows authorised deletion of the backup files.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automatic backup of extruder park positions to a persistent JSON file with atomic writes and migration support | U1's tool-changer stores calibrated park positions in the Klipper config; this module ensures they are preserved in a separate persistent location across config resets |

## Additions

### Classes
- **`ExtruderConfigBak`** — Klipper extra loaded as `[extruder_config_bak]`.

### G-code Commands
- **`DELETE_EXTRUDER_BACKUP_CONFIG`** — Delete the persistent backup files. Gated by `printer.check_extruder_config_permission()` — a fork-specific API that checks for a permission file.

### Key Config Files
- `extruder_config.json` (persistent dir) — Contains `xy_park_position` and `y_idle_position` per extruder.
- `extruder_base_position.json` (snapmaker config dir) — Contains `base_position` per extruder.

### Public API
- `get_extruder_config(extruder_name, field_name=None)` — Read a field from the JSON backup. Supports dotted-path field names and integer indices (e.g. `'xy_park_position.0'`).
- `update_extruder_config(extruder_name, field_name=None, value=None)` — Atomically update a field in the JSON backup using `queuefile.sync_write_file`.
- `extruder_config_bak(config)` — Called at load time to perform the initial backup (or migration) if the persistent file does not exist.
- `_migrate_existing_backup()` — Reads old-format single-file backup and splits it into park-data and base-position files.

### Atomic Write
- `_save_config_atomically(config_path, data)` — Uses `queuefile.sync_write_file(..., safe_write=True)` for atomic JSON persistence.

### Extruder Sections Scanned
All `[extruder]` and `[extruder1]`–`[extruder98]` sections present in the Klipper config.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `queuefile` (fork-specific Python extension) for atomic writes.
- `printer.get_snapmaker_config_dir("persistent")` is a fork-specific API; the "persistent" sub-directory is separate from the normal Snapmaker config dir to survive firmware updates.
- `printer.check_extruder_config_permission()` is not defined in upstream Klipper; without it, `DELETE_EXTRUDER_BACKUP_CONFIG` will always raise an error.
- If `xy_park_position` or `y_idle_position` are missing from any extruder section, `extruder_config_bak()` raises a `config.error` at load time, preventing Klipper from starting.
- The migration code comments out the rename of the old file after migration (left as `.tmp`), which means re-running migration will overwrite the new file each time.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import json, os, tempfile, logging, queuefile
+
+EXTRUDER_CONFIG_FILE = "extruder_config.json"
+EXTRUDER_BASE_POSITION_FILE = "extruder_base_position.json"
+
+class ExtruderConfigBak:
+    def __init__(self, config):
+        self.config_path = os.path.join(
+            self.printer.get_snapmaker_config_dir("persistent"),
+            EXTRUDER_CONFIG_FILE)
+        ...
+        gcode.register_command('DELETE_EXTRUDER_BACKUP_CONFIG', ...)
+
+    def extruder_config_bak(self, config):
+        # scan all [extruder] sections
+        # extract xy_park_position, y_idle_position, base_position
+        # write to persistent JSON if not already present
+        ...
+
+    def update_extruder_config(self, extruder_name, field_name=None, value=None):
+        # atomic JSON update via queuefile.sync_write_file
+        ...
+
+def load_config(config):
+    extruder_bak = ExtruderConfigBak(config)
+    extruder_bak.extruder_config_bak(config)
+    return extruder_bak
```
</details>
