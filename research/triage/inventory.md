# Fork Change Inventory

**Generated from:** `/research/modules/*.md` and `/research/README.md`  
**Upstream HEAD compared:** `2f05309d` — "stm32: usbotg block next bulk_in if buffer not empty"  
**Inventory Date:** 2026-03-30

This is a flat list of every discrete fork change cross-referenced against
upstream Klipper HEAD for triage. Items are numbered for reference in the
triage report.

---

## Legend

| Column | Meaning |
|--------|---------|
| **ID** | Unique triage item identifier |
| **File** | Repository-relative path |
| **Type** | `add` / `mod` / `del` |
| **Description** | One-line summary of change |
| **Motivation** | Inferred reason for divergence |
| **Tier** | 1=Drop · 2=Adapt · 3=Layer · 4=Keep |

---

## A — chelper C Extension

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| A1 | `klippy/chelper/__init__.py` | mod | Reverts `defs_steppersync` from `syncemitter`/`steppersyncmgr` API back to classic `steppersync_alloc`/`flush` API | Fork pre-dates the steppersync refactor | 2 |
| A2 | `klippy/chelper/steppersync.c` | del | Upstream steppersync module removed from build | Fork uses older API inlined in `stepcompress.c` | 2 |
| A3 | `klippy/chelper/steppersync.h` | del | Header for upstream steppersync | Same as A2 | 2 |
| A4 | `klippy/chelper/kin_generic.c` | del | Upstream generic stepper kinematics removed from build | Module added to upstream after fork diverged | 1 |
| A5 | `klippy/chelper/Makefile` | add | Standalone Makefile for cross-compiling `c_helper.so` on AArch64 | U1 host is AArch64; Python build env not always available | 4 |

---

## B — klippy/ Core

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| B1 | `klippy/klippy.py` | mod | Adds SCHED_FIFO thread priority, MCU power rail management, `exception_manager` dispatch | Real-time scheduling; U1 power management; coded error routing | 4 |
| B2 | `klippy/mcu.py` | mod | Removes `MCURestartHelper`, `DummyResponse`, ADC batch; rewrites ~500 lines | Fork pre-dates these upstream refactors | 2 |
| B3 | `klippy/toolhead.py` | mod | Reverts `MotionQueuing`; restores `max_smoothed_v2` look-ahead; adds `max_logical/physical_extruder_num`, `SWITCH_OF_EXTENDED_EXTRUDER`, `SET_MAX_Z_ACCEL/VELOCITY`, coded errors, print-line stamping | Fork pre-dates MotionQueuing; U1 multi-extruder additions | 2 |
| B4 | `klippy/gcode.py` | mod | Coded error IDs for G-code faults; reverts `Coord` namedtuple class definition | Exception system integration; pre-dates `Coord` refactor | 3 |
| B5 | `klippy/webhooks.py` | mod | Removes `msgspec` optional dependency; uses plain `json` | `msgspec` not installed on U1 AArch64 Python env | 2 |
| B6 | `klippy/stepper.py` | mod | Adds `type`/`index` fields to stepper MCU commands for PLR position identification | Power-loss recovery needs per-stepper identity in MCU flash | 4 |
| B7 | `klippy/reactor.py` | mod | Removes `assert_no_pause` context manager | MotionQueuing removed; context manager no longer needed | 1 |
| B8 | `klippy/configfile.py` | mod | Adds `get_snapmaker_config_dir()` and related path helpers | U1-specific config paths under `/home/lava/` | 4 |
| B9 | `klippy/serialhdl.py` | mod | Minor serial handling changes | Adaptation to AT32 USB serial devices | 4 |
| B10 | `klippy/pins.py` | mod | Minor pin aliasing changes | U1 hardware pin assignments | 4 |
| B11 | `klippy/util.py` | mod | Minor utility function tweaks | U1 build environment adaptations | 4 |
| B12 | `klippy/msgproto.py` | mod | Cosmetic/minor changes | Snapshot divergence | 3 |
| B13 | `klippy/queuelogger.py` | mod | Minor log formatting changes | Fork snapshot divergence | 3 |
| B14 | `klippy/mathutil.py` | mod | Minor numerical utility changes | Fork snapshot divergence | 3 |
| B15 | `klippy/coded_exception.py` | add | New `CodedException` base class with `id/index/code/level` fields | Structured error system for Snapmaker app localisation | 4 |
| B16 | `klippy/exception_manager.py` | add | G-code-accessible error bus (`RAISE_EXCEPTION`, `CLEAR_EXCEPTION`, `QUERY_EXCEPTION`) routing coded JSON to Moonraker | Snapmaker app error display protocol | 4 |
| B17 | `klippy/printer_device_scan.py` | add | Scans `/dev/serial/by-path/` to auto-detect MCU serial ports | U1 has multiple AT32 MCUs on fixed USB paths | 4 |
| B18 | `klippy/queuefile.py` | add | Async atomic file I/O queue using background thread + `rename()` | PLR state files need atomic writes without stalling reactor | 4 |

