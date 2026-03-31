# filament_parameters.py

## Summary
`filament_parameters.py` provides the `FilamentParameters` class, a lookup table that maps (vendor, main_type, sub_type) tuples to a set of printing parameters: load/unload temperatures, nozzle-cleaning temperature, pressure-advance `k` value and its calibration range (`flow_k_min`/`flow_k_max`), slow/fast flow velocities, and a softness flag (`is_soft`). The default table ships with roughly 20 material profiles (PLA, PETG, TPU, ABS, ASA, PA, PC, etc.) for generic, Snapmaker, and Polymaker vendors. At startup the module checks a version string against `FILAMENT_PARAMETER_VERSION = '0.0.7'` and resets the persisted JSON config to defaults if the version is stale. Other modules call `get_filament_parameters()`, `get_load_temp()`, etc. to look up the correct temperature for the current filament.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: vendor/type/sub-type indexed filament parameter database with JSON persistence and version migration | U1 uses RFID-identified filament; downstream modules need material-specific temperatures and pressure-advance values without user input |

## Additions

### Classes
- **`FilamentParameters`** — Klipper extra loaded as `[filament_parameters]`.

### G-code Commands
- **`FILAMENT_PARA_GET_ALL_INFO`** — Respond with the full internal parameter dictionary as a string (debug).

### Public API Methods
- `get_filament_parameters(vendor, main_type, sub_type)` → dict — Falls back through vendor_generic / sub_generic if the exact match is absent.
- `get_load_temp(vendor, main_type, sub_type)` → int
- `get_unload_temp(vendor, main_type, sub_type)` → int
- `get_clean_nozzle_temp(vendor, main_type, sub_type)` → int
- `get_flow_temp(vendor, main_type, sub_type)` → int
- `get_flow_k(vendor, main_type, sub_type)` → float
- `get_is_soft(vendor, main_type, sub_type)` → bool
- `reset_parameters()` — Restore defaults and update JSON file.
- `get_status(eventtime)` — Returns a deep copy of the full config dict.

### Config File
- `filament_parameters.json` — Persisted in Snapmaker config dir. Contains a three-level nested dict: `material_type → vendor → sub_type → params`.

### Material Types Covered
PLA, PLA-CF, TPU (with sub-types 95A, 95A HF), PETG (with HF sub-type), PETG-CF, PETG-HF, PCTG, EVA, ABS, ASA, PA, PA-CF, PA6-CF, PA-GF, PA6-GF, PC, PC-ABS.

### Default Unknown Values
- Load/unload: 250 °C; clean nozzle: 170 °C; flow temp: 220 °C; `flow_k`: 0.02; `is_soft`: False.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Uses `printer.get_snapmaker_config_dir()` and `printer.load_snapmaker_config_file()` — Snapmaker-only API.
- Version string `'0.0.7'` is compared against the persisted value; any manual edits to the JSON that include the wrong version will silently wipe user customisations.
- All temperature defaults are hard-coded Snapmaker values; a third-party filament will receive these defaults if its vendor/type is not in the table.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import copy, os, logging
+
+FILAMENT_PARAMETER_VERSION                      = '0.0.7'
+FILAMENT_PARA_CFG_FILE                          = 'filament_parameters.json'
+FILAMENT_PARA_CFG_DEFAULT = {
+    'version': '0.0.6',
+    'PLA': {
+        'vendor_generic': { 'sub_generic': { 'load_temp': 250, ... } },
+        'vendor_Snapmaker': { ... },
+        ...
+    },
+    'TPU': { ... },
+    ...
+}
+
+class FilamentParameters:
+    def __init__(self, config):
+        ...
+        gcode.register_command('FILAMENT_PARA_GET_ALL_INFO',
+                               self.cmd_FILAMENT_PARA_GET_ALL_INFO)
+    def get_filament_parameters(self, filament_vendor, filament_main_type, filament_sub_type):
+        ...  # three-level fallback lookup
+    def get_load_temp(self, ...): ...
+    def get_flow_k(self, ...): ...
+    def reset_parameters(self): ...
+
+def load_config(config):
+    return FilamentParameters(config)
```
</details>
