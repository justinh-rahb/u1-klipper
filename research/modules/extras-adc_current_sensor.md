# adc_current_sensor.py

## Summary
`adc_current_sensor.py` implements `ADCCurrentSensor`, a simple Klipper extra that reads a voltage from an ADC pin and converts it to a current measurement using Ohm's law: `I = (V_adc + voltage_offset) / (sense_resistor × scale)`. The ADC reading is normalised (0–1) and multiplied by `adc_reference_voltage` (default 3.3 V) to get the voltage. The computed current is updated at a configurable `report_time` interval and exposed via `get_status` and the `QUERY_ADC_CURRENT` G-code command. This is intended for monitoring motor/heater currents via a shunt resistor on the ADC.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: ADC-based current measurement via shunt resistor | U1 hardware has current sensing circuits (e.g. for feeder motor or heater monitoring) that need to be readable from Klipper |

## Additions

### Classes
- **`ADCCurrentSensor`** — Klipper extra loaded via `load_config_prefix` (section name `[adc_current_sensor <name>]`).

### G-code Commands
- **`QUERY_ADC_CURRENT SENSOR=<name>`** — Report current reading, sense resistor value, and reference voltage.

### Config Options
- `pin` — ADC input pin name.
- `sense_resistor` (float, required, > 0) — Shunt resistance in ohms.
- `scale` (float, default 1.0) — Additional scaling factor (e.g. op-amp gain).
- `adc_reference_voltage` (float, default 3.3 V) — ADC reference voltage.
- `voltage_offset` (float, default 0.0 V) — Offset added before dividing by resistance (compensates for op-amp offset).
- `report_time` (float, default 0.300 s) — Measurement update interval.
- `sample_time` (float, default 0.001 s) — ADC sample duration per reading.
- `sample_count` (int, default 8) — Number of ADC samples averaged per reading.

### Public API
- `adc_callback(read_time, read_value)` — ADC interrupt handler; computes and stores `last_current`.
- `get_status(eventtime)` → `{'current', 'sense_resistor', 'adc_reference', 'voltage_offset', 'scale'}`
- `stats(eventtime)` → `(False, '<name>: current=<val>')`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- No range checking on the computed current value; a disconnected or shorted sensor will produce an unreasonable reading without any fault detection.
- `last_current` is `None` before the first ADC callback fires; `QUERY_ADC_CURRENT` will raise an `AttributeError` or format error if called immediately on startup.
- The formula assumes a linear, non-inverting current-sense amplifier topology; other circuit topologies would require a different formula.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+class ADCCurrentSensor:
+    def __init__(self, config):
+        self.printer = config.get_printer()
+        self.name = config.get_name().split()[-1]
+        self.sense_resistor = config.getfloat('sense_resistor', above=0.0)
+        self.scale = config.getfloat('scale', 1.0, above=0.0)
+        self.adc_reference = config.getfloat('adc_reference_voltage', 3.3, above=0.0)
+        self.voltage_offset = config.getfloat('voltage_offset', 0.0)
+        ...
+        self.mcu_adc.setup_adc_callback(self.report_time, self.adc_callback)
+        self.gcode.register_mux_command(
+            "QUERY_ADC_CURRENT", "SENSOR", self.name, ...)
+
+    def adc_callback(self, read_time, read_value):
+        voltage = read_value * self.adc_reference
+        self.last_current = round(
+            (voltage + self.voltage_offset) / (self.sense_resistor * self.scale), 3)
+
+def load_config_prefix(config):
+    return ADCCurrentSensor(config)
```
</details>
