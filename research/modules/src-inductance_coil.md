# src/stm32/inductance_coil.c

## Summary
A fork-exclusive MCU firmware module that implements frequency measurement for an inductive proximity sensor (inductance coil) used as a Z-probe or nozzle-height calibration sensor on the Snapmaker U1. The AT32F4x Timer 2 (`TMR2`) input-capture peripheral captures rising/falling edges on PA0, counts pulses over a configurable time window or pulse-count window using Timer 5 (`TMR5`) as a calibration gating counter, computes a moving-average pulse sum, compares it against high/low thresholds, and maps the result to a virtual GPIO state (`OPEN` or `TRIGGERED`). This virtual GPIO state is what the klippy host reads as a probe trigger. The module integrates with Klipper's `sensor_bulk` infrastructure for bulk data reporting and exposes its configuration and query interface via `DECL_COMMAND` entries.

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
- `inductance_coil_crm_tmr_init(struct freq_cal_info *info)` — initialises Timer 2 (`TMR2`) for input-capture pulse counting and Timer 5 (`TMR5`) as a calibration gating counter. The calibration timer period is set by `INPUT_CAPTURE_CAL_CRM_TIM_PR(freq_cal_cycle)` which expands to `CONFIG_CLOCK_FREQ / INPUT_CAPTURE_CAL_CRM_DIV * freq_cal_cycle - 1`; `freq_cal_cycle` is a configurable parameter passed via the `inductance_coil_config` MCU command (in microseconds). The period is **not** fixed at 10 kHz (that constant belongs to `power_loss_check.c`).
- `inductance_coil_dev_init(struct freq_cal_info *info)` — initialises the CRM peripheral clocks (`crm_configuration()`), configures GPIO (`gpio_configuration()`), and sets up the timers (`inductance_coil_crm_tmr_init(info)`). It performs **no OID allocation**; OID allocation is done separately in `command_inductance_coil_config()` via `oid_alloc()`.
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
- **Two timers are hardcoded**: Timer 2 (`TMR2`, PA0) for pulse-counting input capture and Timer 5 (`TMR5`) for calibration gating. Any build that uses Timer 2 **or** Timer 5 for another purpose will conflict (`#define INPUT_CAPTURE_CRM_TIM TMR2` at line 146; `#define INPUT_CAPTURE_CAL_CRM_TIM TMR5` at line 157).
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
+// Uses TMR2 input-capture on PA0 for pulse counting; TMR5 for calibration gating
+// DECL_COMMAND: inductance_coil_config, virtual_gpio_trigger[_with_timer],
+//   inductance_coil_query, query_inductance_coil, query_inductance_coil_status,
+//   query_inductance_coil_config_info
```

</details>
