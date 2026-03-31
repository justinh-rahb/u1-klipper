# src/stm32/inductance_coil.c

## Summary
A fork-exclusive MCU firmware module that implements frequency measurement for an inductive proximity sensor (inductance coil) used as a Z-probe or nozzle-height calibration sensor on the Snapmaker U1. The AT32F4x Timer 2 input-capture peripheral captures rising/falling edges on PA0, counts pulses over a configurable time window or pulse-count window, computes a moving-average pulse sum, compares it against high/low thresholds, and maps the result to a virtual GPIO state (`OPEN` or `TRIGGERED`). This virtual GPIO state is what the klippy host reads as a probe trigger. The module integrates with Klipper's `sensor_bulk` infrastructure for bulk data reporting and exposes its configuration and query interface via `DECL_COMMAND` entries.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No inductance coil support | Full timer-based frequency measurement on AT32F4x (AT32F415 or AT32F403A) | Snapmaker U1 uses an inductive coil for Z-homing/calibration |
| N/A | `MOVING_SUM` circular buffer for windowed pulse averaging | Noise rejection on the frequency measurement |
| N/A | Two frequency calibration modes: `FIXED_TIME_CAL_MODE` and `FIXED_PULSE_NUM_CAL_MODE` | Allows both time-gated and pulse-counted frequency measurement |

## Additions

**Key data structures:**
- `VIRTUAL_GPIO_STATE` enum (`OPEN=0`, `TRIGGERED=1`).
- `FREQ_CAL_MODE` enum (`FIXED_TIME_CAL_MODE=0`, `FIXED_PULSE_NUM_CAL_MODE=1`).
- `MOVING_SUM` struct — circular buffer (max 50 entries) for windowed pulse sum.
- `freq_cal_info` struct — all frequency calibration state: `trigger_mode`, `trigger_invert`, `trg_freq_ht`/`trg_freq_lt` thresholds, `capture_pulse_sum`, `freq_cal_cycle`, `freq_cal_timeout_cycle`, `freq_cal_factor`, `virtual_gpio_state`, `freq_cal_mode`, `moving_sum`.
- `inductance_coil_dev` struct — per-OID device state with timers, flags, and `sensor_bulk` for bulk reporting.
- `timer_config_freq_param` struct — deferred frequency config change parameters.

**Functions:**
- `init_moving_sum`, `add_value`, `reset_buffer`, `get_sum` — `MOVING_SUM` FIFO operations.
- `inductance_coil_crm_tmr_init(struct freq_cal_info *info)` — initialises Timer 2 input-capture and the calibration counter timer at 10 kHz.
- `inductance_coil_dev_init(struct freq_cal_info *info)` — allocates and initialises a device OID.
- ISR handler — updates `g_freq_cal_info.capture_pulse_sum` and `virtual_gpio_state` on each timer interrupt.

**MCU commands (via `DECL_COMMAND`):**
- `command_inductance_coil_config` — configures sampling, trigger mode, invert, thresholds, frequency mode, window size, cal cycle.
- `command_virtual_gpio_trigger_with_timer` — triggers the virtual GPIO with a timer.
- `command_virtual_gpio_trigger` — forces the virtual GPIO state.
- `command_inductance_coil_query` — one-shot query of current state.
- `query_inductance_coil oid=%c rest_ticks=%u` — starts periodic bulk reporting.
- `query_inductance_coil_status oid=%c` — queries status.
- `query_inductance_coil_config_info oid=%c` — reports configuration.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `#if CONFIG_MACH_AT32F4x` gates all hardware code — the module compiles to no-ops on non-AT32 targets. A host-side `probe_inductance_coil.py` extras module is also required.
- `init_moving_sum` calls `shutdown("Invalid buff size!!!")` if `bufferSize==0` or `>50`; this halts the MCU. Callers must validate before calling.
- The module uses a global `g_freq_cal_info` struct rather than per-OID state for the ISR; only one inductance coil device can be active at a time despite the OID allocation.
- Timer 2 is hardcoded (`TMR2`, PA0). Any build that also uses Timer 2 for another purpose will conflict.
- `BYTES_PER_SAMPLE=4` is defined but the `sensor_bulk` integration packs 32-bit values; consumers must know the sample format.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/inductance_coil.c
@@ -0,0 +1,~650 @@
+// New file – inductance coil frequency measurement driver
+// Only active on CONFIG_MACH_AT32F4x (AT32F415 or AT32F403A)
+// Uses TMR2 input-capture on PA0 for pulse counting
+// DECL_COMMAND: inductance_coil_config, virtual_gpio_trigger[_with_timer],
+//   inductance_coil_query, query_inductance_coil, query_inductance_coil_status,
+//   query_inductance_coil_config_info
```

</details>
