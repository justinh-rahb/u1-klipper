# filament_detect.py

## Summary
`filament_detect.py` implements the `FilamentDetector` class, which manages up to 4 NFC/RFID-based filament identification channels on the Snapmaker U1. At startup (or on filament insert/runout events), it requests the `fm175xx_reader` module to read the MIFARE M1 card embedded in a Snapmaker filament spool. The parsed card data (`filament_protocol.m1_proto_data_parse`) is stored per-channel and broadcast via registered callbacks so other modules (e.g., `print_task_config`) can react to filament type changes. A `startup_stay` flag in a JSON config file controls whether previously-detected filament info is preserved across reboots.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | Full new module: RFID-based filament detection for 4 channels using FM175XX SPI reader and Snapmaker M1-card protocol | U1 hardware has per-channel NFC readers embedded in the filament feeder module; upstream Klipper has no filament-ID concept |

## Additions

### Classes
- **`FilamentDetector`** — Klipper extra loaded as `[filament_detect]`. Manages 4-channel filament info lifecycle.

### G-code Commands
- **`FILAMENT_DT_QUERY CHANNEL=<n>`** — Report vendor, main type, sub type, and ARGB colour for channel `n`.
- **`FILAMENT_DT_UPDATE CHANNEL=<n>`** — Trigger an NFC read for channel `n`, updating stored info asynchronously.
- **`FILAMENT_DT_CLEAR CHANNEL=<n>`** — Trigger a card-clear request for channel `n`, resetting stored info to the blank struct.
- **`FILAMENT_DT_SELF_TEST CHANNEL=<n> [TIMES=100]`** — Run repeated NFC read tests and report success rate plus last-parsed filament data.
- **`FILAMENT_DT_STARTUP_STAY STAY=<0|1> [SAVE=1]`** — Enable/disable the `startup_stay` flag that preserves filament info on reboot; optionally persists to `filament_detect.json`.

### Key Functions / Methods
- `_ready()` — Looks up `filament_feed` and `fm175xx_reader` objects; registers the card-info callback; optionally triggers initial reads for channels that already detect filament.
- `_feed_port_evt_handle(channel, detect)` — Handles `filament_feed:port` events; requests read on insert, clear on removal.
- `_runout_evt_handle(extruder, present)` — Handles `filament_switch_sensor:runout`; aware of multi-feeder modules to decide whether to read or clear.
- `_fm175xx_card_info_deal_callback(channel, operation, result, card_type, card_data)` — Called by `fm175xx_reader` with raw card bytes; delegates to `filament_protocol.m1_proto_data_parse` and calls `_filament_info_update`.
- `register_cb_2_update_filament_info(cb)` — Public API for other modules to subscribe to filament-info change events.
- `get_a_filament_info(channel)` / `get_all_filament_info()` — Return cached info.
- `get_status(eventtime)` — Returns `{'info': ..., 'state': ..., 'config': ...}` for Moonraker/webhooks.
- `factory_reset()` — Resets `startup_stay` to `False` and saves config.

### Config Options (loaded from `filament_detect.json`)
- `startup_stay` (bool, default `False`) — When `True`, the module skips initial NFC reads on startup and keeps whatever info was loaded from the config file.

### Events Consumed
- `filament_feed:port` — Filament feeder port-detect state change.
- `filament_switch_sensor:runout` — Filament runout/resume event.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Depends on three other fork-exclusive modules: `fm175xx_reader`, `filament_protocol`, and `filament_feed`. Cannot run on a stock Klipper build.
- Uses `printer.get_snapmaker_config_dir()` and `printer.load_snapmaker_config_file()` — Snapmaker-specific printer extensions not in upstream.
- Channel count is hard-coded to 4 (`FILAMENT_DT_CHANNEL_NUMS`); a printer with fewer NFC readers will see errors if channels are absent.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, copy, os
+from . import filament_protocol
+from . import fm175xx_reader
+from . import filament_feed
+
+FILAMENT_DT_OK                                  = 0
+FILAMENT_DT_ERR                                 = -1
+FILAMENT_DT_PARAM_ERR                           = -2
+
+FILAMENT_DT_STATE_IDLE                          = 0
+FILAMENT_DT_STATE_DETECTING                     = 1
+FILAMENT_DT_STATE_SELF_TESTING                  = 2
+
+FILAMENT_DT_CHANNEL_NUMS                        = 4
+FILAMENT_DT_CONFIG_FILE                         = "filament_detect.json"
+
+DEFAULT_FILAMENT_DT_CONFIG = {
+    'startup_stay': False
+}
+
+class FilamentDetector:
+    def __init__(self, config) -> None:
+        self.printer = config.get_printer()
+        self.reactor = self.printer.get_reactor()
+        ...
+        gcode.register_command('FILAMENT_DT_QUERY', self.cmd_FILAMENT_DT_QUERY)
+        gcode.register_command('FILAMENT_DT_UPDATE', self.cmd_FILAMENT_DT_UPDATE)
+        gcode.register_command('FILAMENT_DT_CLEAR', self.cmd_FILAMENT_DT_CLEAR)
+        gcode.register_command('FILAMENT_DT_SELF_TEST', self.cmd_FILAMENT_DT_SELF_TEST)
+        gcode.register_command('FILAMENT_DT_STARTUP_STAY', self.cmd_FILAMENT_DT_STARTUP_STAY)
+
+def load_config(config):
+    return FilamentDetector(config)
```
</details>