---

## C — klippy/extras/ Modified Upstream Modules

### Major modifications

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| C1 | `klippy/extras/virtual_sdcard.py` | mod | Adds full PLR subsystem: 10 JSON state files, tool-change tracking, `SDCARD_PRINT_PL_RESTORE`, embedded `GCodeParser` | Power-loss recovery — no upstream equivalent | 4 |
| C2 | `klippy/extras/heaters.py` | mod | Adds `idle_hold_max_power`/`active_hold_max_power` per-heater dynamic limits; JSON PID profiles; relaxes `MAX_HEAT_TIME` to 7s; `min/max_temp_overshoot` config | U1 multi-extruder thermal management | 4 |
| C3 | `klippy/extras/probe.py` | mod | Removes `ProbeResult` namedtuple; reverts to older `do_probe()` return signature | Fork pre-dates ProbeResult introduction | 2 |
| C4 | `klippy/extras/bed_mesh.py` | mod | Integrates `inductance_coil` probe as primary Z sensor; adds `BED_MESH_SAVE_FACTORY`, `BED_MESH_APPLY_FACTORY` commands; factory mesh path `/oem/.bed_202507` | U1 inductive probe; factory mesh calibration workflow | 4 |
| C5 | `klippy/extras/resonance_tester.py` | mod | Removes all Z-axis vibration support (vib_dir 3D→2D); removes `SweepingVibrationsTestGenerator`, `ResonanceTestExecutor`; adds `SM_FAST_SHAPER_CALIBRATE` state machine | U1 is CoreXY; Z vibration not relevant; faster calibration flow | 3 |

