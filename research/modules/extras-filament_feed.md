# filament_feed.py

## Summary
`filament_feed.py` is a large, complex module implementing the automatic filament loading, unloading, and pre-loading state machine for the Snapmaker U1's multi-channel feeder hardware. It drives dual PWM H-bridge feed motors, reads two optical wheel tachometers per channel, monitors a port-presence ADC, controls RGB indicator lights, and issues filament-runout/resume events. A rich set of named states (`FEED_STA_*`) models every stage of the load/unload workflow. Per-channel configuration (auto-mode flag, load-completion status) is persisted to a per-instance JSON file (e.g. `<name>_filament_feed.json`). The module also exposes a number of G-code commands and hooks into filament-sensor runout events to drive fully automated filament replenishment during printing.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | Full new module: dual-channel PWM motor-driven filament feeder with ADC port detection, tachometer feedback, and multi-stage load/unload FSM | U1 has a standalone feeder unit mounted above the print head; upstream Klipper has no concept of a separate pre-feeder motor |

## Additions

### Classes
- **`FeedLight`** — Controls per-channel red and white PWM indicator LEDs.
- **`FeedTachometer`** — Wraps `pulse_counter.FrequencyCounter` to read RPM and cumulative pulse count from a wheel encoder.
- **`FeedPwmCfg`** — Data class for H-bridge PWM pin configuration (A-pin, B-pin, cycle time, max value).
- **`FeedMotor`** — Drives a dual-PWM H-bridge motor. Enforces a 2.5 s hard-protect delay when reversing direction. Exposes `run(dir, value)` and `run_one_cycle(dir, value)`.
- **`FilamentFeed`** — Main extra class (one instance per feeder, loaded via `load_config_prefix`). Manages two physical channels per instance.

### G-code Commands
- **`FEED_LOAD MODULE=<name> CHANNEL=<0|1> [...]`** — Trigger full automated filament load on the specified channel.
- **`FEED_UNLOAD MODULE=<name> CHANNEL=<0|1> [STAGE=prepare|doing|cancel]`** — Trigger full automated filament unload.
- **`FEED_MANUAL MODULE=<name> CHANNEL=<0|1> STAGE=prepare|extrude|flush|finish|cancel [...]`** — Drive manual filament operations stage by stage.
- **`FEED_CANCEL MODULE=<name>`** — Cancel any ongoing feed operation.
- **`FEED_MOTOR MODULE=<name> CHANNEL=<0|1> DIR=<0|1|2> VALUE=<0-1>`** — Directly drive a feed motor (for testing/debugging).
- **`FEED_LIGHT MODULE=<name> CHANNEL=<0|1> COLOR=RED|WHITE|ALL VALUE=<0-1>`** — Control indicator LEDs.
- **`FEED_QUERY MODULE=<name>`** — Report current status of all channels.
- **`FEED_UPDATE_AUTO_MODE MODULE=<name> CHANNEL=<0|1> AUTO=<0|1>`** — Enable/disable automatic filament replenishment for a channel.
- **`FEED_REMOVE_FILAMENT MODULE=<name> CHANNEL=<0|1>`** — Remove filament from a channel.

### Key Constants
- `FEED_MOTOR_HARD_PROTECT_TIME = 2.5` s — Minimum delay between motor reversals.
- `FEED_PRELOAD_LENGTH = 950.0` mm — Distance driven during pre-load.
- `FEED_LOAD_LENGTH_MAX = 1100.0` mm — Maximum distance for a full load cycle.
- `FEED_COIL_FREQ_THERSHOLD_SOFT/HARD` — Inductance coil frequency thresholds for soft/hard filament type detection.

### Config Options
- `extruder` / `extruder1` — Name(s) of the extruder(s) served by this feeder.
- `motor_*_pin`, `motor_cycle_time`, `motor_max_value` — H-bridge PWM pin and timing.
- `motor_tach_pin`, `motor_tach_ppr`, `motor_tach_poll_interval` — Motor tachometer.
- `wheel_tach_ch*_pin`, `wheel_tach_ch*_ppr` — Wheel encoder pins and PPR.
- `wheel_2_tach_ch*_pin` — Secondary wheel encoder pins.
- `port_ch*_pin` — ADC port-presence detection pins.
- `light_ch*_red_pin`, `light_ch*_white_pin` — LED pins.
- `preload_length`, `load_length_max`, `unload_speed`, etc. — Tuning parameters.

### Events Emitted
- `filament_feed:port` — Fired when ADC port-presence state changes.

### Events Consumed
- `filament_switch_sensor:runout` — Triggers automatic replenishment workflow.
- `print_stats:start` / `print_stats:stop` / `print_stats:paused` — Print state changes.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Depends on fork-specific `pulse_counter` extension and Snapmaker printer API (`get_snapmaker_config_dir`, `load_snapmaker_config_file`).
- The module uses `reactor.pause()` directly inside G-code command handlers to synchronously wait for motor operations — this blocks the G-code processing thread and is incompatible with upstream's concurrency model.
- Hardcoded mechanical constants (gear ratio, wheel circumference, motor speeds) are specific to U1 feeder hardware.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, copy, os
+from . import pulse_counter
+
+FEED_CHANNEL_NUMS                                   = 2
+FEED_OK                                             = 'ok'
+FEED_ERR                                            = 'general'
+...
+FEED_STA_NONE                                       = 'none'
+FEED_STA_PRELOAD_FEEDING                            = 'preload_feeding'
+FEED_STA_LOAD_PREPARE                               = 'load_prepare'
+...
+class FeedLight: ...
+class FeedTachometer: ...
+class FeedPwmCfg: ...
+class FeedMotor: ...
+class FilamentFeed:
+    def __init__(self, config) -> None:
+        ...
+        gcode.register_mux_command("FEED_LOAD", "MODULE", ...)
+        gcode.register_mux_command("FEED_UNLOAD", "MODULE", ...)
+        gcode.register_mux_command("FEED_MANUAL", "MODULE", ...)
+        gcode.register_mux_command("FEED_CANCEL", "MODULE", ...)
+        gcode.register_mux_command("FEED_MOTOR", "MODULE", ...)
+        gcode.register_mux_command("FEED_LIGHT", "MODULE", ...)
+        gcode.register_mux_command("FEED_QUERY", "MODULE", ...)
+        gcode.register_mux_command("FEED_UPDATE_AUTO_MODE", "MODULE", ...)
+        gcode.register_mux_command("FEED_REMOVE_FILAMENT", "MODULE", ...)
+
+def load_config_prefix(config):
+    return FilamentFeed(config)
```
</details>
