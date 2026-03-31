# park_detector.py

## Summary
`park_detector.py` implements `ParkDetector`, a lightweight Klipper extra that monitors one, two, or three GPIO/ADC button signals to determine whether a tool-changer extruder is in the "parked" (docked), "active" (picked up), or "unknown" state. The primary signal (`pin`) reads the park latch; an optional `active_pin` reads the active/picked state; an optional `grab_valid_pin` reads a gripper-validity signal. Each pin can be either a digital button or an ADC range-based button. State is decoded as `PARKED`, `ACTIVATE`, or `UNKNOWN` based on the logical combination of the two primary signals. The `QUERY_PARK_STA NAME=<name>` command reports current state and optionally prints ADC voltages for debugging.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: multi-pin (digital or ADC) extruder dock-state detector with three-pin support | U1's tool-changer has hall-effect or optical sensors on the dock to detect whether an extruder is parked or active; upstream Klipper has no tool-changer dock detection |

## Additions

### Classes
- **`ParkDetector`** — Klipper extra loaded via `load_config_prefix` (section `[park_detector <name>]`).

### G-code Commands
- **`QUERY_PARK_STA NAME=<name>`** — Report state (`PARKED`/`ACTIVATE`/`UNKNOWN`) and raw pin values for each configured pin.

### Config Options
- `pin` (required) — Primary park-detect pin (digital or ADC).
- `analog_range` — If provided, the primary pin is treated as an ADC button in this voltage range (V min, V max).
- `analog_pullup_resistor` (float, default 4700 Ω) — Pullup for ADC mode.
- `active_pin` — Optional secondary active-state pin.
- `active_analog_range` / `active_analog_pullup_resistor` — ADC range for active pin.
- `grab_valid_pin` — Optional third pin for gripper-validity.
- `grab_valid_analog_range` / `grab_valid_analog_pullup_resistor`
- `ignore_active_pin` (bool, default False) — If True, state is determined solely from `pin` (parked/not-parked binary).

### State Logic
- `ignore_active_pin=False` (default): `PARKED` if `park_state=True AND active_state=False`; `ACTIVATE` if `park_state=False AND active_state=True`; otherwise `UNKNOWN`.
- `ignore_active_pin=True`: `PARKED` if `park_state=True`, else `ACTIVATE`.

### Public API
- `get_park_detector_status()` → `{'state': 'PARKED'|'ACTIVATE'|'UNKNOWN', 'park_pin': bool, 'active_pin': bool, 'grab_valid_pin': bool}`
- `get_park_detector_adc_value()` — Prints ADC voltages to G-code console (debug).

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Callback state variables (`park_state`, `active_state`, `grab_valid_state`) are updated from `buttons` callbacks which may run on a different timing domain; there is no mutex protecting reads from `get_park_detector_status()`.
- ADC voltage display in `get_park_detector_adc_value` hardcodes `× 3.3` — assumes a 3.3 V ADC reference regardless of the `analog_pullup_resistor` configured.
- The `UNKNOWN` state is returned when both sensors agree (both parked or both active), which may mask legitimate hardware faults.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Support for extruder park detection
+import logging
+
+class ParkDetector:
+    def __init__(self, config):
+        self.printer = config.get_printer()
+        self.name = config.get_name().split(' ')[-1]
+        self.pin = config.get('pin')
+        ...
+        # register primary pin (digital or ADC)
+        # register optional active_pin and grab_valid_pin
+        self.gcode.register_mux_command("QUERY_PARK_STA", "NAME", self.name,
+                                        self.cmd_QUERY_PARK)
+
+    def get_park_detector_status(self):
+        # decode PARKED / ACTIVATE / UNKNOWN from pin states
+        ...
+
+def load_config_prefix(config):
+    return ParkDetector(config)
```
</details>