### Minor/medium modifications (85+ files)

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| C6 | `klippy/extras/probe_eddy_current.py` | mod | Large reversion (~767 lines): removes `trigger_analog` import, removes `ProbeResult` usage, older API surface | Fork pre-dates eddy current rewrite | 2 |
| C7 | `klippy/extras/tmc.py` | mod | Removes `TMCStallguardDump` class; changes error messages to coded JSON format; rounds TMC temp to int | Fork removes bulk_sensor-dependent class; coded error integration | 2 |
| C8 | `klippy/extras/output_pin.py` | mod | Removes `GCodeRequestQueue`, `PrinterTemplateEvaluator`; reverts to synchronous pin update model | Fork pre-dates async pin update system; no motion_queuing | 2 |
| C9 | `klippy/extras/print_stats.py` | mod | Adds `LOGICAL/PHYSICAL_EXTRUDER_NUM`; persistent JSON state file; exception info tracking; per-extruder flow/preextrude config | Multi-extruder job tracking; exception system | 4 |
| C10 | `klippy/extras/shaper_calibrate.py` | mod | Simplifies `CalibrationData` (drops `name` param, `data_sets` int not list); adds `zvd` shaper type; removes `save_params()` | Simplified for 2D-only resonance tester; zvd shaper added | 2 |
| C11 | `klippy/extras/buttons.py` | mod | Removes `DebounceButton` class | Fork pre-dates DebounceButton addition | 1 |
| C12 | `klippy/extras/stepper_enable.py` | mod | Changes `SET_STEPPER_ENABLE` from `register_mux_command` to plain `register_command` | Fork uses plain command; older API | 1 |
| C13 | `klippy/extras/homing.py` | mod | Minor homing index/flag changes | API snapshot divergence | 3 |
| C14 | `klippy/extras/fan.py` | mod | Minor changes | Snapshot divergence | 3 |
| C15 | `klippy/extras/led.py` | mod | Minor changes | Snapshot divergence | 3 |
| C16 | `klippy/extras/pause_resume.py` | mod | Minor changes | Snapshot divergence | 3 |
| C17 | `klippy/extras/temperature_sensor.py` | mod | Minor changes | Snapshot divergence | 3 |
| C18 | `klippy/extras/gcode_macro.py` | mod | Minor changes | Snapshot divergence | 3 |
| C19 | `klippy/extras/idle_timeout.py` | mod | Minor changes | Snapshot divergence | 3 |
| C20 | `klippy/extras/endstop_phase.py` | mod | Minor changes | Snapshot divergence | 3 |
| C21 | ~65 other extras/*.py files | mod | API signature reversions, Coord tuple usage, minor behavioural differences | Snapshot divergence from pre-fork Klipper baseline | 3 |

### Upstream extras removed from fork

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| C22 | `klippy/extras/ads1220.py` | del | ADS1220 ADC sensor — removed | Not used on U1; load_cell dependency removed | 1 |
| C23 | `klippy/extras/ads1x1x.py` | del | ADS1x1x ADC — removed | Same | 1 |
| C24 | `klippy/extras/bmi160.py` | del | BMI160 IMU — removed | Not on U1 | 1 |
| C25 | `klippy/extras/canbus_stats.py` | del | CAN-bus statistics — removed | No CAN bus on U1 | 1 |
| C26 | `klippy/extras/garbage_collection.py` | del | Python GC tuning — removed | Fork doesn't auto-load it | 1 |
| C27 | `klippy/extras/hx71x.py` | del | HX71x ADC — removed | Not on U1 | 1 |
| C28 | `klippy/extras/icm20948.py` | del | ICM-20948 IMU — removed | Not on U1 | 1 |
| C29 | `klippy/extras/lis3dh.py` | del | LIS3DH accelerometer — removed | Not on U1 | 1 |
| C30 | `klippy/extras/load_cell.py` | del | Load cell — removed | Not on U1 | 1 |
| C31 | `klippy/extras/load_cell_probe.py` | del | Load cell probe — removed | Not on U1 | 1 |
| C32 | `klippy/extras/motion_queuing.py` | del | MotionQueuing helper — removed | Fork doesn't use MotionQueuing architecture | 2 |
| C33 | `klippy/extras/static_pwm_clock.py` | del | Static PWM clock — removed | Not on U1 | 1 |
| C34 | `klippy/extras/temperature_probe.py` | del | Temperature probe — removed | Not on U1 | 1 |
| C35 | `klippy/extras/trigger_analog.py` | del | Trigger analog — removed | Not on U1; eddy current dep | 1 |
| C36 | `klippy/extras/static_digital_output.py` | del | Static digital output — removed | Not on U1 | 1 |

---

## D — klippy/extras/ New Fork-Exclusive Modules

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| D1 | `klippy/extras/filament_detect.py` | add | Multi-slot filament presence detection via GPIO sensors | U1 has per-slot filament switches | 4 |
| D2 | `klippy/extras/filament_feed.py` | add | Motorised filament loader/feeder control with state machine | U1 filament routing mechanism | 4 |
| D3 | `klippy/extras/filament_entangle_detect.py` | add | Spool tangle/resistance detection | U1 filament path monitoring | 4 |
| D4 | `klippy/extras/filament_parameters.py` | add | Per-material parameter store decoded from NFC tags | U1 material management system | 4 |
| D5 | `klippy/extras/filament_protocol.py` | add | Multi-slot filament routing state machine coordinator | U1 4-extruder filament routing | 4 |
| D6 | `klippy/extras/filament_feed_fac_test.py` | add | Factory test mode for filament feed system | U1 manufacturing test | 4 |
| D7 | `klippy/extras/mqtt.py` | add | Paho-MQTT client for Snapmaker app real-time status push | Primary machine-to-app channel | 4 |
| D8 | `klippy/extras/jsonrpc.py` | add | JSON-RPC 2.0 server over MQTT connection | App command/query protocol | 4 |
| D9 | `klippy/extras/machine_state_manager.py` | add | Printer-wide state machine (idle/printing/paused/error/etc.) | App-facing printer lifecycle management | 4 |
| D10 | `klippy/extras/print_task_config.py` | add | Print job metadata store (slicer, file, timestamps, layer info) | App job tracking; PLR metadata | 4 |
| D11 | `klippy/extras/timelapse.py` | add | Camera timelapse capture control on layer change | U1 built-in camera support | 4 |
| D12 | `klippy/extras/inductance_coil.py` | add | Inductive probe driver using Timer2 frequency measurement | U1 per-head inductive Z probe | 4 |
| D13 | `klippy/extras/probe_inductance_coil.py` | add | Integrates inductance coil with Klipper probe API | U1 probe architecture | 4 |
| D14 | `klippy/extras/adc_current_sensor.py` | add | ADC-based current monitoring | U1 motor/heater current sensing | 4 |
| D15 | `klippy/extras/park_detector.py` | add | Tool park state detection via endstop | U1 4-extruder park/pick system | 4 |
| D16 | `klippy/extras/fm175xx_reader.py` | add | FM175xx NFC reader driver via SoC SPI | U1 filament cartridge identification | 4 |
| D17 | `klippy/extras/homing_precise_corexy.py` | add | Enhanced sensorless CoreXY homing with TMC SG threshold tuning | U1 sensorless X/Y homing | 4 |
| D18 | `klippy/extras/homing_xyz_override.py` | add | G28 override implementing U1-specific homing sequence | U1 homing with probe + inductance coil | 4 |
| D19 | `klippy/extras/auto_screws_tilt_adjust.py` | add | Automated bed tramming with motor-driven adjustment | U1 motorised bed levelling | 4 |
| D20 | `klippy/extras/extruder_calibration.py` | add | Extruder rotation distance auto-calibration | U1 calibration workflow | 4 |
| D21 | `klippy/extras/flow_calibrator.py` | add | Extrusion multiplier flow calibration state machine | U1 calibration workflow | 4 |
| D22 | `klippy/extras/power_loss_check.py` | add | Power loss detection + stepper Z position in MCU flash (dual-sector wear-levelled) | PLR system coordinator | 4 |
| D23 | `klippy/extras/purifier.py` | add | Air purifier fan control | U1 built-in air filter | 4 |
| D24 | `klippy/extras/defect_detection.py` | add | Camera-based print defect detection hook | U1 camera + AI defect detection | 4 |
| D25 | `klippy/extras/extruder_config_bak.py` | add | Per-extruder config backup/restore | U1 extruder hot-swap config persistence | 4 |
| D26 | `klippy/extras/setup.py` | add | Module initialisation helper | U1 startup orchestration | 4 |

---

## E — klippy/kinematics/

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| E1 | `klippy/kinematics/extruder.py` | mod | Adds `ExtruderSwitchRecorder`, park/pick system, `ACTIVATE_EXTRUDER`/`DEACTIVATE_EXTRUDER` G-codes, multi-extruder coordination | U1 4-extruder tool-change protocol | 4 |
| E2 | `klippy/kinematics/idex_modes.py` | mod | Simplified two-rail IDEX API vs upstream multi-axis redesign; removes copy/mirror modes | Fork pre-dates IDEX multi-axis refactor | 3 |
| E3 | `klippy/kinematics/cartesian.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E4 | `klippy/kinematics/corexy.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E5 | `klippy/kinematics/delta.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E6 | `klippy/kinematics/corexz.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E7 | `klippy/kinematics/polar.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E8 | `klippy/kinematics/rotary_delta.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E9 | `klippy/kinematics/winch.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E10 | `klippy/kinematics/hybrid_corexy.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E11 | `klippy/kinematics/hybrid_corexz.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E12 | `klippy/kinematics/deltesian.py` | mod | Minor Coord/API reversion | Snapshot divergence | 3 |
| E13 | `klippy/kinematics/none.py` | mod | Minor changes | Snapshot divergence | 3 |

---

## F — src/ Firmware

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| F1 | `src/stm32/at32f403a.c` | add | AT32F403A 240 MHz main board MCU support (ACC USB clock calibration) | U1 uses Artery Technology AT32F403A | 4 |
| F2 | `src/stm32/at32f403a.h` | add | Header for AT32F403A | Same | 4 |
| F3 | `src/stm32/at32f415rc.c` | add | AT32F415RC 144 MHz extruder head MCU support | U1 uses AT32F415RC on extruder heads | 4 |
| F4 | `src/stm32/at32f415rc.h` | add | Header for AT32F415RC | Same | 4 |
| F5 | `src/stm32/inductance_coil.c` | add | Timer2 inductive probe frequency measurement firmware | U1 inductive probe signal processing | 4 |
| F6 | `src/stm32/inductance_coil.h` | add | Header for inductance coil firmware | Same | 4 |
| F7 | `src/stm32/power_loss_check.c` | add | Dual-sector wear-levelled flash state storage | PLR: stepper Z position survives power loss | 4 |

---

## G — lib/ Hardware Libraries

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| G1 | `lib/at32f403a/` (full directory) | add | AT32F403A HAL libraries from Artery Technology | Required to build AT32F403A firmware | 4 |
| G2 | `lib/at32f415/` (full directory) | add | AT32F415RC HAL libraries | Required to build AT32F415RC firmware | 4 |

---

## H — Configuration

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| H1 | `lava/` (full directory) | add | Complete U1 production configuration (printer.cfg + 4× extruder MCU configs + calibration macros + AT32 build configs) | Production firmware as shipped on U1 devices | 4 |
| H2 | `config/` divergences | mod | Minor differences from upstream example configs; some upstream example configs absent | Fork adds U1 configs; some upstream examples not included | 3 |

---

## I — Scripts

| ID | File | Type | Description | Motivation | Tier |
|----|------|------|-------------|------------|------|
| I1 | `scripts/buildcommands.py` | mod | Minor changes to build system | AT32 cross-compilation support | 4 |
| I2 | `scripts/calibrate_shaper.py` | mod | Adapts to fork's simplified `CalibrationData` (no `name` param) | Matches fork's shaper_calibrate.py API | 2 |
| I3 | `scripts/graph_accelerometer.py` | mod | Minor changes matching simplified CalibrationData | Same | 2 |

---

## Summary by Tier

| Tier | Count | Categories |
|------|-------|------------|
| **1 — Drop** | 16 | A4, B7, C11, C12, C22–C31, C33–C36 |
| **2 — Adapt** | 14 | A1, A2, A3, B2, B3, B5, C3, C6, C7, C8, C10, C32, I2, I3 |
| **3 — Layer** | 23 | B4, B12–B14, C5, C13–C21, E2–E13, H2 |
| **4 — Keep** | 51 | A5, B1, B6, B8–B11, B15–B18, C1, C2, C4, C9, D1–D26, E1, F1–F7, G1–G2, H1, I1 |
| **Total** | **104** | |
