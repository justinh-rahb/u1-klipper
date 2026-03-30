# Extras — Minor & Medium Upstream Changes

## Summary
This document covers all `klippy/extras/` files that differ from upstream Klipper but were not given individual module documents. Changes range from API reversions (removing upstream refactors that hadn't been backported to the fork base) through U1-specific additions to bug fixes and cosmetic regressions. Files are grouped by change size (largest first).

---

## `probe_eddy_current.py` (~767 changed lines)

**Nature:** Reversion to older API. The fork is based on an earlier Klipper snapshot; the large diff reflects the upstream rewrite of the eddy current probe subsystem.

**Key changes:**
- Removes `from . import trigger_analog` — fork does not have `trigger_analog.py` (upstream-only)
- Removes `Z_OFFSET_APPLY_PROBE` registration (now handled differently in fork's `probe.py`)
- `sys` import removed
- Many method signatures changed to match older API surface
- The overall structure is older; the diff is mostly upstream additions that didn't make it into the fork

**Risk:** `trigger_analog` module referenced in upstream is absent; any upstream config using `[probe_eddy_current]` with trigger_analog will fail.

---

## `tmc.py` (~282 changed lines)

**Nature:** Removes upstream stall guard dump feature; changes error message format; minor arithmetic tweak.

**Key changes:**
- `TMCStallguardDump` class and all its methods removed (upstream-only feature)
- `from . import bulk_sensor` removed (no bulk_sensor usage after class removal)
- TMC error messages now use coded JSON format: `'{"coded": "0003-0522-0000-0011", "oneshot": 0, "msg":"..."}'` — integrates with `exception_manager` coded exception system
- Temperature rounding: `round(..., 2)` → `round(..., 0)` — TMC temp reported as integer

**Risk:** Coded error JSON in TMC error strings will appear verbatim in logs and Moonraker responses on upstream.

---

## `output_pin.py` (~282 changed lines)

**Nature:** Removes upstream `GCodeRequestQueue` / `PrinterTemplateEvaluator` / `MotionQueuing`-based deferred pin update system.

**Key changes:**
- `GCodeRequestQueue` class removed — upstream introduced this for time-accurate pin value updates synced with motion queuing
- `PrinterTemplateEvaluator` class removed
- `from .display import display` removed
- `motion_queuing` object no longer loaded — fork doesn't have `motion_queuing.py`
- Pin updates revert to simpler synchronous model

**Risk:** Time-accurate G-code pin control (e.g. laser power sync with motion) unavailable; any config relying on `[output_pin]` template evaluation will fail.

---

## `print_stats.py` (~245 changed lines)

**Nature:** Significant expansion to track multi-extruder job state, exception info, and print job metadata.

**Key changes:**
- Added `LOGICAL_EXTRUDER_NUM = 32`, `PHYSICAL_EXTRUDER_NUM = 4`
- `PRINT_STATS_CONFIG_FILE = "print_stats.json"` — persistent job state file
- `PRINT_STATS_DEFAULT_CONFIG` — default dict for `flow_calibrate` and `preextrude_filament` per extruder
- New G-code commands registered (2 additional commands via `register_command`)
- New methods: `_ready()`, `_update_exception_info(id, index, code, message, level)`, `_reset_last_e_position()`
- `set_current_file(filename)` → `set_current_file(filename, reprint=False)`
- `_handle_activate_extruder()` removed (upstream method for extruder switching stats)

**Risk:** Upstream tooling (Moonraker, Fluidd) reading `print_stats` status may encounter unexpected extra fields.

---

## `shaper_calibrate.py` (~218 changed lines)

**Nature:** Simplifies API to remove multi-dataset named tracking; adds `zvd` shaper type.

**Key changes:**
- `AUTOTUNE_SHAPERS` adds `'zvd'` between `'zv'` and `'mzv'`
- `CalibrationData.__init__` drops `name` parameter — was `(name, freq_bins, psd_sum, psd_x, psd_y, psd_z)`, now `(freq_bins, psd_sum, psd_x, psd_y, psd_z)`
- `self.data_sets` is now an integer count (1) not a list
- `calc_freq_response(name, raw_values)` → `calc_freq_response(raw_values)` — `name` removed
- `process_accelerometer_data(name, data)` → `process_accelerometer_data(data)`
- `get_datasets()` method removed
- `save_params()` method removed from `ShaperCalibrate` class
- Data join uses `joined_data_sets = self.data_sets + other.data_sets` (integer add)

**Risk:** Any script calling `shaper_calibrate` API with `name` argument will get `TypeError`; `zvd` shaper is fork-only.

---

## `led.py` (~218 changed lines)

**Nature:** Replaces upstream `SET_LED_TEMPLATE` with a Moonraker webhook endpoint for LED control.

**Key changes:**
- `SET_LED_TEMPLATE` mux G-code command removed
- New Moonraker endpoint: `control/led` registered via `wh.register_mux_endpoint("control/led", 'led', name, self._handle_control_led)`
- New method `_handle_control_led(web_request)` — handles JSON colour commands from Moonraker
- `get_led_count()` added — returns the number of LEDs in the chain
- `set_color(index, color)` renamed from `_set_color` (now public)
- `_template_update()` removed — template-driven LED updates not supported

**Risk:** `SET_LED_TEMPLATE` G-code command unavailable; macros using it will error. LED control only via Moonraker endpoint.

---

## `axis_twist_compensation.py` (~217 changed lines)

**Nature:** API changes to compensation value update and point calculation; `clear_compensations` simplified.

**Key changes:**
- `_update_z_compensation_value(poslist)` → `_update_z_compensation_value(pos)` — takes single pos, not list
- `clear_compensations(axis=None)` → `clear_compensations()` — axis parameter removed
- `_calculate_nozzle_points(sample_count, interval_dist)` — new helper for point calculation
- `callback(mpresult)` → `callback(kin_pos)` — uses kin_pos directly (not ProbeResult)

**Risk:** Any caller passing axis to `clear_compensations()` will fail; removal of ProbeResult coupling.

---

## `homing.py` (~209 changed lines)

**Nature:** Adds inductive coil probe homing method and sensorless stall simulation.

**Key changes:**
- `HomingMove.__init__` gains `sim_stall_set_endstops=None` parameter
- New method `get_mcu_sim_stall_set_endstops()` — returns simulated stall endstop list
- New method `check_all_stepper_no_movement()` — verifies all steppers stopped before homing acceptance
- New method `probing_coil_move(mcu_probe, pos, speed)` — executes homing move using inductance coil
- `verify_no_probe_skew()` removed (upstream method for checking probe tilt)

**Risk:** `probing_coil_move` is coupled to fork-exclusive inductance coil hardware; upstreaming would require adding the method back.

---

## `gcode_move.py` (~199 changed lines)

**Nature:** Adds Moonraker endpoint for print speed control; removes upstream extra-axes handling.

**Key changes:**
- New Moonraker endpoint: `control/print_speed` via `wh.register_endpoint`
- New handler `handle_control_print_speed(web_request)` — sets speed factor from API
- `_handle_analyze_shutdown()` removed
- `_update_extra_axes()` removed — upstream method for extra kinematics axes

**Risk:** Upstream extra-axes kinematics (if configured) will not be updated on move; `_handle_analyze_shutdown` loss may reduce diagnostic info.

---

## `angle.py` (~199 changed lines)

**Nature:** Removes `HelperMT6816` angle sensor class and associated SPI/register read infrastructure.

**Key changes:**
- `HelperMT6816` class and all methods removed (upstream added this sensor type after fork diverged)
- `ANGLE_DEBUG_READ` mux command removed
- `get_static_delay()`, `_read_reg()`, `_send_spi()` etc. removed

**Risk:** MT6816 angle sensors not supported.

---

## `heater_fan.py` (~190 changed lines)

**Nature:** Adds probe-mode fan speed override and stepped fan control.

**Key changes:**
- New G-code commands: `SET_HEATER_FAN`, `SET_PROBE_FAN`, `RESTORE_FAN` (all mux, keyed by fan name)
- New methods: `set_probe_speed()`, `restore_fan_speed()`, `calculate_stepped_fan_speed(temp)`
- Event handlers: `_handle_probe_start()`, `_handle_probe_end()` — reduces fan speed during probing to avoid vibration interference with inductance coil
- `stepped` fan control: linearly interpolates fan speed between temperature thresholds

**Risk:** `SET_HEATER_FAN` and related commands are U1-specific; upstream configs won't have probe events that trigger the speed changes.

---

## `manual_stepper.py` (~183 changed lines)

**Nature:** API changes to `do_move` and `do_homing_move`; removes extra-axes support.

**Key changes:**
- `do_move(movepos, speed, accel, sync=True)` — `get_name()` and `_submit_move()` removed
- `do_homing_move(movepos, speed, accel, triggered, check_trigger)` — simplified signature
- `command_with_gcode_axis()` removed (upstream extra-axes)
- `process_move(print_time, move, ea_index)` removed

---

## `fan.py` (~181 changed lines)

**Nature:** Adds Moonraker control endpoint and changes set_speed API.

**Key changes:**
- `set_speed(print_time, value, control_enable=True)` — parameter order changed from upstream's `set_speed(value, print_time=None)`
- `set_speed_from_command(value, control_enable=True)` — adds `control_enable` param
- `_apply_speed()` removed, inlined into `set_speed()`
- New Moonraker endpoint: `control/main_fan` → `_handle_control_main_fan(web_request)`
- New method `get_all_fan_speed()` — returns current speed of all fans

**Risk:** Callers using old `set_speed(value, print_time)` signature will pass wrong arguments; significant API break from upstream.

---

## `aht10.py` (~171 changed lines)

**Nature:** Removes upstream `AHTBase` abstract base class; simplifies to single concrete `AHT10` class.

**Key changes:**
- `AHTBase` removed — upstream split AHT10/AHT21 behind a base class; fork does not have `AHT21` support
- `_send_init()` abstract method removed
- `_init_sensor()` removed
- Single `AHT10` class handles the sensor directly

---

## `bus.py` (~163 changed lines)

**Nature:** Removes async I2C write status callback; simplifies I2C bus init.

**Key changes:**
- `MCU_I2C.__init__` drops `sw_pins` parameter (fork version has no software I2C fallback support here)
- `_async_write_status()` callback removed
- `_handle_connect()` simplified

---

## `bme280.py` (~138 changed lines)

**Nature:** Renames internal methods; simplifies gas heater calculation.

**Key changes:**
- `_calc_gas_heater_resistance()` → `_calculate_gas_heater_resistance()`
- `_calc_gas_heater_duration()` → `_calculate_gas_heater_duration()`
- `data_ready(stat)` callback inlined

---

## `lis2dw.py` (~141 changed lines)

**Nature:** Removes multi-sensor-type support; simplifies to single sensor.

**Key changes:**
- `__init__(config, lis_type)` → `__init__(config)` — lis_type parameter removed
- Only LIS2DW supported; multi-type dispatch removed

---

## `exclude_object.py` (~156 changed lines)

**Nature:** Adds fine-grained extrusion position tracking for excluded objects.

**Key changes:**
- `_get_extrusion_offsets(num_coord)` → `_get_extrusion_offsets()` — no coord count param
- New methods: `_get_last_position_e()`, `_get_max_position_extruded()`, `_get_max_position_excluded()`, `_get_last_position_e_extruded()`, `_get_last_position_e_excluded()`
- Better E-axis tracking for multi-extruder object exclusion

---

## `input_shaper.py` (~134 changed lines)

**Nature:** Removes upstream `is_enabled()` and extra-axes update; adds persistent param save.

**Key changes:**
- `is_enabled()` removed
- `_update_kinematics()` removed (upstream extra-axes)
- `_save_input_shaper_params()` added — persists shaper settings to config file

---

## `filament_switch_sensor.py` (~126 changed lines)

**Nature:** Adds per-extruder filament check command and changes runout notification signature.

**Key changes:**
- `CHECK_FILAMENT_RUNOUT` mux command added
- `_get_extruder_index(extruder_name)` helper added
- `note_filament_present(is_filament_present, force=False)` — `eventtime` param removed, `force` added

---

## `buttons.py` (~109 changed lines)

**Nature:** Removes `DebounceButton` infrastructure; reverts ADC callback signature.

**Key changes:**
- `DebounceButton` class removed
- `register_debounce_button()` removed
- `register_debounce_adc_button()` removed
- `adc_callback(samples)` → `adc_callback(read_time, read_value)` — older two-param signature

**Risk:** `gcode_button.py` calls `register_debounce_button` — but the fork's `gcode_button.py` also reverts to `register_buttons`, keeping them consistent internally.

---

## `motion_report.py` (~104 changed lines)

**Nature:** Removes upstream `_handle_analyze_shutdown`; adds `start_trapq_client` API.

**Key changes:**
- `_handle_analyze_shutdown()` removed
- `_dump_shutdown()` and `_shutdown()` added (different shutdown handling)
- `start_trapq_client(trapq_name, client)` — new public API for adding trapq listeners

---

## `shaper_defs.py` (~103 changed lines)

**Nature:** Removes upstream helper for expansion-coefficient-based shaper construction.

**Key changes:**
- `_get_shaper_from_expansion_coeffs()` removed — upstream refactored shaper generation; fork does not have this

---

## `gcode_arcs.py` (~96 changed lines)

**Key changes:** Minor API alignment — arc calculation reverted to older method signatures matching fork's `gcode_move.py`.

---

## `pause_resume.py` (~90 changed lines)

**Nature:** Renames PAUSE/RESUME to PAUSE_BASE/RESUME_BASE to allow macro override.

**Key changes:**
- `PAUSE` → `PAUSE_BASE`, `RESUME` → `RESUME_BASE` command registration
- Original `cmd_PAUSE()` renamed to `cmd_PAUSE_BASE()`
- `import logging` added
- Allows `lava/printer.cfg` macros to define custom `PAUSE`/`RESUME` that call `PAUSE_BASE`/`RESUME_BASE`

---

## `mcp4018.py` (~69 changed lines)

**Nature:** Adds software I2C fallback for MCP4018 digital potentiometer.

**Key changes:**
- `SoftwareI2C` class added — bit-banged I2C implementation
- `get_mcu()`, `build_config()` methods on `SoftwareI2C`

---

## `filament_motion_sensor.py` (~69 changed lines)

**Key changes:**
- `_update_filament_runout_pos(eventtime=None, fast_runout=False)` — adds `fast_runout` parameter
- `_handle_printing()` commented out; replaced by `_handle_start_print_job()`

---

## `stepper_enable.py` (~68 changed lines)

**Key changes:**
- `SET_STEPPER_ENABLE` changed from mux command (keyed by stepper name) to plain command
- `set_motors_enable(stepper_names, enable)` removed
- `motor_debug_enable(stepper, enable)` added

---

## `pwm_tool.py` (~63 changed lines)

**Key changes:**
- `PWMHelper.__init__` drops `config` parameter (takes `pin_params` only)
- `_flush_notification(print_time, clock)` signature changed (different from upstream)
- `_gen_intermediate_updates()` removed

---

## `error_mcu.py` (~61 changed lines)

**Key changes:**
- `_handle_analyze_shutdown()` → `_handle_notify_mcu_shutdown()` — renamed to match fork's shutdown event
- Error messages now formatted as coded JSON for `exception_manager` integration
- `import json, re` added

---

## `sx1509.py` (~52 changed lines)

**Key changes:**
- `handle_connect()` → `_build_config()` — renamed; triggers at config build time instead of connect
- Pin setup reordered

---

## `statistics.py` (~44 changed lines)

**Key changes:** Removes upstream stats fields added after fork divergence; minor formatting.

---

## `htu21d.py` (~40 changed lines)

**Key changes:** Minor sensor class refactoring; removes async callback variant.

---

## `tmc_uart.py` (~39 changed lines)

**Key changes:** UART communication fixes; minor timing adjustments for AT32 MCU UART characteristics.

---

## `fan_generic.py` (~38 changed lines)

**Key changes:**
- `set_speed` API aligned with fork's `fan.py` changes
- Control enable parameter added

---

## `verify_heater.py` (~37 changed lines)

**Key changes:**
- Fault message now includes actual temperature and target: `"Heater %s not heating at expected rate, temp: %.2f target: %.2f"`
- `self.heater` null-check added before accessing temperature

---

## `pid_calibrate.py` (~36 changed lines)

**Key changes:**
- `PROFILE` parameter added to `PID_CALIBRATE` command
- Checks `heater.allow_pid_calibrate` flag before proceeding
- `ignore_pid_json` attribute checked to conditionally skip JSON profile logic

---

## `tmc2130.py` (~34 changed lines)

**Key changes:** Minor register definitions aligned to fork's TMC usage patterns; `TMCStallguardDump` wiring removed.

---

## `temperature_combined.py` (~70 changed lines)

**Key changes:** Sensor status check changed; `get_status()` callback approach modified.

---

## `safe_z_home.py` (~10 changed lines)

**Key changes:**
- Removes `manual_probe.lookup_z_endstop_config()` call (upstream API not in fork)
- Directly reads `stepper_z` config section instead
- `toolhead.set_position(pos, homing_axes="z")` unchanged

---

## `gcode_button.py` (~8 changed lines)

**Key changes:**
- `register_debounce_button()` → `register_buttons()` — matches fork's simplified `buttons.py`
- `register_debounce_adc_button()` → `register_adc_button()`

---

## `gcode_macro.py` (~17 changed lines)

**Key changes:**
- `reactor.assert_no_pause()` context manager removed (fork's `reactor.py` removed this)
- Status lookup now directly calls `reactor.monotonic()` without assert wrapper

---

## Small / Cosmetic Changes (< 10 lines)

| File | Change |
|------|--------|
| `temperature_sensor.py` | `round(..., 2)` → `round(..., 0)` — temperature reported as integer |
| `idle_timeout.py` | `timeout_on_pause` config option added; `idle_timeout` removed from `get_status()` |
| `homing_override.py` | `homing_axes` changed from string concatenation to list append |
| `save_variables.py` | Uppercase variable name restriction removed |
| `firmware_retraction.py` | Typo introduced: "paramters" instead of "parameters" |
| `temperature_mcu.py` | `setup_adc_callback(REPORT_TIME, cb)` → `setup_adc_callback(cb)` |
| `temperature_fan.py` | `set_tf_speed` → `set_speed`; arg order change in `fan.set_speed()` call |
| `sht3x.py` | Minor I2C transaction timing fix |
| `servo.py` | Minor timing parameter adjustment |
| `bed_tilt.py` | `probe_finalize` signature updated (offsets, positions) |
| `hall_filament_width_sensor.py` | Minor format string change |
| `adc_scaled.py` | Minor cleanup |
| `heater_bed.py` | Minor config reading order change |
| `pwm_cycle_time.py` | Minor timing calculation fix |
| `tmc2660.py` | Register cleanup |
| `smart_effector.py` | Minor probe sequence adjustment |
| `pulse_counter.py` | Minor callback signature change |
| `adxl345.py` | Removes newer bulk_sensor API usage |
| `bulk_sensor.py` | Older callback API kept |
| `dotstar.py` | Minor LED chain init order |
| `ds18b20.py` | Minor sensor read timing |
| `endstop_phase.py` | Minor homing index type change |
| `extruder_stepper.py` | Older extruder sync API |
| `bltouch.py` | Minor pin state handling |
| `controller_fan.py` | Minor enable/disable timing |
| `delta_calibrate.py` | Probe result indexing (uses `[2]` not `.bed_z`) |
| `display/*.py` | Various display driver fixes backported |
| `ldc1612.py` | Removes upstream trigger_analog integration |
| `force_move.py` | `STEPPER_BUZZ`/`FORCE_MOVE` changed from mux to non-mux commands |
| `manual_probe.py` | Removes `ProbeResult` namedtuple creation helper |
| `quad_gantry_level.py` | `probe_finalize(offsets, positions)` + `p[2]` instead of `p.bed_z` |
| `z_tilt.py` | Same probe_finalize signature update |
| `probe_eddy_current.py` | Removes `trigger_analog` import (module doesn't exist in fork) |
| `screws_tilt_adjust.py` | Minor probe result indexing |
| `skew_correction.py` | Minor matrix calculation |
| `spi_temperature.py` | Minor SPI transaction |
| `replicape.py` | Minor pin init |
| `palette2.py` | Minor command |
| `neopixel.py` | Minor LED update |
| `multi_pin.py` | Minor pin handling |
| `query_adc.py` | Minor ADC callback |
| `pca9533.py` / `pca9632.py` | Minor I2C write |
| `tmc2208.py` / `tmc2209.py` / `tmc2240.py` / `tmc5160.py` | Minor register/timing adjustments |
| `z_thermal_adjust.py` | Minor temp sensor integration |
| `tsl1401cl_filament_width_sensor.py` | Minor sensor timing |

---

## `temperature_sensors.cfg` (~706 changed lines)

**Nature:** Adds a complete high-precision NTC 100K 3950 thermistor lookup table.

**Key changes:**
- Adds `[adc_temperature NTC_100K_3950_PRECISE]` section with temperature/resistance pairs from -50°C to 300°C at 1°C intervals
- Also adds similar tables for other common thermistor values used in U1 extruders
- Total ~700 lines of calibration data

**Risk:** This is additive only; no existing entries changed. Safe for upstream use except the section names are U1-specific.
