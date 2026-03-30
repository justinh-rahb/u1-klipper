# kinematics/extruder.py

## Summary
`extruder.py` implements Klipper's extruder kinematics and G-code interface. In the Snapmaker U1 fork this file has grown by ~1833 diff lines relative to upstream. The most significant additions are the `ExtruderSwitchRecorder` class (which tracks per-extruder switch, retry, and error counts in a persistent JSON file and exposes G-code commands for inspection and reset), a full park/pick subsystem for dual-extruder tool-change management (park position config options, park-detector integration, and six new G-code commands), and a set of custom exception classes used by the park/pick flow. The `DummyExtruder` class was also updated: its `check_move` and `calc_junction` signatures were simplified and a new `update_move_time` stub was added.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Copyright year: 2016–2025 | Copyright year: 2016–2022 | Fork was branched from an earlier upstream snapshot |
| `import stepper, chelper` only | Also imports `coded_exception`, `queuefile`, `os`, `json`, `copy` | Required by new persistence and exception subsystems |
| No extruder-switch tracking | `ExtruderSwitchRecorder` class persists switch/retry/error counts to JSON | Maintenance alerting and warranty tracking for Snapmaker hardware |
| No park/pick concept | Full park position config (`xy_park_position`, `y_idle_position`, `y_park_position`) + `park_detector` integration | Dual-carriage tool-change requires safe parking positions |
| `DummyExtruder.check_move(move, ea_index)` | `DummyExtruder.check_move(move)` — `ea_index` removed | Simplified move-check interface; `ea_index` concept dropped |
| `DummyExtruder.calc_junction` takes `ea_index` | `ea_index` parameter removed | Consistent with `check_move` simplification |
| `DummyExtruder.get_axis_gcode_id()` returns a value | Raises `command_error` instead | Prevents silent misuse of dummy extruder as a real axis |
| No `update_move_time` on `DummyExtruder` | `update_move_time(flush_time, clear_history_time)` stub added (no-op) | Interface parity required by the toolhead dispatcher |
| `load_config_prefix` only instantiates the extruder | Also creates `ExtruderSwitchRecorder` (for index 0) and validates `park_detector` config consistency across all extruders | Ensures recorder and detector are set up exactly once and consistently |

## Additions

- **Exception classes**: `ExtruderParkAction`, `ExtruderUnknownParkStatus`, `ExtruderPickAbnormal` — used by the park/pick state machine.
- **Constants**: `PARK_DETECTOR_LOOP_CHECK_INTERVAL = 0.1`, `PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10`, `MAX_ALLOWED_DIFFERENCE = 3.0`, `EXTRUDER_SWITCH_RECORDER = "extruder_switch_recorder.json"`, `STRUCTURED_CODE_LIST = []`.
- **`ExtruderSwitchRecorder` class**:
  - Tracks per-extruder switch, retry, and error counts.
  - Persists data to JSON in the printer's persistent config directory.
  - Supports data migration from a legacy path.
  - Periodic auto-save timer.
  - Maintenance threshold checking with structured exception codes (`0001-0523-0000-0037` family).
  - G-code commands: `GET_EXTRUDER_SWITCH_RECORDER`, `RESET_EXTRUDER_SWITCH_RECORDER`, `RESET_EXTRUDER_MAINTENANCE_COUNT`.
- **Park position management**:
  - Config options: `xy_park_position`, `y_idle_position`, `y_park_position`.
  - `park_detector` object integration for physical park/pick detection.
  - `active_binding_probe()` method.
  - `extruder_list` object registered with the printer for multi-extruder enumeration.
- **G-code commands**: `PICK_EXTRUDER`, `PARK_EXTRUDER`, `SET_PARK_POSITION`, `ENTER_PARK_POINT_MANUAL_CALIBRATION`, `EXIT_PARK_POINT_MANUAL_CALIBRATION`, `MOVE_TO_PARK_CALIBRATION_POINT`, `VERIFY_PARK_POSITION`.

## Removals / Overrides

