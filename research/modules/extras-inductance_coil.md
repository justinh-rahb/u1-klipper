# inductance_coil.py

## Summary
`inductance_coil.py` implements the `InductanceCoil` class, a Klipper extra that interfaces with an eddy-current (LC) inductive frequency sensor used as a Z-probe substitute on the U1. The MCU continuously measures the oscillation frequency of an LC circuit positioned near the print surface; the sensor triggers when the frequency crosses a configured threshold (`trg_freq_ht`/`trg_freq_lt`). The module streams bulk frequency samples via the `bulk_sensor` framework, supports two calibration modes (fixed-time and fixed-pulse-count), and exposes commands to set the trigger frequency and query the live frequency. It is paired with `probe_inductance_coil.py` which wraps it as a standard Klipper probe.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: LC inductive frequency sensor driver with bulk streaming, two calibration modes, and configurable trigger thresholds | U1 uses an inductance coil as a bed-contact Z-probe; upstream Klipper only ships a simple digital-endstop probe and basic BLTouch support |

## Additions

### Classes
- **`FrequencyQueryHelper`** — Collects bulk sensor samples between `request_start_time` and `request_end_time`; writes time/frequency CSV files in a background process.
- **`FrequencyCommandHelper`** — Registers per-probe G-code commands `FREQUENCY_MEASURE` and `FREQUENCY_QUERY`.
- **`InductanceCoil`** — Main sensor driver; loaded via `load_config_prefix`.

### G-code Commands (multiplexed by `PROBE=<name>`)
- **`FREQUENCY_MEASURE PROBE=<name> [NAME=<str>]`** — Start/stop raw frequency sample collection; writes CSV to `<vsd_dir>/frequency_data/frequency-<name>-<NAME>.csv`.
- **`FREQUENCY_QUERY PROBE=<name>`** — Report the most recent frequency sample (takes 0.3 s of samples).
- **`SET_TRIG_FREQ PROBE=<name> TRIG_FREQ_HT=<int> TRIG_FREQ_LT=<int>`** — Update trigger frequency thresholds at runtime.
- **`INDUCTANCE_COIL_QUERY PROBE=<name>`** — Report current sensor state/status.

### Key Config Options
- `freq_cal_mode` (0=fixed-time, 1=fixed-pulse-count) — Calibration mode.
- `freq_cal_cycle` (float, s) — Calibration window duration (fixed-time mode).
- `capture_over_cnt` (int, default 1000) — Max capture count before overflow.
- `cal_time_out` (float, default 1.0 s) — Calibration timeout.
- `trg_freq_ht` / `trg_freq_lt` (float, default 1200000 Hz) — High and low trigger frequencies.
- `trigger_mode` (int) — Trigger mode select.
- `trigger_invert` (bool) — Invert trigger polarity.
- `max_freq` / `min_freq` (int) — Sanity range for frequency readings.
- `cal_window_size` (int, 1–50) — Sliding window size for frequency averaging.
- `date_rate` (int, default 1000) — Bulk sensor data rate (samples/s).

### Constants
- `MAX_INDUCTANCE_COIL_FREQUENCY = 2000000` Hz
- `MIN_INDUCTANCE_COIL_FREQUENCY = 1000000` Hz
- `BATCH_UPDATES = 0.100` s

### Bulk Sensor Integration
The module uses `bulk_sensor.FixedFreqReader` and `bulk_sensor.BatchBulkHelper` to receive batched frequency measurements from the MCU and exposes a Moonraker dump endpoint `inductance_coil/dump_inductance_coil`.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires custom MCU firmware commands (`config_inductance_coil`, frequency capture commands) not present in upstream Klipper MCU firmware.
- Uses `bulk_sensor.FixedFreqReader` — this may be a fork-modified version of the upstream bulk sensor helper.
- CSV output directory falls back to `/userdata/gcodes/frequency_data` if no virtual_sdcard is configured — Snapmaker-specific path.
- `multiprocessing.Process` is used to write CSV files in the background; this may conflict with Klipper's MCU restart/shutdown sequencing.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, multiprocessing, os, time
+import shutil, pathlib
+from . import probe, bulk_sensor
+from . import probe_inductance_coil
+
+MAX_INDUCTANCE_COIL_FREQUENCY = 2000000
+MIN_INDUCTANCE_COIL_FREQUENCY = 1000000
+BATCH_UPDATES = 0.100
+
+class FrequencyQueryHelper: ...
+class FrequencyCommandHelper:
+    def register_commands(self, name):
+        gcode.register_mux_command("FREQUENCY_MEASURE", "PROBE", name, ...)
+        gcode.register_mux_command("FREQUENCY_QUERY", "PROBE", name, ...)
+
+class InductanceCoil:
+    def __init__(self, config, mcu):
+        ...
+        self.gcode.register_mux_command("SET_TRIG_FREQ", "PROBE", ...)
+        self.gcode.register_mux_command("INDUCTANCE_COIL_QUERY", "PROBE", ...)
+        self.batch_bulk.add_mux_endpoint(
+            "inductance_coil/dump_inductance_coil", "sensor", ...)
```
</details>
