# mcu.py

## Summary
`mcu.py` defines the `MCU` class and its command/response wrappers. This is one of the most heavily modified files in the fork. The changes reflect an older Klipper architecture (approximately Klipper 0.11/2024-era) rather than the refactored 2025+ upstream: several classes that were split out upstream (`MCURestartHelper`, `AsyncResponseWrapper`, `DummyResponse`, `MotionQueuing`) are inlined back into `MCU` or removed. Notable additions include: ADC read-tolerance and timing validation (`set_read_tolerance`, `_handle_analog_in_state` guard), a `is_pulse_gpio` parameter for `MCU_endstop`, move-queue management methods (`register_stepqueue`, `flush_moves`, `check_active`, `note_mcu_movequeue_activity`), a `QUERY_ADC_EXCEPT_RECORDER` G-code command, `estimate_clock_systime()` for converting MCU clock ticks to system time (used in `serialhdl.py` error reporting), and `get_max_stepper_error()` for configurable step-error tolerance.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `MCURestartHelper` is a separate class | Restart logic merged back into `MCU` | Older architecture; simplification |
| `AsyncResponseWrapper` provides long-lived response subscriptions | Class removed; `register_response` called directly | Older architecture |
| `DummyResponse` stubs out responses in file-output debug mode | Class removed | File-output debug mode not supported |
| `CommandQueryWrapper.__init__(conn_helper, ...)` | `__init__(serial, ..., error=serialhdl.error)` | Directly uses serial handle; removes `conn_helper` indirection |
| `CommandQueryWrapper.send(..., retry=True)` / `get_response(..., retry=True)` | `retry` parameter removed; always retries | Fork removed `retry=False` fast-fail path from `serialhdl` |
| `MCU_endstop.__init__(mcu, pin_params)` | Adds `is_pulse_gpio=False` parameter; appended to `config_endstop` MCU command | Supports inductance-coil virtual endstops |
| `MCU_adc.setup_adc_sample(report_time, sample_time, sample_count, batch_num, ...)` | `setup_adc_sample(sample_time, sample_count, ...)` — no `report_time` or `batch_num` | Older ADC API |
| `MCU_adc.setup_adc_callback(callback)` | `setup_adc_callback(report_time, callback)` — `report_time` moved here | API reorganisation |
| `MCU_adc` supports batched sampling (`batch_num`, `bytes_per_report`) | Batch path removed; always single-sample | Simplification |
| `MCU_adc._handle_analog_in_state` decodes a packed byte array | Decodes single `value` + `next_clock` directly; optionally validates timing via `read_time_tol` | ADC timing guard for the U1's multiple ADC channels |
| `TRSYNC_TIMEOUT = 0.025` | `TRSYNC_TIMEOUT = 0.050` | Looser timeout for slower extruder MCU comms |
| Step error constant `MAX_STEPCOMPRESS_ERROR = 0.000025` (hardcoded) | `get_max_stepper_error()` reads `max_stepper_error` from config (default 0.000025) | Allows per-MCU tuning |
| `MCU` does not directly manage step queues | `register_stepqueue(stepqueue)`, `flush_moves(print_time, clear_history_time)`, `check_active(print_time, eventtime)`, `note_mcu_movequeue_activity(mq_time, set_step_gen_time)` added | `MotionQueuing` class removed; queue management inlined |

## Additions
- `MCU.get_max_stepper_error()` → `float` from `max_stepper_error` config key.
- `MCU.estimate_clock_systime(clock)` → delegates to `clocksync.estimate_clock_systime(clock)`.
- `MCU.register_stepqueue(stepqueue)` — registers a stepcompress queue for flushing.
- `MCU.flush_moves(print_time, clear_history_time)` — flushes stepcompress queues and steppersync.
- `MCU.check_active(print_time, eventtime)` — checks MCU activity during move generation.
- `MCU_adc.set_read_tolerance(read_time_tol, min_update_ratio)` — configures timing guards on ADC callbacks.
- `MCU.cmd_QUERY_ADC_EXCEPT_RECORDER(gcmd)` — G-code command to dump ADC timing anomaly counters.
- `MCU_endstop.__init__` `is_pulse_gpio` parameter — passed to `config_endstop` firmware command.

## Removals / Overrides
- `MCURestartHelper` class — merged into `MCU`.
- `AsyncResponseWrapper` class — removed.
- `DummyResponse` class — removed.
- `MCU_adc` batch sampling (`batch_num`, `bytes_per_report`, `_old_handle_analog_in_state`, `_unpack_from`) — removed.
- `MCU_pwm.next_aligned_print_time(print_time, allow_early)` — removed.
- `MIN_SCHEDULE_TIME`, `MAX_SCHEDULE_TICKS`, `MAX_NOMINAL_DURATION` constants — removed.
- `MAX_STEPCOMPRESS_ERROR` constant — replaced by `get_max_stepper_error()`.
- `import struct` — removed (was needed for `_unpack_from`).

## Risks / Compatibility Notes
- Removing `retry=True` from `CommandQueryWrapper.send` means there is no fast-fail path; any query that hangs will always wait the full timeout. This could mask transient comms issues.
- `is_pulse_gpio` is always `False` unless explicitly set by an extras module (e.g. `probe_inductance_coil.py`); the default firmware command changes to include a trailing `is_pulse_gpio=%d` field, which requires the corresponding MCU firmware to understand this parameter.
- `TRSYNC_TIMEOUT` doubled to 50 ms — this gives extruder MCUs more time but also means homing probes will wait up to 50 ms longer before detecting a lost trigger.
- The `adc_except_recorder` object is a plain `dict` registered in the printer; it is never garbage-collected and grows without bound if many ADC anomalies accumulate.
- `MCU_adc._handle_analog_in_state` now returns early (dropping the sample) when timing constraints are violated. Callers should not assume every MCU ADC tick generates a callback.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/mcu.py
+++ b/klippy/mcu.py
 # Key structural changes:
 # - DummyResponse, AsyncResponseWrapper, MCURestartHelper removed
 # - CommandQueryWrapper: conn_helper -> serial, retry param removed
 # - MCU_endstop: is_pulse_gpio parameter added
 # - MCU_adc: batch sampling removed; set_read_tolerance added
 # - MCU: register_stepqueue, flush_moves, check_active added
 # - MCU: estimate_clock_systime, get_max_stepper_error added
 # - TRSYNC_TIMEOUT: 0.025 -> 0.050
 # - QUERY_ADC_EXCEPT_RECORDER G-code command added
```

</details>