- `ea_index` parameter removed from `DummyExtruder.check_move` and `DummyExtruder.calc_junction`.
- `DummyExtruder.get_axis_gcode_id()` no longer returns a value; replaced with a `command_error` raise.
- Upstream copyright year range truncated (cosmetic but signals divergence point).

## Risks / Compatibility Notes

- The simplified `check_move(move)` / `calc_junction` signatures are **incompatible** with any upstream code that passes `ea_index`; merging upstream changes to these methods will require manual reconciliation.
- `ExtruderSwitchRecorder` writes to the printer's persistent config directory; misconfiguration of that path will silently skip persistence.
- `PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10` and `MAX_ALLOWED_DIFFERENCE = 3.0` are hard-coded constants — they are not exposed as config options and cannot be tuned per-machine without a code change.
- The structured exception codes (`0001-0523-0000-0037`) are Snapmaker-specific and will not be understood by generic Klipper tooling.
- `park_detector` config consistency is validated at startup; a mismatch across extruder config sections will raise an error that may be confusing without Snapmaker documentation.
- This file has diverged substantially from upstream (1833 diff lines); rebasing onto a newer Klipper release will be a significant effort.

## Raw Diff

<details>
<summary>View Diff</summary>

```diff
3c3
< # Copyright (C) 2016-2025  Kevin O'Connor <kevin@koconnor.net>
---
> # Copyright (C) 2016-2022  Kevin O'Connor <kevin@koconnor.net>
7c7,239
< import stepper, chelper
---
> import stepper, chelper, coded_exception, queuefile
> import os, json, copy
>
> class ExtruderParkAction(Exception):
>     pass
>
> class ExtruderUnknownParkStatus(Exception):
>     pass
>
> class ExtruderPickAbnormal(Exception):
>     pass
>
> PARK_DETECTOR_LOOP_CHECK_INTERVAL = 0.1
> PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10
> MAX_ALLOWED_DIFFERENCE = 3.0
> STRUCTURED_CODE_LIST = []
>
> EXTRUDER_SWITCH_RECORDER = "extruder_switch_recorder.json"
>
> class ExtruderSwitchRecorder:
>     def __init__(self, config):
>         self.printer = config.get_printer()
>         self.configfile = self.printer.lookup_object('configfile')
>         self._data = {}
>         self._save_timer = None
>         self._load()
>         self._register_commands()
>         self._schedule_save()
>     def _load(self):
>         # Load from persistent config dir; migrate from old path if needed
>         ...
>     def _schedule_save(self):
>         # Periodic JSON save via reactor timer
>         ...
>     def record_switch(self, extruder_index):
>         ...
>     def record_retry(self, extruder_index):
>         ...
>     def record_error(self, extruder_index):
>         ...
>     def check_maintenance_threshold(self, extruder_index):
>         # Raises coded_exception with code 0001-0523-0000-0037 if threshold exceeded
>         ...
>     def _register_commands(self):
>         gcode = self.printer.lookup_object('gcode')
>         gcode.register_command('GET_EXTRUDER_SWITCH_RECORDER', ...)
>         gcode.register_command('RESET_EXTRUDER_SWITCH_RECORDER', ...)
>         gcode.register_command('RESET_EXTRUDER_MAINTENANCE_COUNT', ...)
>
> # ... (extruder park/pick classes and config additions) ...
>
> # Park position config options added to PrinterExtruder.__init__:
> #   xy_park_position, y_idle_position, y_park_position
> # park_detector object looked up and integrated
> # active_binding_probe() method added
> # extruder_list registered with printer
>
> # New G-code commands registered:
> #   PICK_EXTRUDER, PARK_EXTRUDER, SET_PARK_POSITION,
> #   ENTER_PARK_POINT_MANUAL_CALIBRATION,
> #   EXIT_PARK_POINT_MANUAL_CALIBRATION,
> #   MOVE_TO_PARK_CALIBRATION_POINT, VERIFY_PARK_POSITION

295c1929,1931
<     def check_move(self, move, ea_index):
---
>     def update_move_time(self, flush_time, clear_history_time):
>         pass
>     def check_move(self, move):
```

</details>
