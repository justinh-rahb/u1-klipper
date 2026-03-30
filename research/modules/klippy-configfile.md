# configfile.py

## Summary
`configfile.py` handles loading, parsing, and saving `printer.cfg`. The fork merges what upstream splits into `ConfigFileReader`, `ConfigAutoSave`, and `ConfigValidate` into a single `PrinterConfig` class, adopts a custom `ConfigError` that inherits from both `CodedException` and `configparser.Error`, and simplifies the internal two-pass config loading path. The `deprecate()` helper signature is also simplified. Upstream's `deprecate_gcode()` and `deprecate_mcu_code()` methods are removed as the fork does not use them.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `error = configparser.Error` (plain exception) | `class ConfigError(CodedException, configparser.Error)` | Structured error routing through exception_manager |
| `ConfigFileReader` is a separate class; `ConfigAutoSave` and `ConfigValidate` are separate helpers | All merged into `PrinterConfig` as private methods | Simplification / reduced indirection |
| `deprecate(section, option, value, msg)` builds a detailed dict and deduplicates | Simplified: passes a pre-built `msg` string directly to `pconfig.deprecate(...)` | Reduced complexity |
| `load_main_config()` returns `(regular_fileconfig, autosave_fileconfig)` tuple | `read_main_config()` returns a single merged `ConfigWrapper` | Cleaner API |
| `check_unused_options` uses `ConfigValidate.check_unused(fileconfig)` | Inlined into `PrinterConfig.check_unused_options(config)` | Single-class design |
| `runtime_warning` deduplicates via `_add_deprecated` | `runtime_warning` appends to `self.runtime_warnings` directly, sets `self.status_warnings` | Simplified deduplication |
| `get_status` returns `settings`, `config`, `warnings` merged from three sub-objects | Returns `config` and `warnings` from `PrinterConfig` directly | Same data, simpler path |

## Additions
- `ConfigError` class — dual-inherits from `CodedException` and `configparser.Error`.
- `PrinterConfig._read_config_file(filename)` — reads and normalises line endings (moved from `ConfigFileReader`).
- `PrinterConfig._parse_config_buffer`, `_resolve_include`, `_parse_config`, `_build_config_wrapper`, `_build_config_string` — include-file resolution and config building moved from `ConfigFileReader` into `PrinterConfig`.
- `PrinterConfig.read_config(filename)` — reads an arbitrary config file into a `ConfigWrapper`.
- `PrinterConfig.read_main_config()` — replaces `load_main_config()`; now returns one `ConfigWrapper`.

## Removals / Overrides
- `ConfigFileReader` class — removed; its methods inlined into `PrinterConfig`.
- `ConfigAutoSave` class — removed; merged into `PrinterConfig`.
- `ConfigValidate` class — removed; merged into `PrinterConfig`.
- `PrinterConfig.deprecate_gcode(cmd, param, value, msg)` — removed.
- `PrinterConfig.deprecate_mcu_code(mcu, feature, msg)` — removed.
- `PrinterConfig._add_deprecated(data)` — removed; deduplication replaced with simpler list append.

## Risks / Compatibility Notes
- Any extra module calling `pconfig.deprecate_gcode(...)` or `pconfig.deprecate_mcu_code(...)` will raise `AttributeError`.
- `ConfigError` now inherits from `CodedException` with default `id=522`. All config errors will appear in the Moonraker exception bus with the Motion module ID unless overridden.
- The single-pass `read_main_config()` return value changed from a tuple to a single object; any code that unpacks `(regular_fileconfig, autosave_fileconfig)` from `load_main_config()` will break (not an issue in the fork which already uses the new API).
- `status_settings` dict still populated via `_build_status`; format compatible with upstream Moonraker's `configfile.settings` subscription.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/configfile.py
+++ b/klippy/configfile.py
@@ -8,2 +9 @@
-error = configparser.Error
+class ConfigError(CodedException, configparser.Error):
+    pass
+error = ConfigError

 # ConfigFileReader, ConfigAutoSave, ConfigValidate classes removed;
 # their methods merged into PrinterConfig.

 # deprecate_gcode() and deprecate_mcu_code() removed from PrinterConfig.
```

</details>
