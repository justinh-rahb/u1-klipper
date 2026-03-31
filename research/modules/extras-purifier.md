# purifier.py

## Summary
`purifier.py` implements the `Purifier` class, a Klipper extra that manages a fume/particle purifier fan attached to the U1 enclosure. It wraps a standard `fan.Fan` object for the main fan, adds a secondary fan tachometer (via `pulse_counter`), monitors purifier power presence via an ADC pin, accumulates total run-time (persisted to `purifier_config.json`), and implements a configurable delayed fan-off behaviour (default 180 s after power is removed). A periodic save timer (every 360 s) ensures run-time data is not lost if Klipper is killed without a clean shutdown.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: enclosure purifier fan control with power-presence detection, delayed off, run-time tracking, and webhook/G-code interface | U1 supports an optional air purifier accessory; this module provides integrated control from Klipper |

## Additions

### Classes
- **`PurifierFanTachometer`** — Wraps `pulse_counter.FrequencyCounter` to read fan RPM.
- **`Purifier`** — Klipper extra loaded as `[purifier]`.

### G-code Commands
- **`SET_PURIFIER [FAN_SPEED=0-100] [DELAY_TIME=<s>] [WORK_TIME=<s>]`** — Set fan speed (turns on/off with optional delay), update delay time, or override accumulated work time. Saves delay and work_time to JSON.
- **`GET_PURIFIER`** — Report all current purifier status fields.

### Webhook Endpoint
- `control/purifier` — REST equivalent of `SET_PURIFIER`.

### Config Options
- `tachometer_ppr` (int, default 2) — Pulses per revolution for both tachometers.
- `tachometer_poll_interval` (float, default 1 ms) — Poll interval.
- `extra_fan_tach_pin` — Secondary fan tachometer GPIO pin.
- `power_det_pin` — ADC pin for detecting purifier power presence.
- `power_det_threshold` (float, default 0.88) — ADC normalised threshold below which power is considered present.

### Persisted Config (`purifier_config.json`)
- `work_time` (int, seconds) — Accumulated run-time.
- `delay_time` (int, seconds, default 180) — Delayed fan-off duration.

### Fan States
- `FAN_STATE_TURN_ON = 0`, `FAN_STATE_TURN_OFF = 1`, `FAN_STATE_TURNING_OFF = 2`

### Key Logic
- `fan_turn_on(speed)` — Sets fan speed; only activates if power is detected. Cancels any pending delayed-off timer.
- `fan_turn_off(delay_time)` — If `delay_time < 1`, turns fan off immediately and saves run-time. Otherwise schedules delayed turn-off via `_delay_turnoff_handle`.
- `_adc_callback` — ADC interrupt: if power drops below threshold and fan was on, calls `fan_turn_off(0)` immediately.

### Status
- `get_status(eventtime)` → `{'power_detected', 'power_det_value', 'work_time', 'fan_state', 'fan_speed', 'fan_rpm', 'extra_fan_speed', 'extra_fan_rpm', 'delay_time'}`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- `FAN_DELAY_TIME_MIN = 1` s — any `delay_time` below 1 results in immediate shutdown with no delay, even if `delay_time=0` is technically requested.
- The secondary tachometer RPM is exposed in `get_status` but `extra_fan_speed` duplicates `fan_speed` (the `Fan.get_status` speed) rather than the extra fan — likely a bug.
- `_adc_callback` can call `fan_turn_off(0)` from the ADC interrupt path, which directly calls `reactor` methods; this should be safe as `set_speed_from_command` internally uses the reactor but should be reviewed.
- Accumulated work time uses `reactor.monotonic()` differences; time is only added when fan is on, but clock skew (e.g. NTP adjustment) could cause negative increments.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, json, copy, os
+from . import fan
+from . import pulse_counter
+
+FAN_STATE_TURN_ON    = 0
+FAN_STATE_TURN_OFF   = 1
+FAN_STATE_TURNING_OFF = 2
+DEFAULT_FAN_DELAY_TIME = 180
+PURIFIER_CONFIG_FILE = "purifier_config.json"
+
+class PurifierFanTachometer: ...
+
+class Purifier:
+    def __init__(self, config):
+        ...
+        self._fan = fan.Fan(config, default_shutdown_speed=0.)
+        self._power_det_pin.setup_adc_callback(..., self._adc_callback)
+        gcode.register_command('SET_PURIFIER', ...)
+        gcode.register_command('GET_PURIFIER', ...)
+        wh.register_endpoint("control/purifier", ...)
+
+def load_config(config):
+    return Purifier(config)
```
</details>
