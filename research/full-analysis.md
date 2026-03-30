# Snapmaker U1 Klipper Fork — Full Analysis

> **Single-file version.** This document concatenates the master index and all module analyses into one navigable document.
> For the full index with hyperlinks to individual files, see [`research/README.md`](README.md).

---

## Top-Level Table of Contents

1. [Master Index & Key Findings](#snapmaker-u1-klipper-fork--research-index)
2. [New Fork-Exclusive Extras (26 modules)](#filament_detectpy)
3. [Significantly Modified Upstream Extras](#major-upstream-modified-extras)
4. [Minor/Medium Modified Upstream Extras (85+ files)](#extras--minor--medium-upstream-changes)
5. [New Core klippy/ Modules](#klippycoded_exceptionpy)
6. [Modified Core klippy/ Modules](#klippyklippypy)
7. [Kinematics Changes](#klippykinematicsextruderpy--extruder-switching-park--pick)
8. [chelper C Extension Changes](#klippychelper--c-helper-layer-changes)
9. [src/ Firmware Modules](#srcstm32at32f403ac--at32f403a-main-board-mcu)
10. [Hardware Libraries](#hardware-libraries-libat32f403a-libat32f415-librp2040)
11. [lava/ Production Configuration](#lava--snapmaker-u1-production-configuration-directory)
12. [config/ Changes](#config--upstream-config-changes)
13. [scripts/ Changes](#scripts--script-changes)

---

# Snapmaker U1 Klipper Fork — Research Index

## Fork Identity

| Field | Value |
|-------|-------|
| **Fork Repository** | `justinh-rahb/u1-klipper` (community mirror of Snapmaker U1 Klipper) |
| **Fork HEAD** | `6491ebab3831112a6549539a87c068ef34bc6583` |
| **Upstream Compared Against** | `github.com/Klipper3d/klipper` HEAD (latest `master`) |
| **Upstream Snapshot Date** | 2026-03-30 |
| **Upstream HEAD** | `2f053099` — "stm32: usbotg block next bulk_in if buffer not empty" |
| **Fork Base Estimate** | Mid-2024 Klipper snapshot (based on copyright year "2024" in modified files; `chelper/__init__.py` copyright "2016-2021" unchanged; `heaters.py` copyright reverted to "2016-2020") |
| **Primary Target Hardware** | Snapmaker U1 — CoreXY, 4-extruder, AArch64 SoC host, AT32F403A main MCU, AT32F415RC × 4 extruder MCUs |
| **Research Date** | 2026-03-30 |

---

## High-Level Change Summary

| Category | Count | Details |
|----------|-------|---------|
| **New klippy/extras/ modules** | 26 | Filament system (6), communication (2), machine management (3), hardware sensors (5), calibration/homing (5), auxiliary (5) |
| **Upstream-only extras removed from fork** | 15 | `ads1220`, `ads1x1x`, `bmi160`, `canbus_stats`, `garbage_collection`, `hx71x`, `icm20948`, `lis3dh`, `load_cell`, `load_cell_probe`, `motion_queuing`, `static_pwm_clock`, `temperature_probe`, `trigger_analog`, `static_digital_output` |
| **Upstream extras significantly modified** | 5 | `virtual_sdcard` (+1919 lines), `bed_mesh` (+961), `resonance_tester` (+772), `heaters` (+670), `probe` (+502) |
| **Upstream extras with minor/medium changes** | ~85 | API reversions, U1-specific additions, signature changes |
| **New core klippy/ modules** | 4 | `coded_exception`, `exception_manager`, `printer_device_scan`, `queuefile` |
| **Modified core klippy/ modules** | 14 | `klippy.py`, `mcu.py`, `toolhead.py`, `gcode.py`, `webhooks.py`, `stepper.py`, `reactor.py`, `configfile.py`, `serialhdl.py`, `pins.py`, `util.py`, `msgproto.py`, `queuelogger.py`, `mathutil.py` |
| **New src/ firmware modules** | 6 | `at32f403a.c/h`, `at32f415rc.c/h`, `inductance_coil.c/h`, `power_loss_check.c` |
| **Modified kinematics files** | 13 | All kinematics files differ (API versioning); `extruder.py` and `idex_modes.py` have major changes |
| **Modified chelper C files** | 17 | API revert from upstream steppersync refactor; `kin_generic.c` removed |
| **New library directories** | 2 | `lib/at32f403a/` (AT32F403A HAL), `lib/at32f415/` (AT32F415 HAL) |
| **New config directory** | 1 | `lava/` — complete U1 production configuration |
| **Fork-exclusive test files** | 2 | `test/klippy/snapmaker-lava-p1.cfg`, `test/klippy/snapmaker-lava-p1.test` |
| **Total files different from upstream** | ~375 | Files changed + fork-only + upstream-only |
| **Total fork-exclusive files (excl. research)** | ~48 | New files added by fork not present in upstream |

---

## Key Findings

### 1. Power-Loss Recovery (PLR) System — Most Extensive Addition
`virtual_sdcard.py` is transformed from a simple G-code streamer into a comprehensive print job supervisor that continuously snapshots the full printer state across **10 JSON files** in `/home/lava/printer_data/klippy/`. The system tracks temperatures, positions, flow rates, fan speeds, bed mesh, tool assignments, pressure advance, layer info, and object exclusions. On power restoration, `SDCARD_PRINT_PL_RESTORE` re-reads these files and seeks to the interrupted G-code line. This integrates with `power_loss_check.c` (which stores stepper Z position in MCU flash), `queuefile.py` (async atomic writes), and `print_task_config.py` (job metadata). **This entire subsystem has no upstream equivalent and is deeply tied to the `/home/lava/` path structure.**

### 2. AT32 MCU Support — Custom Hardware Layer
The U1 uses Artery Technology AT32 MCUs which are STM32-compatible but run at 240 MHz (main board, AT32F403A) and 144 MHz (extruder heads, AT32F415RC). These are disguised as `stm32f103xe` and `stm32f105xc` to the Klipper build system. Two complete HAL libraries (`lib/at32f403a/`, `lib/at32f415/`) and four new `src/stm32/` files implement the hardware differences. Notably, `at32f403a.c` uses the AT32's ACC (Auto Clock Calibration) to achieve the 240 MHz clock from the USB SOF signal — no external crystal needed.

### 3. Inductive Probe Z-Sensing — Fork-Exclusive Hardware
The U1 uses inductive probes on each extruder head for both Z-offset calibration and bed mesh generation. This required adding three modules: `inductance_coil.py` (driver), `probe_inductance_coil.py` (integration with Klipper probe API), and `src/stm32/inductance_coil.c` (Timer2 frequency measurement firmware). `bed_mesh.py` was modified to prefer the inductance coil probe over the standard probe when `[inductance_coil]` sections are configured. This is a significant and well-engineered addition.

### 4. 4-Extruder Multi-Material Architecture
The U1 supports T0–T3 tool changes. This required: `kinematics/extruder.py` gaining an `ExtruderSwitchRecorder` and park/pick system; `virtual_sdcard.py` tracking `T0`–`T31` commands; `print_stats.py` tracking `LOGICAL_EXTRUDER_NUM = 32` and `PHYSICAL_EXTRUDER_NUM = 4`; `park_detector.py` (new) detecting tool park state; `filament_protocol.py` (new) coordinating multi-slot filament routing; and `lava/printer.cfg` having 4× extruder + 4× extruder MCU + 4× inductance coil + 4× park detector + 4× PLR check. The `kinematics/idex_modes.py` is significantly simplified compared to upstream's multi-axis redesign.

### 5. Structured Exception System
The fork adds a two-level exception architecture: `coded_exception.py` defines `CodedException` with `id/index/code/level` fields; `exception_manager.py` provides a G-code-accessible error bus (`RAISE_EXCEPTION`, `CLEAR_EXCEPTION`, `QUERY_EXCEPTION`) that routes errors to Moonraker. TMC driver errors, MCU shutdown events, and heater failures all emit coded JSON strings (`{"coded": "0003-0522-0000-0011", "oneshot": 0, "msg": "..."}`) that the Snapmaker app can parse for localised error messages. This entirely replaces Klipper's standard plain-text error strings.

### 6. API Reversions — Fork is Based on ~Mid-2024 Klipper
The large number of `diff` lines in "modified" files is primarily because **the fork uses an older Klipper API surface**. Concretely: `probe.py` removes `ProbeResult` namedtuple (upstream introduced mid-2024); `chelper` removes `steppersync.c` and `kin_generic.c`; `toolhead.py` reverts the `MotionQueuing` / `extra_axes` refactor; `output_pin.py` removes `GCodeRequestQueue`; `buttons.py` removes `DebounceButton`; `stepper_enable.py` changes `SET_STEPPER_ENABLE` from mux to plain command. This means **the fork is not a clean divergence — it's a snapshot of an older Klipper with U1 additions on top**.

### 7. MQTT + JSON-RPC Communications Layer
`mqtt.py` (new) provides a Paho-MQTT client for real-time printer state push to the Snapmaker app. `jsonrpc.py` (new) provides a JSON-RPC 2.0 server layer over the MQTT connection. Together they form the primary machine-to-app communication channel, bypassing the standard Moonraker/Fluidd WebSocket API for real-time status updates. This requires `paho-mqtt` and `cryptography` Python packages not in upstream's `klippy-requirements.txt`.

### 8. Resonance Testing Simplified to 2D
`resonance_tester.py` removes all Z-axis vibration support — all `vib_dir` tuples are reduced from 3D `(x,y,z)` to 2D `(x,y)`. `SweepingVibrationsTestGenerator` and `ResonanceTestExecutor` classes are removed. A new `SM_FAST_SHAPER_CALIBRATE` command does automated X+Y calibration via state machine. `shaper_calibrate.py` has its `CalibrationData` simplified to drop named datasets. This is consistent with U1's hardware (LIS2DW accelerometers on print heads; Z vibration not relevant for CoreXY shaping).

### 9. lava/ — Complete Production Configuration
The `lava/` directory contains the full production config as shipped on U1 devices: 96 config sections, 4-extruder setup, sensorless homing, NFC filament ID reading, MQTT, power-loss recovery, bed mesh, air purification, and timelapse. The AT32 MCU firmware `.config` files are here too. This is the definitive reference for how all fork modules interoperate.

### 10. NFC Filament ID Reading
`fm175xx_reader.py` (new) drives FM175xx NFC ICs via SoC SPI to identify Snapmaker-branded filament cartridges. Each extruder head has an NFC reader (2 on SoC SPI bus 2 dev 0, 2 on dev 1). The `filament_parameters.py` module decodes the NFC tag data to retrieve filament type, color, diameter, and manufacturer. This is proprietary Snapmaker DRM/material management integration with no upstream equivalent.

---

## Upstream Compatibility Assessment

**Verdict: Not directly rebassable onto current upstream without significant work.**

The fork diverges from upstream in four independent dimensions:

1. **API reversions** — ~85 extra files differ because the fork uses an older Klipper API (pre-`ProbeResult`, pre-`MotionQueuing`, pre-`steppersync` refactor, pre-`kin_generic`). Rebasing would require either pulling these upstream refactors into all U1-specific code, or reverting them in 85 files.

2. **New dependencies** — Fork requires `paho-mqtt`, `cryptography`, `spidev`, and potentially `numpy` patterns incompatible with upstream. These are not in `klippy-requirements.txt`.

3. **Hard-coded paths** — `/home/lava/printer_data/klippy/`, `/oem/.bed_202507`, `/userdata/.bed_202507`, `/dev/ttyS6`, USB by-path addresses are all U1-specific and scattered throughout the codebase.

4. **Missing upstream features** — 15 upstream extras are absent (load cell, garbage collection, new sensors, etc.); the chelper `steppersync` refactor and `kin_generic` are missing. Upstream configs referencing these will fail.

**Estimated rebase effort:** High (weeks). A clean approach would be to start from current upstream and re-apply U1-specific features as a set of patches, rather than trying to forward-port the existing fork.

---

## Table of Contents

### Raw Diffs
- [`research/raw/full.diff`](raw/full.diff) — Complete unified diff (2 MB)
- [`research/raw/klippy.diff`](raw/klippy.diff) — klippy/ directory diff
- [`research/raw/klippy-extras.diff`](raw/klippy-extras.diff) — klippy/extras/ diff
- [`research/raw/klippy-kinematics.diff`](raw/klippy-kinematics.diff) — kinematics diff
- [`research/raw/klippy-chelper.diff`](raw/klippy-chelper.diff) — chelper C code diff
- [`research/raw/scripts.diff`](raw/scripts.diff) — scripts/ diff
- [`research/raw/config.diff`](raw/config.diff) — config/ diff
- [`research/raw/root-files.diff`](raw/root-files.diff) — Root Makefile/README diff
- [`research/raw/name-status.txt`](raw/name-status.txt) — File manifest (all changed/added/removed)

### Module Documentation

#### New klippy/extras/ Modules (Fork-Exclusive)
| File | Module | Description |
|------|--------|-------------|
| [extras-filament_detect.md](modules/extras-filament_detect.md) | `filament_detect.py` | Multi-slot filament presence detection |
| [extras-filament_feed.md](modules/extras-filament_feed.md) | `filament_feed.py` | Motorised filament loader/feeder |
| [extras-filament_entangle_detect.md](modules/extras-filament_entangle_detect.md) | `filament_entangle_detect.py` | Tangle detection |
| [extras-filament_parameters.md](modules/extras-filament_parameters.md) | `filament_parameters.py` | Per-material parameter store (NFC) |
| [extras-filament_protocol.md](modules/extras-filament_protocol.md) | `filament_protocol.py` | Multi-slot filament routing protocol |
| [extras-filament_feed_fac_test.md](modules/extras-filament_feed_fac_test.md) | `filament_feed_fac_test.py` | Factory test mode |
| [extras-mqtt.md](modules/extras-mqtt.md) | `mqtt.py` | MQTT client (Snapmaker app comms) |
| [extras-jsonrpc.md](modules/extras-jsonrpc.md) | `jsonrpc.py` | JSON-RPC 2.0 over MQTT |
| [extras-machine_state_manager.md](modules/extras-machine_state_manager.md) | `machine_state_manager.py` | Printer state machine |
| [extras-print_task_config.md](modules/extras-print_task_config.md) | `print_task_config.py` | Print job metadata |
| [extras-timelapse.md](modules/extras-timelapse.md) | `timelapse.py` | Camera timelapse control |
| [extras-inductance_coil.md](modules/extras-inductance_coil.md) | `inductance_coil.py` | Inductive probe driver |
| [extras-probe_inductance_coil.md](modules/extras-probe_inductance_coil.md) | `probe_inductance_coil.py` | Probe API integration |
| [extras-adc_current_sensor.md](modules/extras-adc_current_sensor.md) | `adc_current_sensor.py` | ADC current monitoring |
| [extras-park_detector.md](modules/extras-park_detector.md) | `park_detector.py` | Tool park state detection |
| [extras-fm175xx_reader.md](modules/extras-fm175xx_reader.md) | `fm175xx_reader.py` | NFC filament ID reader |
| [extras-homing_precise_corexy.md](modules/extras-homing_precise_corexy.md) | `homing_precise_corexy.py` | Enhanced sensorless CoreXY homing |
| [extras-homing_xyz_override.md](modules/extras-homing_xyz_override.md) | `homing_xyz_override.py` | G28 override for U1 homing sequence |
| [extras-auto_screws_tilt_adjust.md](modules/extras-auto_screws_tilt_adjust.md) | `auto_screws_tilt_adjust.py` | Automated bed tram |
| [extras-extruder_calibration.md](modules/extras-extruder_calibration.md) | `extruder_calibration.py` | Extruder rotation calibration |
| [extras-flow_calibrator.md](modules/extras-flow_calibrator.md) | `flow_calibrator.py` | Extrusion multiplier calibration |
| [extras-power_loss_check.md](modules/extras-power_loss_check.md) | `power_loss_check.py` | Power loss detection + MCU flash state |
| [extras-purifier.md](modules/extras-purifier.md) | `purifier.py` | Air purifier control |
| [extras-defect_detection.md](modules/extras-defect_detection.md) | `defect_detection.py` | Print defect detection |
| [extras-extruder_config_bak.md](modules/extras-extruder_config_bak.md) | `extruder_config_bak.py` | Extruder config backup |
| [extras-setup.md](modules/extras-setup.md) | `setup.py` | Module setup/init helper |

#### Significantly Modified Upstream Extras
| File | Key Change |
|------|-----------|
| [extras-modified-upstream.md](modules/extras-modified-upstream.md) | `virtual_sdcard` (PLR), `heaters` (dynamic power/PID profiles), `probe` (API revert), `bed_mesh` (inductance coil), `resonance_tester` (2D only, fast calibrate) |

#### Minor/Medium Modified Upstream Extras
| File | Coverage |
|------|---------|
| [extras-minor-changes.md](modules/extras-minor-changes.md) | 85+ files: tmc, output_pin, print_stats, shaper_calibrate, led, homing, fan, pause_resume, buttons, and all others |

#### New Core klippy/ Modules
| File | Module | Description |
|------|--------|-------------|
| [klippy-coded_exception.md](modules/klippy-coded_exception.md) | `coded_exception.py` | Structured error base class |
| [klippy-exception_manager.md](modules/klippy-exception_manager.md) | `exception_manager.py` | Centralised error bus + G-codes |
| [klippy-printer_device_scan.md](modules/klippy-printer_device_scan.md) | `printer_device_scan.py` | MCU serial port auto-detection |
| [klippy-queuefile.md](modules/klippy-queuefile.md) | `queuefile.py` | Async atomic file I/O queue |

#### Modified Core klippy/ Modules
| File | Key Change |
|------|-----------|
| [klippy-klippy.md](modules/klippy-klippy.md) | SCHED_FIFO thread priority, MCU power rail management, exception dispatch |
| [klippy-mcu.md](modules/klippy-mcu.md) | ~500 lines changed; removes `MCURestartHelper`, ADC batch, `DummyResponse` |
| [klippy-toolhead.md](modules/klippy-toolhead.md) | Reverts look-ahead algorithm; removes `MotionQueuing`/`extra_axes` |
| [klippy-gcode.md](modules/klippy-gcode.md) | Coded error IDs; `Coord` namedtuple revert |
| [klippy-webhooks.md](modules/klippy-webhooks.md) | Removes `msgspec` usage |
| [klippy-stepper.md](modules/klippy-stepper.md) | Adds power-loss `type`/`index` fields to MCU commands |
| [klippy-reactor.md](modules/klippy-reactor.md) | Removes `assert_no_pause` context manager |
| [klippy-configfile.md](modules/klippy-configfile.md) | U1-specific config path helpers |
| [klippy-serialhdl.md](modules/klippy-serialhdl.md) | Serial handling minor changes |
| [klippy-pins.md](modules/klippy-pins.md) | Minor pin handling changes |
| [klippy-util.md](modules/klippy-util.md) | Minor utility changes |
| [klippy-minor-core-changes.md](modules/klippy-minor-core-changes.md) | `msgproto`, `queuelogger`, `mathutil` — cosmetic |

#### Kinematics
| File | Key Change |
|------|-----------|
| [kinematics-extruder.md](modules/kinematics-extruder.md) | `ExtruderSwitchRecorder`, park/pick system, multi-extruder G-codes |
| [kinematics-idex_modes.md](modules/kinematics-idex_modes.md) | Simplified two-rail API vs upstream multi-axis redesign |
| [kinematics-minor-changes.md](modules/kinematics-minor-changes.md) | 11 files: Coord signatures, `_motor_off`, homing indices, `PrinterRail` |

#### chelper C Extension
| File | Key Change |
|------|-----------|
| [chelper-changes.md](modules/chelper-changes.md) | Reverts `steppersync` API; drops `kin_generic.c`; adds cross-compile `Makefile` |

#### src/ Firmware Modules
| File | Key Change |
|------|-----------|
| [src-at32f403a.md](modules/src-at32f403a.md) | AT32F403A 240 MHz main board MCU support |
| [src-at32f415rc.md](modules/src-at32f415rc.md) | AT32F415RC 144 MHz extruder head MCU support |
| [src-inductance_coil.md](modules/src-inductance_coil.md) | Timer2 inductive probe frequency measurement |
| [src-power_loss_check.md](modules/src-power_loss_check.md) | Dual-sector wear-levelled flash state storage |

#### Hardware Libraries
| File | Coverage |
|------|---------|
| [hardware-libs.md](modules/hardware-libs.md) | `lib/at32f403a/` + `lib/at32f415/` HAL libraries |

#### Configuration
| File | Coverage |
|------|---------|
| [lava-directory.md](modules/lava-directory.md) | Complete `lava/` production config; MCU configs; calibration macros |
| [config-changes.md](modules/config-changes.md) | Minor upstream config divergences; missing files |
| [scripts-changes.md](modules/scripts-changes.md) | `buildcommands.py`, `calibrate_shaper.py`, `graph_accelerometer.py` |

---


---

# filament_detect.py

## Summary
`filament_detect.py` implements the `FilamentDetector` class, which manages up to 4 NFC/RFID-based filament identification channels on the Snapmaker U1. At startup (or on filament insert/runout events), it requests the `fm175xx_reader` module to read the MIFARE M1 card embedded in a Snapmaker filament spool. The parsed card data (`filament_protocol.m1_proto_data_parse`) is stored per-channel and broadcast via registered callbacks so other modules (e.g., `print_task_config`) can react to filament type changes. A `startup_stay` flag in a JSON config file controls whether previously-detected filament info is preserved across reboots.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | Full new module: RFID-based filament detection for 4 channels using FM175XX SPI reader and Snapmaker M1-card protocol | U1 hardware has per-channel NFC readers embedded in the filament feeder module; upstream Klipper has no filament-ID concept |

## Additions

### Classes
- **`FilamentDetector`** — Klipper extra loaded as `[filament_detect]`. Manages 4-channel filament info lifecycle.

### G-code Commands
- **`FILAMENT_DT_QUERY CHANNEL=<n>`** — Report vendor, main type, sub type, and ARGB colour for channel `n`.
- **`FILAMENT_DT_UPDATE CHANNEL=<n>`** — Trigger an NFC read for channel `n`, updating stored info asynchronously.
- **`FILAMENT_DT_CLEAR CHANNEL=<n>`** — Trigger a card-clear request for channel `n`, resetting stored info to the blank struct.
- **`FILAMENT_DT_SELF_TEST CHANNEL=<n> [TIMES=100]`** — Run repeated NFC read tests and report success rate plus last-parsed filament data.
- **`FILAMENT_DT_STARTUP_STAY STAY=<0|1> [SAVE=1]`** — Enable/disable the `startup_stay` flag that preserves filament info on reboot; optionally persists to `filament_detect.json`.

### Key Functions / Methods
- `_ready()` — Looks up `filament_feed` and `fm175xx_reader` objects; registers the card-info callback; optionally triggers initial reads for channels that already detect filament.
- `_feed_port_evt_handle(channel, detect)` — Handles `filament_feed:port` events; requests read on insert, clear on removal.
- `_runout_evt_handle(extruder, present)` — Handles `filament_switch_sensor:runout`; aware of multi-feeder modules to decide whether to read or clear.
- `_fm175xx_card_info_deal_callback(channel, operation, result, card_type, card_data)` — Called by `fm175xx_reader` with raw card bytes; delegates to `filament_protocol.m1_proto_data_parse` and calls `_filament_info_update`.
- `register_cb_2_update_filament_info(cb)` — Public API for other modules to subscribe to filament-info change events.
- `get_a_filament_info(channel)` / `get_all_filament_info()` — Return cached info.
- `get_status(eventtime)` — Returns `{'info': ..., 'state': ..., 'config': ...}` for Moonraker/webhooks.
- `factory_reset()` — Resets `startup_stay` to `False` and saves config.

### Config Options (loaded from `filament_detect.json`)
- `startup_stay` (bool, default `False`) — When `True`, the module skips initial NFC reads on startup and keeps whatever info was loaded from the config file.

### Events Consumed
- `filament_feed:port` — Filament feeder port-detect state change.
- `filament_switch_sensor:runout` — Filament runout/resume event.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Depends on three other fork-exclusive modules: `fm175xx_reader`, `filament_protocol`, and `filament_feed`. Cannot run on a stock Klipper build.
- Uses `printer.get_snapmaker_config_dir()` and `printer.load_snapmaker_config_file()` — Snapmaker-specific printer extensions not in upstream.
- Channel count is hard-coded to 4 (`FILAMENT_DT_CHANNEL_NUMS`); a printer with fewer NFC readers will see errors if channels are absent.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, copy, os
+from . import filament_protocol
+from . import fm175xx_reader
+from . import filament_feed
+
+FILAMENT_DT_OK                                  = 0
+FILAMENT_DT_ERR                                 = -1
+FILAMENT_DT_PARAM_ERR                           = -2
+
+FILAMENT_DT_STATE_IDLE                          = 0
+FILAMENT_DT_STATE_DETECTING                     = 1
+FILAMENT_DT_STATE_SELF_TESTING                  = 2
+
+FILAMENT_DT_CHANNEL_NUMS                        = 4
+FILAMENT_DT_CONFIG_FILE                         = "filament_detect.json"
+
+DEFAULT_FILAMENT_DT_CONFIG = {
+    'startup_stay': False
+}
+
+class FilamentDetector:
+    def __init__(self, config) -> None:
+        self.printer = config.get_printer()
+        self.reactor = self.printer.get_reactor()
+        ...
+        gcode.register_command('FILAMENT_DT_QUERY', self.cmd_FILAMENT_DT_QUERY)
+        gcode.register_command('FILAMENT_DT_UPDATE', self.cmd_FILAMENT_DT_UPDATE)
+        gcode.register_command('FILAMENT_DT_CLEAR', self.cmd_FILAMENT_DT_CLEAR)
+        gcode.register_command('FILAMENT_DT_SELF_TEST', self.cmd_FILAMENT_DT_SELF_TEST)
+        gcode.register_command('FILAMENT_DT_STARTUP_STAY', self.cmd_FILAMENT_DT_STARTUP_STAY)
+
+def load_config(config):
+    return FilamentDetector(config)
```
</details>

---

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

---

# filament_entangle_detect.py

## Summary
`filament_entangle_detect.py` implements the `FilamentEntangleDetect` class, which detects filament tangling on the spool by comparing extruder motor movement (via `extruder.find_past_position`) with two optical wheel-encoder pulse counts from the associated `filament_feed` module. A 100 ms periodic timer computes the ratio of actual feed-wheel pulses to expected pulses based on how far the extruder advanced. If the ratio falls below a threshold (indicating the spool stopped turning while the extruder kept moving), a tangle is declared, the print is paused via `PAUSE`, and an exception event is raised. Detection sensitivity and skip length can be tuned per-filament-type, and a user-settable `detect_factor` is persisted to a per-sensor JSON file.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: tangle detection via encoder-vs-extruder motion comparison, with material-specific thresholds and configurable sensitivity | U1 uses a spool holder with dual wheel encoders; tangling is a real failure mode the hardware can detect |

## Additions

### Classes
- **`FilamentEntangleDetect`** — Klipper extra loaded with `load_config_prefix` (section name `[filament_entangle_detect <name>]`).

### G-code Commands
- **`SET_FILAMENT_ENTANGLE_DETECT_FACTOR SENSOR=<name> DETECT_FACTOR=<float>`** — Adjust the per-sensor detection sensitivity factor (minimum 0.5). Persists to `<name>_entangle.json`.

### Key Config Options
- `extruder` — Name of the extruder this sensor monitors.
- `filament_feed` — Name of the associated `filament_feed` instance.
- `skip_length` (float, mm) — Length of filament to extrude before enabling tangle detection after a print starts.

### Detection Logic Constants
- `CHECK_ENTANGLE_INTERVAL = 0.1` s — Timer interval.
- `ENTANGLE_DETECT_LENGTH_DEFAULT = 6.0` mm — Extruder travel per expected encoder pulse (hard filament).
- `ENTANGLE_DETECT_LENGTH_DEFAULT_SOFT = 120.0` mm — Soft filament threshold.
- `ENTANGLE_DETECT_LENGTH_DEFAULT_TPU_*` — TPU-specific variants (60/120/180 mm).
- `ENTANGLE_GLOBAL_SENSITIVITY_HIGH/MEDIUM/LOW = 1.0/1.5/3.0` — Global multipliers selected from `print_task_config['filament_entangle_sen']`.

### Events Consumed
- `print_stats:start` / `print_stats:stop` / `print_stats:paused` — Start/stop/pause the check timer.
- `print_task_config:set_entangle_detect` — Re-arm skip-length when detection is toggled.
- `klippy:ready`, `klippy:shutdown`

### Events Emitted
- `filament_entangle_detect:tangled` — Fired (with extruder index) when a tangle is confirmed; consumed by `flow_calibrator`.
- `print_stats:update_exception_info` — Exception ID 523, code 38.

### Public API
- `skip_entangle_check(skip=False)` — Temporarily disable tangle checking (used by other modules during non-print moves).
- `get_status(eventtime)` — Returns `{'detect_factor': ...}`.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `filament_feed`, `print_task_config`, and `exception_manager` — all fork-exclusive. Will fail silently (`init_ok = False`) if any are absent.
- Uses `extruder.find_past_position(print_time)` which is a fork-added method on the extruder object; not present in upstream.
- Issues `gcode.run_script('\nPAUSE\nM400\n')` from a reactor timer callback — this is a blocking scripted pause that may conflict with upstream pause/resume logic.
- Per-material detection length is tightly coupled to `print_task_config`'s `filament_soft`, `filament_type`, and `filament_sub_type` fields.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, os
+from . import print_task_config
+
+CHECK_ENTANGLE_INTERVAL                     = 0.1
+ENTANGLE_DETECT_LENGTH_DEFAULT              = 6.0
+ENTANGLE_DETECT_LENGTH_DEFAULT_SOFT         = 120.0
+...
+class FilamentEntangleDetect:
+    def __init__(self, config):
+        ...
+        self.gcode.register_mux_command(
+            "SET_FILAMENT_ENTANGLE_DETECT_FACTOR", "SENSOR", self.name,
+            self.cmd_SET_FILAMENT_ENTANGLE_DETECT_FACTOR)
+        self.printer.register_event_handler('print_stats:start',
+                self._handle_start_print_job)
+        self.printer.register_event_handler('print_stats:stop',
+                self._handle_stop_print_job)
+        self.printer.register_event_handler('print_stats:paused',
+                self._handle_pause_print_job)
+        self.printer.register_event_handler('print_task_config:set_entangle_detect',
+                self._handle_set_entangle_detect)
+
+def load_config_prefix(config):
+    return FilamentEntangleDetect(config)
```
</details>

---

# filament_parameters.py

## Summary
`filament_parameters.py` provides the `FilamentParameters` class, a lookup table that maps (vendor, main_type, sub_type) tuples to a set of printing parameters: load/unload temperatures, nozzle-cleaning temperature, pressure-advance `k` value and its calibration range (`flow_k_min`/`flow_k_max`), slow/fast flow velocities, and a softness flag (`is_soft`). The default table ships with roughly 20 material profiles (PLA, PETG, TPU, ABS, ASA, PA, PC, etc.) for generic, Snapmaker, and Polymaker vendors. At startup the module checks a version string against `FILAMENT_PARAMETER_VERSION = '0.0.7'` and resets the persisted JSON config to defaults if the version is stale. Other modules call `get_filament_parameters()`, `get_load_temp()`, etc. to look up the correct temperature for the current filament.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: vendor/type/sub-type indexed filament parameter database with JSON persistence and version migration | U1 uses RFID-identified filament; downstream modules need material-specific temperatures and pressure-advance values without user input |

## Additions

### Classes
- **`FilamentParameters`** — Klipper extra loaded as `[filament_parameters]`.

### G-code Commands
- **`FILAMENT_PARA_GET_ALL_INFO`** — Respond with the full internal parameter dictionary as a string (debug).

### Public API Methods
- `get_filament_parameters(vendor, main_type, sub_type)` → dict — Falls back through vendor_generic / sub_generic if the exact match is absent.
- `get_load_temp(vendor, main_type, sub_type)` → int
- `get_unload_temp(vendor, main_type, sub_type)` → int
- `get_clean_nozzle_temp(vendor, main_type, sub_type)` → int
- `get_flow_temp(vendor, main_type, sub_type)` → int
- `get_flow_k(vendor, main_type, sub_type)` → float
- `get_is_soft(vendor, main_type, sub_type)` → bool
- `reset_parameters()` — Restore defaults and update JSON file.
- `get_status(eventtime)` — Returns a deep copy of the full config dict.

### Config File
- `filament_parameters.json` — Persisted in Snapmaker config dir. Contains a three-level nested dict: `material_type → vendor → sub_type → params`.

### Material Types Covered
PLA, PLA-CF, TPU (with sub-types 95A, 95A HF), PETG (with HF sub-type), PETG-CF, PETG-HF, PCTG, EVA, ABS, ASA, PA, PA-CF, PA6-CF, PA-GF, PA6-GF, PC, PC-ABS.

### Default Unknown Values
- Load/unload: 250 °C; clean nozzle: 170 °C; flow temp: 220 °C; `flow_k`: 0.02; `is_soft`: False.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Uses `printer.get_snapmaker_config_dir()` and `printer.load_snapmaker_config_file()` — Snapmaker-only API.
- Version string `'0.0.7'` is compared against the persisted value; any manual edits to the JSON that include the wrong version will silently wipe user customisations.
- All temperature defaults are hard-coded Snapmaker values; a third-party filament will receive these defaults if its vendor/type is not in the table.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import copy, os, logging
+
+FILAMENT_PARAMETER_VERSION                      = '0.0.7'
+FILAMENT_PARA_CFG_FILE                          = 'filament_parameters.json'
+FILAMENT_PARA_CFG_DEFAULT = {
+    'version': '0.0.6',
+    'PLA': {
+        'vendor_generic': { 'sub_generic': { 'load_temp': 250, ... } },
+        'vendor_Snapmaker': { ... },
+        ...
+    },
+    'TPU': { ... },
+    ...
+}
+
+class FilamentParameters:
+    def __init__(self, config):
+        ...
+        gcode.register_command('FILAMENT_PARA_GET_ALL_INFO',
+                               self.cmd_FILAMENT_PARA_GET_ALL_INFO)
+    def get_filament_parameters(self, filament_vendor, filament_main_type, filament_sub_type):
+        ...  # three-level fallback lookup
+    def get_load_temp(self, ...): ...
+    def get_flow_k(self, ...): ...
+    def reset_parameters(self): ...
+
+def load_config(config):
+    return FilamentParameters(config)
```
</details>

---

# filament_protocol.py

## Summary
`filament_protocol.py` is a pure-logic library module (no Klipper extra entry point) that defines the binary layout of Snapmaker's proprietary MIFARE M1 NFC filament tag and parses raw card bytes into a structured `FILAMENT_INFO_STRUCT` dictionary. The 1 KB card is divided into sections covering vendor/manufacturer strings, material type/sub-type codes, up to 5 RGB colours, physical spool data (diameter, weight, length), drying parameters, hotend temperature range, bed temperature, and manufacturing date. The parser also verifies an RSA-PKCS#1v15 / SHA-256 digital signature using one of 10 embedded public keys (key version 0–9) before accepting the data. If the signature check fails, `FILAMENT_PROTO_SIGN_CHECK_ERR` is returned and the info is treated as unofficial (`OFFICIAL = False`).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: proprietary binary NFC card parser with RSA signature verification and 10 rotating public keys | Snapmaker implements filament authentication to ensure only genuine/authorised filament data is trusted for auto-parameter selection |

## Additions

### Data Structures
- **`FILAMENT_INFO_STRUCT`** — Template dict with 30 fields: `VERSION`, `VENDOR`, `MANUFACTURER`, `MAIN_TYPE`, `SUB_TYPE`, `TRAY`, `ALPHA`, `COLOR_NUMS`, `ARGB_COLOR`, `RGB_1`–`RGB_5`, `DIAMETER`, `WEIGHT`, `LENGTH`, `DRYING_TEMP`, `DRYING_TIME`, `HOTEND_MAX_TEMP`, `HOTEND_MIN_TEMP`, `BED_TYPE`, `BED_TEMP`, `FIRST_LAYER_TEMP`, `OTHER_LAYER_TEMP`, `SKU`, `MF_DATE`, `RSA_KEY_VERSION`, `OFFICIAL`, `CARD_UID`.

### Type Mappings
- `FILAMENT_PROTO_MAIN_TYPE_MAPPING` — Numeric codes for PLA, PETG, ABS, TPU, PVA.
- `FILAMENT_PROTO_SUB_TYPE_MAPPING` — Numeric codes for Basic, Matte, SnapSpeed, Silk, Support, HF, 95A, 95A HF.

### RSA Public Keys
- `FILAMENT_PROTO_RSA_PUBLIC_KEY_0` through `FILAMENT_PROTO_RSA_PUBLIC_KEY_9` — 10 PEM-encoded RSA-2048 public keys (2048-bit).

### Functions
- `get_key_by_value(dict_obj, value)` — Reverse lookup helper.
- `verify_signature_pkcs1(public_key, data, signature)` — Verifies RSA-PKCS#1v15 / SHA-256 signature using `cryptography` library.
- `m1_proto_data_parse(data_buf)` — Main entry point. Accepts a 1024-byte list. Returns `(error_code, info_dict)`. Parses all fields from defined byte offsets and validates the signature over bytes 0–639.

### Error Codes
- `FILAMENT_PROTO_OK = 0`
- `FILAMENT_PROTO_ERR = -1`
- `FILAMENT_PROTO_PARAMETER_ERR = -2`
- `FILAMENT_PROTO_RSA_KEY_VER_ERR = -3`
- `FILAMENT_PROTO_SIGN_CHECK_ERR = -4`

### Card Layout Constants
All byte positions (`M1_PROTO_*_POS`) and lengths (`M1_PROTO_*_LEN`) for every field in the 1 KB M1 card memory are defined as named constants (e.g., `M1_PROTO_VENDOR_POS = 16`, `M1_PROTO_VENDOR_LEN = 16`).

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `cryptography` Python package (`cryptography.hazmat.primitives`), which is not a standard Klipper dependency.
- The 10 hard-coded RSA public keys are Snapmaker IP; rotating keys beyond version 9 would require a fork update.
- Cards with RSA key version > 9 are rejected with `FILAMENT_PROTO_RSA_KEY_VER_ERR`, silently treating them as unofficial filament.
- The digital signature covers only bytes 0–639 of the 1 KB card; the remaining 384 bytes (signature sectors 10–15) are not validated for integrity beyond being extracted as the signature itself.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import copy
+from cryptography.hazmat.primitives import hashes, serialization
+from cryptography.hazmat.primitives.asymmetric import padding
+from cryptography.hazmat.backends import default_backend
+from cryptography.exceptions import InvalidSignature
+
+FILAMENT_INFO_STRUCT = {
+    'VERSION': 0, 'VENDOR': 'NONE', 'MANUFACTURER': 'NONE',
+    'MAIN_TYPE': 'NONE', 'SUB_TYPE': 'NONE', ...
+    'OFFICIAL': False, 'CARD_UID': 0,
+}
+
+FILAMENT_PROTO_RSA_PUBLIC_KEY_0 = b"""-----BEGIN RSA PUBLIC KEY-----
+MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA8oEF7YuKO86...
+-----END RSA PUBLIC KEY-----"""
+# ... keys 1-9 ...
+
+def m1_proto_data_parse(data_buf):
+    # validate length, select RSA key, verify signature
+    # parse all fields from byte offsets
+    # return (FILAMENT_PROTO_OK, info) or error code
+    ...
```
</details>

---

# filament_feed_fac_test.py

## Summary
`filament_feed_fac_test.py` implements `FeedFacTest`, a factory self-test module for the Snapmaker U1 filament feeder board. It drives alternating digital output patterns on five output pins (light channels, tachometer drive pins, and a port pin) and reads back the resulting states on five corresponding input pins to verify electrical continuity. It then runs the feeder motor in both forward and reverse directions at 50% PWM and checks the motor tachometer RPM falls within configured `motor_dest_rpm_min` / `motor_dest_rpm_max` bounds. It also re-uses the `FeedMotor` and `FeedTachometer` helper classes from the conceptually related `filament_feed_fac_test.py` file itself (defined inline).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: factory-floor PCB continuity and motor RPM test for the feeder board | Snapmaker uses automated end-of-line testing; this module enables a single G-code command to validate the feeder hardware before shipment |

## Additions

### Classes
- **`FeedTachometer`** — (Local copy of feeder tachometer helper) Wraps `pulse_counter.FrequencyCounter` to report RPM and cumulative count.
- **`FeedPwmCfg`** — Data class for PWM H-bridge config.
- **`FeedMotor`** — H-bridge driver with direction-reversal protection (2.5 s hard-protect time).
- **`FeedFacTest`** — Main extra class loaded via `load_config_prefix`.

### G-code Commands
- **`FEED_FACTORY_TEST MODULE=<name>`** — Runs the full factory test sequence and responds with pass/fail state, pin input/output bitmasks, and RPM readings for idle, forward, and reverse motor directions.

### Config Options
- `light_ch_1_white`, `light_ch_2_white` — Output pin names for white LEDs (driven high/low alternately).
- `wheel_tach_ch_1_1_pin`, `wheel_tach_ch_2_1_pin` — Output/drive pins for wheel tachometers.
- `port_ch_1_pin` — Output port-detect drive pin.
- `light_ch_1_red`, `light_ch_2_red` — Input pins (readback for white output).
- `wheel_tach_ch_1_2_pin`, `wheel_tach_ch_2_2_pin` — Input pins (readback for tach outputs).
- `port_ch_2_pin` — Input pin (readback for port output).
- `motor_ch_1_pin`, `motor_ch_2_pin` — H-bridge PWM pins.
- `motor_cycle_time` — PWM period (s).
- `motor_max_value` — Maximum PWM duty cycle (0–1).
- `motor_tach_pin` — Motor tachometer input pin.
- `motor_tach_ppr` — Pulses per revolution (default 2).
- `motor_tach_poll_interval` — Tachometer poll interval (default 0.5 ms).
- `motor_dest_rpm_min`, `motor_dest_rpm_max` — RPM pass/fail window.

### Test States
- `TEST_STATE_IDLE`, `TEST_STATE_TESTING`, `TEST_STATE_FAILED`, `TEST_STATE_SUCCESSFUL`

### Test Logic
1. Set even-indexed output pins HIGH, odd LOW; verify input bitmask matches.
2. Swap: even LOW, odd HIGH; verify again.
3. Run motor forward at 0.5 duty; check RPM in bounds.
4. Run motor reverse at 0.5 duty; check RPM in bounds.
5. Stop motor; check RPM == 0.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The test uses `reactor.pause()` inside a G-code command handler to synchronously wait for motor spin-up — blocking behaviour.
- Uses bare `raise` (with no argument) to trigger the failure path — valid Python 2/3 only inside an except block; if any `if` branch triggers `raise` outside an except, it will cause a `RuntimeError`. The test is intended only as a factory tool, not for production use.
- Output pins are configured with `setup_max_duration(0.)` (unlimited duration), so a crash mid-test leaves them in an energised state.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging
+from . import pulse_counter
+
+TEST_STATE_IDLE      = 'idle'
+TEST_STATE_TESTING   = 'testing'
+TEST_STATE_FAILED    = 'failed'
+TEST_STATE_SUCCESSFUL = 'successful'
+
+FEED_MOTOR_DIR_IDLE = 0
+FEED_MOTOR_DIR_A    = 1
+FEED_MOTOR_DIR_B    = 2
+FEED_MOTOR_HARD_PROTECT_TIME = 2.5
+
+class FeedTachometer: ...
+class FeedPwmCfg: ...
+class FeedMotor: ...
+
+class FeedFacTest:
+    def __init__(self, config) -> None:
+        ...
+        gcode.register_mux_command("FEED_FACTORY_TEST", "MODULE",
+                                self.module_name,
+                                self.cmd_FEED_FACTORY_TEST)
+    def cmd_FEED_FACTORY_TEST(self, gcmd):
+        # GPIO continuity test + motor RPM test
+        ...
+
+def load_config_prefix(config):
+    return FeedFacTest(config)
```
</details>

---

# mqtt.py

## Summary
`mqtt.py` implements `MQTTClient`, a Klipper extra that wraps the `paho-mqtt` Python library to provide a persistent MQTT v5 broker connection for other fork modules. It manages subscriptions and publications with per-topic QoS tracking, handles automatic broker reconnection (1–120 s back-off), and dispatches received messages to registered callbacks via `reactor.register_async_callback` to ensure callbacks run on the Klipper reactor thread. The `timelapse`, `defect_detection`, and `jsonrpc` modules all use this as their transport layer. Wildcards (`#`, `+`) are explicitly blocked in both subscribe and publish calls.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: MQTT v5 client with topic subscription management and async callback dispatch | U1 communicates with an on-board camera and other Linux-side services via MQTT; Klipper's built-in IPC (webhooks/Unix socket) is insufficient for these use cases |

## Additions

### Classes
- **`SubscriptionHandle`** — Lightweight container holding a topic string and callback; used as an opaque handle for `unsubscribe()`.
- **`MQTTClient`** — Klipper extra loaded as `[mqtt]`.

### Key Config Options
- `client_id` — MQTT client ID (default: `klipper_<random_5-7_digit_number>`).
- `address` — Broker hostname/IP (default: `localhost`).
- `port` — Broker port (default: 1883).
- `default_qos` — Default QoS level 0–2 (default: 0).

### Public API
- `subscribe_topic(topic, callback, qos=None)` → `SubscriptionHandle` — Subscribe to an exact topic (no wildcards). If a subscription already exists for the topic, the QoS is upgraded to `max(old, new)` and the callback is appended.
- `unsubscribe(hdl: SubscriptionHandle)` — Remove a specific subscription handle; sends an MQTT unsubscribe only if the last handler for that topic is removed.
- `publish_topic(topic, payload, qos=None, retain=False)` — Publish; dicts/lists are JSON-encoded; booleans are lowercased strings.
- `is_connected()` → bool
- `get_status(eventtime)` → `{'connected': bool}`

### Internal Callbacks
- `_on_connect` — Re-subscribes all known topics on reconnect.
- `_on_message` — Dispatches to all registered handlers for a topic via async reactor callbacks.
- `_on_disconnect` — Logs disconnect reason code.

### Lifecycle
- `_handle_shutdown()` / `_handle_request_restart()` — Disable reconnection and disconnect cleanly on Klipper shutdown or restart.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `paho-mqtt` Python package (`paho.mqtt.client`), which is not shipped with stock Klipper.
- The MQTT network thread (`loop_start()`) runs outside the Klipper reactor; callbacks are bounced back to the reactor thread via `register_async_callback`, but this introduces latency and means ordering with other reactor events is not guaranteed.
- `publish_topic` raises an exception if the broker is not connected, which will propagate to the caller as a G-code error.
- Only MQTTv5 is used (`paho_mqtt.MQTTv5`); brokers that only support v3.1.1 (e.g., some older Mosquitto versions) will reject the connection.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, json
+import paho.mqtt.client as paho_mqtt
+import threading, random
+from typing import List, Optional, Any, Callable, Dict, Union, Tuple
+
+class SubscriptionHandle:
+    def __init__(self, topic: str, callback: Callable[[bytes], None]):
+        self.callback = callback
+        self.topic = topic
+
+class MQTTClient:
+    def __init__(self, config):
+        ...
+        self.client = paho_mqtt.Client(client_id=self.client_id,
+                                       protocol=paho_mqtt.MQTTv5)
+        self.client.on_connect    = self._on_connect
+        self.client.on_message    = self._on_message
+        self.client.on_disconnect = self._on_disconnect
+        self.client.loop_start()
+        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
+        self.client.connect(self.address, self.port)
+    def subscribe_topic(self, topic, callback, qos=None) -> SubscriptionHandle: ...
+    def unsubscribe(self, hdl): ...
+    def publish_topic(self, topic, payload=None, qos=None, retain=False): ...
+
+def load_config(config):
+    return MQTTClient(config)
```
</details>

---

# jsonrpc.py

## Summary
`jsonrpc.py` provides a JSON-RPC 2.0 client library used by the `timelapse` and `defect_detection` modules to communicate with on-board camera and vision services over MQTT. It defines an abstract `TransportInterface`, a concrete `MQTTTransport` implementation (backed by the fork's `mqtt.py` extra), and a `JSONRPCClient` that manages pending requests, generates monotonically-increasing IDs via a thread-safe `GlobalIdGenerator`, and supports both fire-and-forget async requests (`send_request`) and blocking synchronous requests (`send_request_with_response`). The synchronous path polls the reactor with 50 ms pauses while waiting for the response topic message.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: JSON-RPC 2.0 client over MQTT transport with async and synchronous request modes | On-board camera services expose a JSON-RPC API over MQTT; this adapter makes calling them from Klipper G-code handlers straightforward |

## Additions

### Classes
- **`GlobalIdGenerator`** — Thread-safe sequential integer ID generator (range 1 to 0x7FFFFFFF, wrapping).
- **`TransportInterface`** (ABC) — Abstract base class with `connect`, `disconnect`, `is_connected`, `send`, and `set_message_handler`.
- **`MQTTTransport`** (`TransportInterface`) — Subscribes to a response topic and publishes to a request topic using the `MQTTClient` extra. Tracks `_is_connected` state separately from the underlying MQTT connection.
- **`JSONRPCClient`** — Core JSON-RPC 2.0 client; not a Klipper extra itself (instantiated by callers).

### Error Codes
- `JSONRPC_ERR_SERVER_ERROR = -32000` (JSON-RPC standard)
- `JSONRPC_ERR_INVALID_REQUEST = -32600`
- `JSONRPC_ERR_METHOD_NOT_FOUND = -32601`
- `JSONRPC_ERR_INVALID_PARAMS = -32602`
- `JSONRPC_ERR_PARSE_ERROR = -32700`
- `JSONRPC_ERR_TRANSPORT_ERROR = -111` (fork-specific)
- `JSONRPC_ERR_TIMEOUT = -112` (fork-specific)
- `JSONRPC_ERR_NOT_CONNECTED = -113` (fork-specific)

### Transport Constant
- `JSONRPC_TRANSPORT_MQTT = "mqtt"` — Only supported transport type.

### Key Methods on `JSONRPCClient`
- `connect()` — Connects the underlying transport (subscribes the response topic).
- `disconnect()` — Clears pending requests and disconnects transport.
- `send_request(method, params={}, callback=None)` — Fire-and-forget; stores the callback in `pending_requests` keyed by request ID. Response dispatched by `_handle_response`.
- `send_request_with_response(method, params={}, timeout=None)` → dict — Blocks the reactor (via `reactor.pause`) until the matching response arrives or times out. Returns the full JSON-RPC response dict including `result` or `error`.

### Limits
- `JSONRPC_PENDING_REQUEST_SIZE = 100` — Maximum number of outstanding async requests; oldest is evicted on overflow.
- Default `request_timeout = 30` s.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- `send_request_with_response` calls `reactor.pause()` in a loop — this is acceptable in a G-code command handler but must not be called from a reactor timer callback or it will deadlock the reactor.
- Only one synchronous request can be in-flight at a time (`sync_request_id` single slot). Concurrent calls serialize via a `while self.sync_request_id is not None` spin-wait.
- Response matching is purely by ID; if the remote service reuses IDs or sends out-of-order responses, the wrong callback may be invoked.
- The module imports `*` from itself (`from .jsonrpc import *`) in callers; all module-level names are therefore potentially exported into the caller's namespace.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import json, logging, copy
+from abc import ABC, abstractmethod
+from typing import Callable, Dict
+import threading
+
+JSONRPC_ERR_SERVER_ERROR    = -32000
+JSONRPC_ERR_TIMEOUT         = -112
+JSONRPC_ERR_NOT_CONNECTED   = -113
+JSONRPC_PENDING_REQUEST_SIZE = 100
+JSONRPC_TRANSPORT_MQTT = "mqtt"
+
+class GlobalIdGenerator: ...
+class TransportInterface(ABC): ...
+class JSONRPCClient:
+    def send_request(self, method, params={}, callback=None): ...
+    def send_request_with_response(self, method, params={}, timeout=None): ...
+    def _handle_message(self, message: str): ...
+    def _handle_response(self, response: Dict): ...
+class MQTTTransport(TransportInterface):
+    def connect(self): ...   # subscribe response_topic
+    def send(self, data): ...  # publish request_topic
```
</details>

---

# machine_state_manager.py

## Summary
`machine_state_manager.py` provides `MachineStateManager`, a Klipper extra that tracks the printer's high-level operational state (`MachineMainState`) and a finer-grained sub-state (`ActionCode`). It enforces a state-transition rule matrix: most non-IDLE states can only be entered from IDLE, while IDLE and ABNORMAL can be reached from any state. Pre- and post-transition hooks can be registered by other modules. A 10-entry history ring-buffer records state changes for diagnostics. On klippy shutdown the state is automatically set to ABNORMAL. G-code commands allow external systems (e.g., a UI) to drive state changes and query current status.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: explicit printer-lifecycle state machine with transition guards, action sub-states, hooks, and history | U1 UI needs to know whether the printer is idle, printing, calibrating, loading filament, etc. to gate user interactions and prevent conflicting operations |

## Additions

### Enumerations
- **`MachineMainState`** (IntEnum) — 14 states: `IDLE`, `PRINTING`, `XYZ_OFFSET_CALIBRATE`, `BED_LEVELING`, `FLOW_CALIBRATION`, `SHAPER_CALIBRATE`, `UPGRADING`, `ABNORMAL`, `SCREWS_TILT_ADJUST`, `AUTO_LOAD`, `AUTO_UNLOAD`, `MANUAL_LOAD`, `PARK_POINT_MANUAL_CALIBRATION`, `HOMING_ORIGIN_CALIBRATION`.
- **`ActionCode`** (IntEnum) — ~40 sub-states covering homing, plate detection, printing phases, calibration sub-steps, and filament operations (e.g. `PRINT_AUTO_FEEDING = 133`, `BED_LEVELING = 256`, `FLOW_CALIBRATE = 320`).

### Classes
- **`MachineStateManagerErr`** — Custom exception for invalid transitions.
- **`MachineStateManager`** — Klipper extra loaded as `[machine_state_manager]`.

### G-code Commands
- **`SET_MAIN_STATE MAIN_STATE=<name|int> [ACTION=<name|int>]`** — Attempt a validated state transition.
- **`SET_ACTION_CODE ACTION=<name|int> [MAIN_STATE=<name|int>]`** — Update action code, optionally asserting the expected current main state.
- **`GET_MACHINE_STATE`** — Report current main state and action code.
- **`GET_STATE_HISTORY [SHOW_ERROR=0|1]`** — Dump last 10 state transitions.
- **`EXIT_TO_IDLE [REQ_FROM_STATE=<name|int>]`** — Transition to IDLE, optionally asserting the requesting state.
- **`SHOW_STATE_RULES`** — Print the transition and exit rule tables.

### Public API
- `change_state(new_state, action=None)` — Thread-safe (uses reactor mutex); validates transition, runs pre-hooks, updates state, runs post-hooks.
- `exit_to_idle(requested_from_state=None)` — Convenience wrapper for transitioning to IDLE.
- `set_action_code(action_code, main_state=None)` — Update action code with optional state guard.
- `register_pre_hook(hook)` / `unregister_pre_hook(hook)` — Register callbacks invoked before a state change; return `False` to veto.
- `register_post_hook(hook)` / `unregister_post_hook(hook)` — Register callbacks invoked after a successful state change.
- `can_transition(target_state, current_state=None)` → bool
- `get_status(eventtime)` → `{'main_state': ..., 'action_code': ...}`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The transition rule table (`DEFAULT_TRANSITION_RULES`) only explicitly restricts a subset of state pairs; `IDLE` and `ABNORMAL` are universally reachable from any state.
- The hook system uses a plain Python list protected by the reactor mutex; if a hook raises an exception the transition is rolled back but the hook is not removed.
- G-code-driven state changes (`SET_MAIN_STATE`) bypass any business-logic guards and directly call `change_state`; a malformed G-code script could put the printer in an inconsistent state.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, time
+from enum import Enum, IntEnum, unique
+
+class MachineStateManagerErr(Exception): ...
+
+@unique
+class MachineMainState(IntEnum):
+    IDLE = 0; PRINTING = 1; XYZ_OFFSET_CALIBRATE = 2
+    BED_LEVELING = 3; FLOW_CALIBRATION = 4; ...
+    HOMING_ORIGIN_CALIBRATION = 13
+
+@unique
+class ActionCode(IntEnum):
+    IDLE = 0; HOMING = 1; DETECT_PLATE = 2
+    PRINT_AUTO_FEEDING = 133; BED_LEVELING = 256; ...
+    HOMING_ORIGIN_CALIBRATING = 832
+
+class MachineStateManager:
+    def __init__(self, config):
+        ...
+        gcode.register_command('SET_ACTION_CODE', ...)
+        gcode.register_command('SET_MAIN_STATE', ...)
+        gcode.register_command('GET_MACHINE_STATE', ...)
+        gcode.register_command('GET_STATE_HISTORY', ...)
+        gcode.register_command('EXIT_TO_IDLE', ...)
+        gcode.register_command('SHOW_STATE_RULES', ...)
+
+def load_config(config):
+    return MachineStateManager(config)
```
</details>

---

# print_task_config.py

## Summary
`print_task_config.py` implements `PrintTaskConfig`, the central per-print-job configuration store for the U1. It persists settings to `print_task.json` and holds filament metadata (vendor, type, sub-type, colour, SKU, official flag), extruder mapping tables (logical-to-physical for up to 32 logical / 4 physical extruders), and feature flags (timelapse, auto bed leveling, flow calibration, shaper calibration, auto-replenish, tangle detection). It integrates with `filament_detect` to auto-populate filament info from RFID reads, with `filament_parameters` to look up print temperatures, and with `filament_feed` to manage automatic filament replenishment during multi-material prints. A reprint-info sub-dict allows the previous job's settings to be restored for reprinting.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: per-job configuration store integrating filament RFID data, multi-extruder mapping, and feature-flag management | U1's tool-changer, RFID filament ID, and optional calibration steps require a structured per-job config that Klipper's standard config system does not provide |

## Additions

### Classes
- **`PrintTaskConfig`** — Klipper extra loaded as `[print_task_config]`.

### G-code Commands
- **`SET_PRINT_EXTRUDER_MAP`** — Set the logical-to-physical extruder mapping table.
- **`GET_PRINT_EXTRUDER_MAP`** — Query the current mapping.
- **`SET_PRINT_FILAMENT_CONFIG`** — Set filament metadata for one or more extruder slots (vendor, type, sub-type, colour, etc.).
- **`GET_PRINT_TASK_CONFIG`** — Dump the full config dict.
- **`SAVE_CURRENT_PRINT_TASK_CONFIG`** — Force a save to `print_task.json`.
- **`RESET_PRINT_TASK_CONFIG`** — Reset all fields to defaults.
- **`LOAD_PRINT_TASK_CONFIG`** — Reload from `print_task.json`.
- **`SET_TIME_LAPSE_CAMERA`** — Enable/disable timelapse flag.
- **`SET_PRINT_AUTO_BED_LEVELING`** — Enable/disable auto bed leveling for this job.
- **`SET_PRINT_PREFERENCES`** — Set multiple preference flags (auto-replenish, tangle detect, sensitivity) in one call.
- **`SET_PRINT_USED_EXTRUDERS`** — Mark which extruders are used in this print job.
- **`SET_REPRINT_INFO`** — Save reprint-info snapshot.
- **`INNER_CHECK_AND_RELOAD_FILAMENT_INFO`** — Internal command to check and reload filament metadata from RFID cache.
- **`INNER_AUTO_REPLENISH_FILAMENT`** — Internal command to execute automatic filament replenishment logic.

### Webhook Endpoint
- `print_task_config/set_print_preferences` — REST endpoint equivalent of `SET_PRINT_PREFERENCES`.

### Config Options (in `print_task.json`)
- `filament_vendor`, `filament_type`, `filament_sub_type` — Per-extruder arrays (4 entries).
- `filament_color` (uint32 ARGB), `filament_color_rgba` (hex string) — Per-extruder colour arrays.
- `filament_official`, `filament_sku`, `filament_edit`, `filament_exist`, `filament_soft` — Per-extruder bool/int arrays.
- `extruder_map_table` — 32-entry logical-to-physical mapping array.
- `extruders_used`, `extruders_replenished` — Per-extruder bool/index arrays.
- `time_lapse_camera`, `auto_bed_leveling`, `flow_calibrate`, `shaper_calibrate` — Boolean feature flags.
- `auto_replenish_filament` — Bool.
- `filament_entangle_detect` — Bool.
- `filament_entangle_sen` — `'low'`|`'medium'`|`'high'`.
- `reprint_info` — Sub-dict mirroring key fields for reprint restoration.

### Events Emitted
- `print_task_config:set_entangle_detect` — Fired when entangle-detect setting changes; consumed by `filament_entangle_detect`.

### Constants
- `LOGICAL_EXTRUDER_NUM = 32`, `PHYSICAL_EXTRUDER_NUM = 4`
- `ENTANGLE_SENSITIVITY_LOW/MEDIUM/HIGH = 'low'/'medium'/'high'`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The RFID callback `_rfid_filament_info_update_cb` silently ignores unofficial RFID data if the slot already has a non-NONE vendor set — may prevent legitimate updates from non-Snapmaker filament.
- The auto-replenishment logic (`INNER_AUTO_REPLENISH_FILAMENT`) calls `reactor.pause()` inside a G-code command handler for potentially long operations.
- The 32-entry logical extruder map is a U1-specific concept; upstream Klipper extruder objects map 1:1 without an indirection table.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# print task config info
+import logging, os, copy, string
+from . import filament_feed
+
+LOGICAL_EXTRUDER_NUM = 32
+PHYSICAL_EXTRUDER_NUM = 4
+PRINT_TASK_CONFIG_FILE = "print_task.json"
+
+DEFAULT_PRINT_TASK_CONFIG = {
+    'filament_vendor': ['NONE'] * 4,
+    'filament_type': ['NONE'] * 4,
+    'extruder_map_table': [0,1,2,3] + [0]*28,
+    'time_lapse_camera': False,
+    'filament_entangle_detect': False,
+    ...
+}
+
+class PrintTaskConfig:
+    def __init__(self, config):
+        ...
+        gcode.register_command("SET_PRINT_EXTRUDER_MAP", ...)
+        gcode.register_command("SET_PRINT_FILAMENT_CONFIG", ...)
+        gcode.register_command("SET_PRINT_PREFERENCES", ...)
+        gcode.register_command("INNER_AUTO_REPLENISH_FILAMENT", ...)
+        webhooks.register_endpoint(
+            "print_task_config/set_print_preferences", ...)
+
+def load_config(config):
+    return PrintTaskConfig(config)
```
</details>

---

# timelapse.py

## Summary
`timelapse.py` implements `TimeLapse`, a Klipper extra that controls an on-board camera to capture timelapse frames during printing. It communicates with a camera service via JSON-RPC over MQTT (`mqtt.py` + `jsonrpc.py`), calling the `camera.start_timelapse`, `camera.stop_timelapse`, and `camera.take_a_photo` methods. Timelapse activation is gated by the `print_task_config` flag `time_lapse_camera`. A minimum 1-second interval between frame requests prevents flooding. On `TIMELAPSE_START` the module also turns on the cavity LED (`SET_LED LED=cavity_led WHITE=1`). Frame capture requests are fire-and-forget (async JSON-RPC), while start/stop calls are synchronous with a 5-second timeout.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: timelapse control via MQTT JSON-RPC to on-board camera service, gated by print_task_config | U1 has an optional cavity camera; this module provides a Klipper-native way to trigger it from G-code macros |

## Additions

### Classes
- **`TimeLapse`** — Klipper extra loaded as `[timelapse]`.

### G-code Commands
- **`TIMELAPSE_START [TYPE=new|continue] [FRAME_RATE=<int>]`** — Start a timelapse session. Sends `camera.start_timelapse` JSON-RPC call synchronously. Raises a structured error (ID 524) on failure, which causes the print to pause.
- **`TIMELAPSE_STOP`** — Stop timelapse; sends `camera.stop_timelapse` synchronously.
- **`TIMELAPSE_TAKE_FRAME [DEBUG=0|1]`** — Trigger a single photo capture (async). In debug mode (`DEBUG=1`) saves the image to `/userdata/gcodes/pictures/pic_<timestamp>.jpg`.
- **`TIMELAPSE_IGNORE IGNORE=<0|1>`** — Suppress all frame captures for the current print session (useful during non-print phases).

### Config Options
- `frame_rate` (int, default 24) — Default frames-per-second requested when starting timelapse.

### MQTT Topics
- Request: `camera/request`
- Response: `camera/response`

### Event Handlers
- `print_stats:start` — Clears the `timeslapse_ignore` flag.
- `print_stats:stop` — Clears the `timeslapse_ignore` flag.
- `klippy:ready` — Looks up `mqtt` and `print_task_config` objects; creates the `JSONRPCClient`.

### Key Logic
- `REQUEST_INTERVAL_MIN = 1` s — Minimum time between consecutive frame-capture requests.
- `REQUEST_TIMEOUT = 5` s — Synchronous JSON-RPC timeout for start/stop.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `mqtt` and `print_task_config` extras to be present; if either is absent, G-code commands raise errors.
- `TIMELAPSE_START` failure path uses a structured error dict (`id=524`) inside `gcmd.error()`; this is a fork-specific extension of Klipper's `GCodeException`.
- `send_request_with_response` blocks the G-code thread for up to 5 seconds; during that time no other G-code can execute.
- Debug image path is hardcoded to `/userdata/gcodes/pictures` — Snapmaker-specific filesystem layout.
- The `TIMELAPSE_TAKE_FRAME` command has a `filepath` hardcoded to `/tmp/tmp.jpg` for non-debug mode — this is a temporary location that will be overwritten by every frame capture.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# timelapse manager for klippy
+# Copyright (C) 2025-2030  Scott Huang <shili.huang@snapmaker.com>
+import logging, time, os
+from .jsonrpc import *
+
+REQUEST_TOPIC  = "camera/request"
+RESPONSE_TOPIC = "camera/response"
+REQUEST_INTERVAL_MIN = 1
+REQUEST_TIMEOUT = 5
+
+class TimeLapse:
+    def __init__(self, config):
+        ...
+        self.gcode.register_command('TIMELAPSE_START', ...)
+        self.gcode.register_command('TIMELAPSE_STOP', ...)
+        self.gcode.register_command('TIMELAPSE_TAKE_FRAME', ...)
+        self.gcode.register_command('TIMELAPSE_IGNORE', ...)
+
+    def cmd_TIMELAPSE_START(self, gcmd):
+        # check print_task_config['time_lapse_camera']
+        # gcode.run_script_from_command("SET_LED LED=cavity_led WHITE=1")
+        # mqtt_jsonrpc.send_request_with_response("camera.start_timelapse", ...)
+        ...
+
+def load_config(config):
+    return TimeLapse(config)
```
</details>

---

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

---

# probe_inductance_coil.py

## Summary
`probe_inductance_coil.py` is the fork's replacement for (and extension of) the upstream `probe.py` module. It re-implements `ProbeCommandHelper`, `ProbeEndstopWrapper`, and `ProbePointsHelper`, adapting them to work with the `InductanceCoil` frequency sensor instead of a simple endstop. Beyond standard probe commands (`PROBE`, `PROBE_ACCURACY`, `PROBE_CALIBRATE`, `Z_OFFSET_APPLY_PROBE`), it adds commands for XYZ offset calibration between multiple extruders (`PROBE_XYZ_OFFSET_CALIBRATE`), bed-contact detection (`PROBE_BED_CONTACT`), and inductance coil trigger frequency override (`SET_PROBE_TRIG_FREQ`). It also introduces a configurable circle-mode probing pattern (in addition to the standard rectangular grid), Decimal-precision circle-centre calculation, and per-probe XYZ offset persistence via a JSON config file.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Upstream `probe.py` defines `ProbeCommandHelper`, `ProbeEndstopWrapper`, `ProbePointsHelper` | Fork replaces these with extended versions in `probe_inductance_coil.py` that integrate with `InductanceCoil` frequency-based triggering, add XYZ offset calibration, and support circle/rectangle probe patterns | U1 uses an LC coil probe instead of a switch; multi-extruder offset calibration and alternative probing patterns are required for the U1's tool-changer architecture |

## Additions

### New Classes (Fork-Exclusive)
- **`ProbeCommandHelper`** (extended vs upstream) — Adds commands:
  - `PROBE_BED_CONTACT` — Probe until bed contact without recording position.
  - `SET_PROBE_TRIG_FREQ` — Override inductance coil trigger frequency for the next probe.
  - `INDUCTANCE_COIL_PROBE_QUERY` — Query current sensor frequency.
  - `PROBE_XYZ_OFFSET_CALIBRATE` (`PROBE_XYZ_OFFSET_CALIBRATE_ADVANCED`) — Automated multi-extruder XYZ offset calibration sequence.
- **`ExtruderOffsetCalAbort`** — Exception used to abort offset calibration.

### New Functions
- `find_circle_center(A, B, C)` — Uses Decimal precision arithmetic to find the circumcentre of three XY points (used in circle-mode bed levelling).
- `calc_probe_z_average(positions, method, axis)` — Mean/median averaging for probe results.
- `run_single_probe(probe_obj, gcmd)` — Helper to execute a single probe move and return the position.

### New Config Options (on probe section)
- `probe_mode` (0=rectangle, 1=circle) — Probing pattern shape.
- `z_offset_config_file` — Path to JSON file persisting per-extruder XYZ offsets.
- Various XYZ-offset calibration geometry parameters.

### Constants
- `MAX_OFFSET_DELTA_X/Y/Z = 0.8/0.8/0.5` mm — Maximum allowed per-step offset correction during XYZ calibration.
- `RECTANGLE_PROBE_MODE = 0`, `CIRCLE_PROBE_MODE = 1`

### Probe Endpoint
- `PROBE_XYZ_OFFSET_CALIBRATE` — Drives the toolhead through a multi-step sequence: home, move to calibration position, probe multiple points on a calibration target, compute offsets, optionally save to JSON.

## Removals / Overrides
- The fork's `probe_inductance_coil.py` effectively replaces the upstream `probe.py` extra. The standard `[probe]` config section maps to `ProbeEndstopWrapper` defined here, not upstream's version.
- Circle-mode probing and XYZ multi-extruder offset calibration do not exist in any form in upstream Klipper.

## Risks / Compatibility Notes
- Any config or macro that directly uses upstream `probe.py`-specific internals (e.g., imports from `extras.probe`) may break.
- The XYZ offset calibration workflow (`PROBE_XYZ_OFFSET_CALIBRATE`) is deeply coupled to the U1's tool-changer hardware (extruder docking, calibration target geometry).
- Circle-mode probing (`find_circle_center`) is only valid for exactly 3 points; passing fewer or more will raise an error.
- Relies on `queuefile.sync_write_file` for atomic JSON saves — a fork-specific extension.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Z-Probe support
+# Copyright (C) 2017-2024  Kevin O'Connor <kevin@koconnor.net>
+# (Fork heavily modified by Snapmaker)
+import logging, copy, time, os
+import pins, queuefile
+from . import manual_probe, inductance_coil
+from decimal import Decimal, getcontext
+
+RECTANGLE_PROBE_MODE = 0
+CIRCLE_PROBE_MODE    = 1
+MAX_OFFSET_DELTA_X   = 0.8
+MAX_OFFSET_DELTA_Y   = 0.8
+MAX_OFFSET_DELTA_Z   = 0.5
+
+def find_circle_center(A, B, C): ...   # Decimal-precision circumcentre
+def calc_probe_z_average(positions, method='average', axis=2): ...
+
+class ProbeCommandHelper:
+    def __init__(self, config, probe, query_endstop=None):
+        ...
+        gcode.register_command('PROBE_BED_CONTACT', ...)
+        gcode.register_command('SET_PROBE_TRIG_FREQ', ...)
+        gcode.register_command('INDUCTANCE_COIL_PROBE_QUERY', ...)
+        gcode.register_command('PROBE_XYZ_OFFSET_CALIBRATE', ...)
```
</details>

---

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

---

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

---

# fm175xx_reader.py

## Summary
`fm175xx_reader.py` implements `FM175XXReader`, a Klipper extra that drives one or more FM175XX SPI NFC/RFID reader ICs (connected via `/dev/spidev*`) to read MIFARE M1 1K NFC tags embedded in Snapmaker filament spools. The module runs a dedicated background thread that continuously scans up to 4 channels, dispatching card-info read or clear requests from a queue. For each successful read it verifies an HMAC-SHA256 message authentication code derived from the card UID to guard against replay attacks before passing the raw 1 KB card data to registered callbacks. It also provides a self-test mode for production validation.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: multi-channel SPI NFC reader driver with HMAC authentication, async request queuing, and callbacks for the filament detection system | U1 hardware has FM175XX NFC chips in the feeder unit to read per-spool RFID tags; no upstream equivalent exists |

## Additions

### Classes
- **`FM175XXReader`** — Klipper extra loaded as `[fm175xx_reader]`.

### Key Config Options
- `spi_bus_ch*` — SPI bus device path for each channel (e.g. `/dev/spidev0.0`).
- `spi_cs_ch*_pin` — Chip-select GPIO pin for each channel.
- `hmac_key` — HMAC-SHA256 key used to authenticate card UID.
- `channel_nums` (int, default 4) — Number of reader channels.

### Public API
- `register_cb_2_card_info_deal(cb)` — Register a callback `cb(channel, operation, result, card_type, card_data)` invoked after each read or clear.
- `request_read_card_info(channel)` — Enqueue a read request for `channel`.
- `request_clear_card_info(channel)` — Enqueue a clear (info-reset) request for `channel`.
- `self_test(channel, times)` — Run `times` consecutive read attempts on `channel`.
- `self_test_result()` → `(finished, test_times, success_times)` — Poll self-test progress.

### Constants
- `FM175XX_CHANNEL_NUMS = 4`
- `FM175XX_OK = 0`, `FM175XX_ERR = -1`, etc.
- `FM175XX_MIFARE_CARD_TYPE_M1` — Card type identifier for MIFARE 1K.
- `FM175XX_CARD_INFO_READ` / `FM175XX_CARD_INFO_CLEAR` — Operation codes passed to callbacks.

### Background Thread
A dedicated Python thread (started in `__init__`) processes the request queue by calling `spidev` directly to communicate with the FM175XX chip, implementing the MIFARE 1K read protocol (REQA, anticollision, select, authentication, block reads).

### HMAC Authentication
After reading the card UID, the module computes `HMAC-SHA256(hmac_key, card_uid)` and checks it against a stored authenticator on the card before accepting the data — preventing cloning or replay attacks.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `spidev` Python package and appropriate kernel SPI device nodes (`/dev/spidev*`) — hardware-specific.
- The background thread uses `threading` directly, which runs outside the Klipper reactor; all callbacks are dispatched back to the reactor via `reactor.register_async_callback`.
- If a channel's SPI device is absent or fails to open, the module may log errors but continues operating the remaining channels.
- HMAC key is stored in Klipper config (plaintext); this provides authentication but not confidentiality.
- The self-test mode (`self_test`) spins in the background thread; polling via `self_test_result()` from a G-code handler with `reactor.pause()` can block the print thread.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, time, threading, copy
+import spidev
+import hmac, hashlib
+
+FM175XX_CHANNEL_NUMS = 4
+FM175XX_OK    = 0
+FM175XX_ERR   = -1
+FM175XX_CARD_INFO_READ  = 0
+FM175XX_CARD_INFO_CLEAR = 1
+FM175XX_MIFARE_CARD_TYPE_M1 = 1
+
+class FM175XXReader:
+    def __init__(self, config):
+        # open spidev devices for each channel
+        # start background reader thread
+        ...
+    def register_cb_2_card_info_deal(self, cb): ...
+    def request_read_card_info(self, channel): ...
+    def request_clear_card_info(self, channel): ...
+    def self_test(self, channel, times): ...
+    def self_test_result(self): ...
+
+def load_config(config):
+    return FM175XXReader(config)
```
</details>

---

# homing_precise_corexy.py

## Summary
`homing_precise_corexy.py` implements `HomingPreciseCorexy`, a specialised post-homing refinement for CoreXY kinematics on the U1. After a standard G28 homes both XY axes against their endstops, this module performs a diagonal probing move (using the TMC phase position) to precisely determine the stepper phase offset. The phase data is used to sub-step-correct the homed position so that the machine homes to a reproducible electrical phase boundary rather than the less repeatable mechanical endstop. Optionally, a saved calibration origin (`homing_calibrated_origin.json`) can be loaded to further correct the coordinate system. The module also validates the result across multiple probe attempts.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: TMC phase-based post-homing position refinement for CoreXY, with optional calibrated-origin correction and result validation | U1 requires sub-step homing repeatability for multi-extruder tool-change accuracy; standard endstop homing has ±half-step positional jitter |

## Additions

### Classes
- **`HomingPreciseCorexy`** — Klipper extra loaded as `[homing_precise_corexy]`.

### G-code Commands
- **`HOMING_PRECISE_COREXY`** — Run the standard precise homing procedure (uses saved calibrated origin if available).
- **`HOMING_PRECISE_COREXY_ADVANCED`** — Extended version with additional parameters for debugging.
- **`ENTER_HOMING_ORIGIN_CALIBRATION`** — Enter calibration mode to measure and save a new origin.
- **`EXIT_HOMING_ORIGIN_CALIBRATION`** — Exit calibration mode.

### Key Config Options
- `xy_back_offset` (float, default 5 mm) — Back-off distance from endstop before diagonal probing.
- `diagonal_probe_before_delay` (float, s) — Dwell before each diagonal probe.
- `diagonal_probe_samples` (int, ≥2) — Number of probe samples for averaging.
- `diagonal_probe_tolerance` (float) — Max deviation between samples.
- `diagonal_probe_accel` (float) — Probe acceleration.
- `diagonal_probe_speed` (float) — Probe speed.
- `diagonal_probe_retract_speed` (float) — Retract speed.
- `diagonal_probe_tolerance_retries` (int) — Retry count on tolerance failure.
- `diagonal_move_rail` (int, 0=A-motor, 1=B-motor, default 1) — Which CoreXY motor moves during diagonal probe.
- `use_calibration_origin` (bool, default False) — Apply saved origin correction.
- `enable_home_validation` (bool, default False) — Validate result with extra probes.
- `use_float_calc` (bool, default False) — Use floating-point distance calculation instead of integer-phase.
- `validation_retries` (int, default 3)

### Key Methods
- `diagonal_probe(endstops, movepos)` — Executes a `HomingMove` diagonally and returns endstop trigger position + MCU step counts.
- `cal_diagonal_dist(m_steps)` — Computes calibrated A/B motor distances from raw step counts (integer phase method).
- `cal_diagonal_dist_float(m_steps)` — Floating-point alternative.
- `phase_backoff_steps(corexy_rails)` → `(x_steps, y_steps)` — Computes phase-aligned backoff distances.
- `translate_to_ab_grid(c_dist, origin)` — Converts fractional phase distances to integer grid positions.
- `load_calibrated_origin()` — Reads `homing_calibrated_origin.json` from persistent config dir.

### Calibration Data File
`homing_calibrated_origin.json` — Contains version, A/B phase origin values; version must be ≥ `MIN_SUPPORTED_CALIBRATION_VERSION = 2`.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires TMC stepper drivers (tmc2130/2208/2209/2240/2660/5160) for both stepper_x and stepper_y; will raise an error if these are absent.
- The module requires CoreXY kinematics and raises a config error for other kinematics types.
- Only `diagonal_move_rail = 1` (B-motor) is fully tested; the comment in the code notes that `diagonal_move_rail = 0` is "not yet adapted".
- Structured error codes (e.g. `0002-0528-0000-0010`) are Snapmaker-specific and will not be parsed by stock Klipper error handlers.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import math, logging, queuefile, os, json, copy
+import stepper
+from . import homing
+
+HOMING_CALIBRATED_ORIGIN_FILE = "homing_calibrated_origin.json"
+CALIBRATION_DATA_VERSION = 2
+
+class HomingPreciseCorexy:
+    def __init__(self, config):
+        if config.getsection('printer').get('kinematics') != 'corexy':
+            raise config.error("homing_precise_corexy: kinematics must be corexy!!!")
+        ...
+        self.gcode.register_command('HOMING_PRECISE_COREXY', ...)
+        self.gcode.register_command('HOMING_PRECISE_COREXY_ADVANCED', ...)
+        self.gcode.register_command("ENTER_HOMING_ORIGIN_CALIBRATION", ...)
+        self.gcode.register_command("EXIT_HOMING_ORIGIN_CALIBRATION", ...)
+
+    def diagonal_probe(self, endstops, movepos, ...): ...
+    def phase_backoff_steps(self, corexy_rails): ...
+    def load_calibrated_origin(self): ...
+
+def load_config(config):
+    return HomingPreciseCorexy(config)
```
</details>

---

# homing_xyz_override.py

## Summary
`homing_xyz_override.py` implements `HomingXYZOverride`, which completely replaces the G28 homing command with a custom sequence tailored to the U1's multi-extruder tool-changer. Before probing Z it verifies the active extruder is correctly docked or active (calling `get_extruder_activate_status()`), handles unhomed axes by performing a Z-hop using a homing endstop move (for positive-dir Z) or a set-position lift, then moves to a configured XY position, and finally executes a configurable G-code template plus a multi-sample Z probe with its own speed, tolerance, and retract parameters. The module also raises structured Snapmaker error codes (`0002-0528-*`) for common failure modes.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Upstream has `safe_z_home` and `homing_override` for custom G28 sequences | Fork adds `homing_xyz_override` with built-in extruder-status validation, structured error codes, and a two-phase Z probe (fast first-touch + accurate second probe) | U1 tool-changer requires extruder dock-state verification before Z homing; the upstream modules lack this integration |

## Additions

### Classes
- **`HomingXYZOverride`** — Klipper extra loaded as `[homing_xyz_override]`. Intercepts and replaces `G28`.

### G-code Commands
- **`G28`** (override) — The full custom homing sequence: optional Z-hop, XY homing, extruder status check, move to probe position, Z probe. Falls back to previous G28 implementation for axes not handled by this module.

### Key Config Options
- `home_xy_position` — XY position to move to before Z probing (required).
- `z_hop` — Z height to lift before XY movement if Z is already homed.
- `z_hop_speed` — Speed for Z-hop lift.
- `z_hop_homing_accel` — Acceleration override during Z-hop homing move.
- `z_safe` — Minimum Z height when Z is already homed.
- `z_safe_speed` — Speed for Z-safe lift.
- `speed` — XY travel speed to probe position.
- `set_position_z` — Z coordinate assumed before Z-axis is homed (for `set_position`).
- `safe_move_y_pos` — Y limit below which XY moves are safe.
- `z_first_probe_speed` — Speed for the initial fast Z touch.
- `z_first_probe_tolerance` — Tolerance for first-touch samples.
- `z_first_probe_sample_count` — Number of samples for first touch.
- `z_first_probe_retract_dist` — Retract distance between first-touch samples.
- `z_offset` — Fixed Z offset applied after probing.
- `z_probe_speed`, `z_probe_fast_speed`, `z_probe_accel`, `z_probe_z_accel`, `z_probe_tolerance`, `z_probe_lift_speed`, `z_probe_samples`, `z_probe_trigger_freq`, `z_probe_retract_dist`
- `gcode` — G-code template executed as part of the homing sequence (loaded via `gcode_macro`).
- `z_hop_homing_begin_gcode`, `z_hop_homing_end_gcode` — Templates executed around the Z-hop homing move.

### Events Consumed
- `stepper_enable:motor_off` — Clears `z_raised` and `homing_stepper_z_info` when motors are disabled.

### Conflict Check
- Raises a config error if `[homing_override]` or `[safe_z_home]` sections are also present.

## Removals / Overrides
- **Replaces `G28`** — The previous `G28` handler is saved as `prev_G28` and can be called for axes not handled by this module.
- Cannot coexist with `homing_override` or `safe_z_home`.

## Risks / Compatibility Notes
- The extruder status validation (`get_extruder_activate_status`, `check_allow_retry_switch_extruder`, `analyze_switch_extruder_error`) are all fork-specific extruder methods; stock Klipper extruder objects will fail with `AttributeError`.
- Structured error strings (e.g. `'{"coded": "0002-0528-0000-0001", ...}'`) are passed to `gcmd.error()` and `printer.command_error()` — stock Klipper will treat these as plain error strings.
- The `_z_probe_pre_process` method modifies `gcmd.get_command_parameters()` in-place to pass probe parameters, which mutates the G-code command object.
- `grab_hall_sensor_type` attribute check on extruder adds another fork-specific dependency.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Run user defined actions in place of a normal G28 homing command
+import math, logging, copy
+import stepper
+from . import homing
+
+class HomingXYZOverride:
+    def __init__(self, config):
+        ...
+        self.prev_G28 = self.gcode.register_command("G28", None)
+        self.gcode.register_command("G28", self.cmd_G28)
+        if config.has_section("homing_override") or config.has_section("safe_z_home"):
+            raise config.error("(homing_override or safe_z_home) and "
+                               "homing_xyz_override cannot be used simultaneously")
+
+    def cmd_G28(self, gcmd):
+        # 1. Z-hop if needed
+        # 2. Check extruder park status
+        # 3. Move to home_xy_position
+        # 4. Execute gcode template
+        # 5. Two-phase Z probe
+        ...
+
+def load_config(config):
+    return HomingXYZOverride(config)
```
</details>

---

# auto_screws_tilt_adjust.py

## Summary
`auto_screws_tilt_adjust.py` implements `AutoScrewsTiltAdjust`, an automated bed-levelling screw adjustment wizard for the Snapmaker U1. Unlike the upstream `screws_tilt_adjust` which performs a single probe pass and reports turn amounts, this module drives a multi-round interactive loop: it probes all four screw positions, computes Z differences, pauses to let the user make manual adjustments, re-probes to verify convergence, and repeats until all four corners are within the `adjust_tolerance` threshold or the `max_adjust_times` limit is reached. It uses the fork's `probe_inductance_coil.ProbePointsHelper` and supports a configurable `screw_order`. A rich step-state machine (`AutoScrewsTiltAdjustStep`) tracks progress and is exposed via webhooks for UI integration.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `screws_tilt_adjust` in upstream probes once and reports mm/turn amounts; no interactive loop | Fork drives an iterative probe-adjust-verify loop with state machine, webhooks, and configurable screw order | U1 UI guides the user through interactive screw adjustment; the upstream one-shot approach is insufficient for a guided workflow |

## Additions

### Classes
- **`AutoScrewsTiltAdjustError`** / `AutoScrewsTiltAdjustAbort` / `AutoScrewsTiltAdjustPass` / `AutoScrewsTiltAdjustLimit`  — Custom exceptions for FSM flow control.
- **`AutoScrewsTiltAdjustStep`** — Namespace of state-name string constants (e.g. `IDLE`, `PROBING_BED`, `WAIT_MANUAL_ADJUST_SCREWS`, `SCREWS_TILT_ADJUST_OK`).
- **`AutoScrewsTiltAdjust`** — Klipper extra loaded as `[auto_screws_tilt_adjust]`.

### G-code Commands
- **`AUTO_SCREWS_TILT_ADJUST`** — Run full automatic iterative adjustment.
- **`AUTO_SCREWS_TILT_ADJUST_ENTRY`** — Enter the adjustment workflow (set state to start).
- **`AUTO_SCREWS_TILT_ADJUST_HOMING`** — Perform homing step.
- **`AUTO_SCREWS_TILT_ADJUST_DETECT_PLATE`** — Detect the build plate.
- **`AUTO_SCREWS_TILT_ADJUST_RESET_TO_INITIAL`** — Move to initial position.
- **`AUTO_SCREWS_TILT_ADJUST_PROBE_REFERENCE_POINTS`** — Probe all four reference screw positions.
- **`AUTO_SCREWS_TILT_ADJUST_MANUAL_TUNING`** — Wait for user to manually turn screws, then re-probe.
- **`AUTO_SCREWS_TILT_ADJUST_EXIT`** — Exit the workflow.

### Webhook Endpoints
- `auto_screws_tilt_adjust/abort_screws_adjust` — Abort from UI.
- `auto_screws_tilt_adjust/next_point_adjust` — Signal that user finished adjusting the current screw.

### Config Options
- `screw1`–`screw4` (required) — XY coordinates of the four screws.
- `screw1_name`–`screw4_name` — Human-readable screw labels.
- `screw_order` (list of 4 ints, default [1,2,3,4]) — Order in which screws are adjusted.
- `screw_adjust_threshold` (float, default 0.1 mm) — Minimum Z difference that triggers an adjustment round.
- `adjust_tolerance` (float, default 0.05 mm) — Convergence threshold.
- `probe_interval` (float, default 10 mm) — Distance between probe and screw position.
- `adjust_probe_samples` (int, default 2) — Samples per probe during adjustment.
- `max_adjust_times` (int, default 30) — Maximum adjustment iterations.
- `max_verify_attempts` (int, default 10) — Maximum verification probes.
- `samples` (int, default 3) — Samples for reference probing.
- `sample_retract_dist` (float, default 0.3 mm) — Retract between samples.

### Status
- `get_status(eventtime)` → `{'probe_step', 'screw_order', 'probe_after_delay', 'min_z', 'max_z', 'target_z', 'current_point', 'base_points', 'need_adjusted_z'}`

## Removals / Overrides
- N/A (new file; conceptually related to but does not override upstream `screws_tilt_adjust`)

## Risks / Compatibility Notes
- The probe finalize callback (`probe_finalize`) and the interactive loop use `reactor.pause()` inside G-code handlers, blocking the print thread during multi-minute adjustment sessions.
- The abort-via-webhook path sets `abort_flag` asynchronously, which is read in the G-code thread without a lock — potential race condition.
- `screw_order` validation requires exactly the values 1–4 once each; mis-configuration raises a config error at load time, not at runtime.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Helper script to automatically adjust bed screws tilt using Z probe
+import math, logging
+from . import probe_inductance_coil
+
+class AutoScrewsTiltAdjustStep:
+    IDLE = "adjust_idle"
+    PROBING_BED = "adjust_probing"
+    WAIT_MANUAL_ADJUST_SCREWS = "adjust_wait_manual"
+    SCREWS_TILT_ADJUST_OK = "adjust_complete"
+    ...
+
+class AutoScrewsTiltAdjust:
+    def __init__(self, config):
+        # Read exactly 4 screw positions
+        # Configure ProbePointsHelper with circle/rect probe mode
+        gcode.register_command("AUTO_SCREWS_TILT_ADJUST", ...)
+        gcode.register_command("AUTO_SCREWS_TILT_ADJUST_MANUAL_TUNING", ...)
+        webhooks.register_endpoint(
+            "auto_screws_tilt_adjust/abort_screws_adjust", ...)
+        webhooks.register_endpoint(
+            "auto_screws_tilt_adjust/next_point_adjust", ...)
+
+def load_config(config):
+    return AutoScrewsTiltAdjust(config)
```
</details>

---

# extruder_calibration.py

## Summary
`extruder_calibration.py` implements `ExtruderParkCalibration`, which calibrates the XY park (docking) position of each extruder on the U1's tool-changer carriage. It probes the mechanical slot/aperture that each extruder docks into using the fork's probe framework (`probe_inductance_coil.run_single_probe`), measures the contact position from two sides, and computes the centre point. For `probe_mode=1` (two-sided), it drives the probe in one direction, records first contact, reverses and records second contact, then averages for the true centre. Results are validated against optional `theoretical_position` and `tolerance` bounds. On success, results are written to a calibration log and can be persisted to the extruder backup config.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automated tool-changer dock-slot probing to calibrate extruder XY park positions | U1 is a tool-changer printer; each extruder must be precisely calibrated to its dock slot; upstream Klipper has no tool-changer docking calibration |

## Additions

### Classes
- **`ExtruderParkCalibrationStep`** — State constants: `PROBING_IDLE`, `PROBING_START`, `PROBING_COMPLETE`, `PROBING_ERROR`.
- **`ExtruderParkCalibration`** — Klipper extra loaded as `[extruder_calibration]`.

### G-code Commands
- **`CALIBRATE_EXTRUDER_PARK_POSITION [ENABLE_THEORETICAL_CHECK=1] [extruder_START_X=<f>] [extruder_START_Y=<f>] ...`** — Run the full calibration sequence for all configured extruders. Supports per-extruder start position overrides via G-code parameters.
- **`PROBE_SINGLE_POINT`** — Single probing move for debugging/testing.

### Key Config Options (per extruder section)
- `extruder_start_position` — XY start position for this extruder's probe (required for each extruder).
- `extruder_probe_aperture` — Width of the dock slot (float, default 5.3 mm).
- `extruder_probe_direction` — Initial probe direction (0 or 1).
- `extruder_reverse_distance` — Distance to reverse between first and second contact.
- `extruder_probe_dist` — Total probe travel distance.
- `extruder_result_offset` — Fixed offset applied to the computed position.
- `extruder_theoretical_position` — Expected result; used for bounds checking.
- `extruder_tolerance` — Max deviation from theoretical before raising an error.
- `extruder_probe_mode` (0=single-side, 1=two-sided)
- `extruder_polarity_invert` — Invert probe trigger polarity.
- `extruder_y_cal_second_position` — Optional second position for Y-axis calibration.

### Shared Config Options
- `speed`, `probe_fast_speed`, `lift_speed` — Motion speeds.
- `accel` — Probe acceleration.
- `samples`, `sample_retract_dist`, `samples_tolerance`, `samples_tolerance_retries`
- `save_result` — Whether to persist calibration results to JSON.
- `y_cal_enable` — Enable Y-axis secondary calibration.
- `analog_output_pin`, `analog_range`, `analog_pullup_resistor` — ADC button for laser-based position sensing.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires extruder objects with `get_extruder_activate_status()` and `cmd_SWITCH_EXTRUDER_ADVANCED()` — fork-specific extruder methods.
- Calibration log directory falls back to `/tmp/calibration_data` if no virtual_sdcard is found — a path that may be unavailable or undesirable.
- The two-sided probing algorithm assumes the slot is symmetric and perfectly aligned with the probe axis; any angular misalignment will introduce systematic error.
- `probe_mode` configuration key is accidentally read as `'_probe_mode'` (with underscore prefix) for the per-extruder override — likely a bug.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Extruder Park Calibration module for Klipper
+import logging, os, queuefile, copy
+from . import probe, probe_inductance_coil
+
+class ExtruderParkCalibrationStep:
+    PROBING_IDLE = "idle"; PROBING_START = "probing"
+    PROBING_COMPLETE = "complete"; PROBING_ERROR = "error"
+
+class ExtruderParkCalibration:
+    def __init__(self, config):
+        ...
+        # Read per-extruder positions from config
+        for i in range(99):
+            section = 'extruder' if not i else 'extruder%d' % i
+            pos = config.getlists(section + '_start_position', ...)
+            if pos is not None:
+                self.extruder_start_positions[section] = ...
+            else:
+                break
+        self.gcode.register_command(
+            'CALIBRATE_EXTRUDER_PARK_POSITION', ...)
+        self.gcode.register_command('PROBE_SINGLE_POINT', ...)
+
+def load_config(config):
+    return ExtruderParkCalibration(config)
```
</details>

---

# flow_calibrator.py

## Summary
`flow_calibrator.py` implements `FlowCalibrator`, which performs automated pressure-advance (K factor) calibration by printing a test pattern and measuring the motor acceleration-time data via Klipper's `motion_report` trapeziodal queue. Two algorithms are supported: binary search (`DICHOTOMY`) and linear regression (`LINEAR_FITTING`). The module monitors extruder trapezoid move events (`trapq:extruder`) to capture acceleration ramps, feeds them to a compiled Cython extension (`flow_calculator`) for analysis, and persists the resulting K value to `flow_calibrator.json`. During printing it can run in-print calibration on each extruder and record whether calibration was performed for that print job.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automated in-print pressure-advance K calibration using acceleration-time data and a Cython flow calculator | U1 supports per-filament K-value auto-tuning at print start; upstream Klipper requires manual pressure advance tuning |

## Additions

### Classes
- **`AbortCalibration`** — Custom exception with a `message` field for clean calibration abort paths.
- **`AccelTimeQueryHelper`** — Collects `trapq:extruder` bulk sensor samples and extracts `(time, duration, start_velocity, acceleration)` tuples. Can write CSV for analysis.
- **`FlowCalibrator`** — Main extra loaded as `[flow_calibrator]`.

### G-code Commands
- **`FLOW_CALIBRATE`** — Run a full automatic K-factor calibration for the active extruder (prints test pattern, measures, applies result).
- **`FLOW_MEASURE_K`** — Measure K factor from existing printed pattern (no new print, just measurement).
- **`ACCEL_TIME_MEASURE`** — Start/stop raw acceleration-time data capture; writes CSV for offline analysis.
- **`FLOW_RESET_K`** — Reset all extruder K values to defaults and save.
- **`FLOW_APPLY_CALIBRATE_K`** — Apply the last calibrated K value to the extruder's pressure advance setting.

### Config Options
- `config_name` — JSON config file name (default `flow_calibrator.json`).
- `debug` (int, 0/1) — Enable debug mode (bypasses some guards).

### Persisted Config (`flow_calibrator.json`)
- `factor` — Dict mapping extruder names to K values: `{'extruder': 0.02, 'extruder1': 0.02, ...}`.
- `env` — Calibration environment parameters: `k_min`, `k_max`, `k_step`, `start_vel`, `start_dist`, `slow_vel`, `slow_dist`, `fast_vel`, `fast_dist`, `accel`, `loop`.

### Dependencies
- `flow_calculator` — Cython extension module (built by `extras/setup.py`).
- `motion_report.PrinterMotionReport` — For trapq sample subscription.

### Event Handlers
- `virtual_sdcard:reset_file` — Clears in-print calibration state.
- `pause_resume:cancel` — Aborts calibration.
- `filament_switch_sensor:runout` — Sets abort reason to `ABORT_REASON_FILAMENT_RUNOUT`.
- `filament_entangle_detect:tangled` — Sets abort reason to `ABORT_REASON_FILAMENT_TANGLED`.

### Abort Reasons
- `cancel_by_user`, `filament_runout`, `out_of_range`, `filament_tangled`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `flow_calculator` Cython extension to be compiled; without it the module fails to import. The `extras/setup.py` file handles the build.
- Requires `numpy` (`import numpy as np`) — not a standard Klipper dependency.
- Requires `queuefile` — a fork-specific Python extension.
- In-print calibration (`_calibrated_in_printing`) tracks state per print but does not handle multi-extruder sequential calibration robustly; only one calibration can be in progress at a time.
- The `_apply_k` method at startup calls `_set_pressure_advance` for all extruders in `extruder_list`, which is a fork-added printer object.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, multiprocessing, os, time, pathlib, queuefile
+from . import motion_report
+from . import flow_calculator
+import numpy as np, json
+
+ALGORITHM_TYPE_DICHOTOMY       = 'DICHOTOMY'
+ALGORITHM_TYPE_LINEAR_FITTING  = 'LINEAR_FITTING'
+
+DEFAULT_K = {'extruder': 0.02, 'extruder1': 0.02, 'extruder2': 0.02, 'extruder3': 0.02}
+DEFAULT_ENV = {'k_min': 0.005, 'k_max': 0.065, 'start_vel': 4, ...}
+
+class FlowCalibrator(object):
+    def __init__(self, config):
+        ...
+        self._gcode.register_command('FLOW_CALIBRATE', ...)
+        self._gcode.register_command('FLOW_MEASURE_K', ...)
+        self._gcode.register_command('ACCEL_TIME_MEASURE', ...)
+        self._gcode.register_command('FLOW_RESET_K', ...)
+        self._gcode.register_command('FLOW_APPLY_CALIBRATE_K', ...)
+
+def load_config(config):
+    return FlowCalibrator(config)
```
</details>

---

# power_loss_check.py

## Summary
`power_loss_check.py` implements `PowerLossCheck`, a Klipper extra that interfaces with a custom MCU firmware command set (`config_power_loss_check`) to monitor mains voltage via a GPIO line, detect power loss events, and support power-loss resume (PLR). The MCU measures the duty cycle of a mains-frequency sense signal to distinguish 110 V (~50% duty in a different voltage range) from 220 V supply, and sets a `power_loss_flag` when the signal disappears. On detection, Klipper is shut down with a structured error code. For 220 V supplies the module can automatically switch the bed heater PID profile (`pid2`). It also queries and stores the MCU's flash-saved stepper positions from the last print for PLR restoration.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: hardware mains-voltage monitoring with 110/220 V auto-detection, MCU-side PLR flash save, and automatic bed PID switching | U1 is sold in both 110 V and 220 V markets; the MCU saves critical position data on power loss; Klipper must read this to enable power-loss resume |

## Additions

### Classes
- **`PowerLossCheck`** — Klipper extra loaded via both `load_config` (as `[power_loss_check]`) and `load_config_prefix` (as `[power_loss_check <name>]`). Multiple instances are tracked in a shared `power_loss_check_list` object.

### G-code Commands (master instance only)
- **`UPDATE_POWER_LOSS_REPORT_INTERVAL INTERVAL=<f>`** — Update MCU reporting interval.
- **`QUERY_POWER_LOSS_CHECK_INFO`** — Query and display current voltage type, duty cycle, and power-loss flag.
- **`ENABLE_POWER_LOSS_REPORT_LOG ENABLE=<0|1>`** — Toggle verbose MCU status output to G-code console.

### G-code Commands (all instances, multiplexed by `NAME=<name>`)
- **`ENABLE_POWER_LOSS NAME=<name> ENABLE=<0|1> [PRINT_FLAG=<u32>] [MOVE_LINE=<u32>]`** — Enable/disable power-loss monitoring on the MCU; sets the print-flag and current move line for PLR.
- **`QUERY_POWER_LOSS_FLASH_VALID NAME=<name>`** — Query MCU flash validity info (last sequence, valid sector count, env flag, saved stepper count).
- **`QUERY_POWER_LOSS_STEPPER_INFO NAME=<name> [TYPE=<u8>] [INDEX=<u8>]`** — Retrieve saved stepper position from flash.

### Key Config Options
- `pin` — GPIO sense pin for mains monitoring (supports invert/pullup).
- `power_loss_trigger_time` (float, default 0.0109 s) — Minimum signal-loss duration before declaring power loss.
- `report_interval` (int, default 0) — MCU periodic report interval in seconds.
- `duty_threshold` (float, default 0.54) — Duty cycle threshold for voltage type detection.
- `debounce_threshold` (int, default 20) — MCU debounce count.
- `type_confirm_threshold` (int, default 3) — Consecutive samples needed to confirm voltage type.
- `bed_pid_control_mode` (str, `'auto_switch'`|`'pid2'`|`'default'`) — Master only: bed PID switching mode.

### MCU Commands Used
- `config_power_loss_check`, `update_report_interval`, `enable_power_loss`
- `query_power_loss_status`, `query_power_loss_flash_valid`, `query_power_loss_stepper_info`

### Events
- `power_loss_check:mcu_update_complete` — Fired after all instances have read their flash data on startup.

### Auto PID Switching
On `klippy:ready`, the master instance starts a timer that monitors `voltage_type` and automatically issues `SET_PID_PROFILE HEATER=heater_bed PROFILE=pid2` when 110 V is detected.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires custom MCU firmware commands not present in upstream Klipper; will fail at MCU identify if the firmware does not support them.
- On power-loss detection, `printer.invoke_shutdown` is called with a JSON-encoded error — a Snapmaker-specific extension of the normal `invoke_shutdown(msg)` API.
- The shared `power_loss_check_list` object uses `printer.add_object` / `printer.lookup_object` without a formal Klipper config section, which is unconventional and may conflict if the object name is reused.
- `ctypes.c_int32` is used to sign-extend MCU stepper position values — correct on all platforms but an unusual pattern in Klipper code.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Power loss detection handling
+import logging, copy, ctypes
+import pins, stepper
+
+class PowerLossCheck:
+    def __init__(self, config):
+        ...
+        self._mcu.add_config_cmd(
+            "config_power_loss_check oid=%d clock=%u power_loss_trigger_time=%u ...")
+        # Register MCU responses
+        self._mcu.register_response(self.handle_report_power_loss_status,
+                            "report_power_loss_status", self._oid)
+        # G-code commands (master)
+        gcode.register_command('UPDATE_POWER_LOSS_REPORT_INTERVAL', ...)
+        gcode.register_command('QUERY_POWER_LOSS_CHECK_INFO', ...)
+        # G-code commands (all instances)
+        gcode.register_mux_command("ENABLE_POWER_LOSS", "NAME", ...)
+        gcode.register_mux_command("QUERY_POWER_LOSS_FLASH_VALID", "NAME", ...)
+
+def load_config(config): ...
+def load_config_prefix(config): ...
```
</details>

---

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

---

# defect_detection.py

## Summary
`defect_detection.py` implements `DefectDetection`, a Klipper extra that uses an on-board camera (via MQTT JSON-RPC) to detect four categories of print defects in real time: dirty bed before printing, noodle stringing above the print, residue on the bed surface, and a dirty nozzle. Each detection type has independently configurable enable/disable, a sliding-window history, and a high/low sensitivity setting. When a defect is confirmed the print is paused via `pause_resume.send_pause_command()` and an exception event is raised. A configurable `ignore_detect_layer` suppresses detection for the first N layers. Detection state and configuration are persisted in `defect_detection.json`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: AI-based real-time print defect detection using MQTT camera service, with four defect categories and sliding-window confirmation | U1 has an optional cavity camera; this module provides automated quality monitoring without user intervention |

## Additions

### Classes
- **`DefectDetection`** — Klipper extra loaded as `[defect_detection]`.

### G-code Commands
- **`DEFECT_DETECTION_CONFIG`** — Set detection parameters (enable/disable specific checks, sensitivity, window sizes) at runtime; persists to JSON.
- **`DEFECT_DETECTION_START`** — Reset internal state and arm detection for the current layer.
- **`DEFECT_DETECTION_DETECT`** — Trigger a single detection round (sends camera JSON-RPC request, blocks for result).
- **`DEFECT_DETECTION_DETECT_BED`** — Specifically detect dirty-bed or residue on the build surface.
- **`DEFECT_DETECTION_DETECT_NOZZLE`** — Specifically detect a dirty nozzle.

### Webhook Endpoint
- `defect_detection/config` — REST-style config update endpoint (same as `DEFECT_DETECTION_CONFIG` G-code).

### Config Options (in `[defect_detection]` section)
- `debug_mode` (bool, default False)
- `bed_detect_pos_x/y` (float) — XY position for bed defect detection camera shot.
- `bed_detect_probe_distance` (float, default 50 mm) — Z height for bed camera shot.
- `ignore_detect_layer` (int, default 30) — Skip detection for this many initial layers.
- `clean_bed_threshold_high/low` — Confidence thresholds for clean-bed detection.
- `residue_threshold_high/low`, `noodle_threshold_high/low`, `nozzle_threshold_high/low` — Per-category thresholds.

### Runtime Config (persisted in `defect_detection.json`)
- `main_enable` (bool) — Master enable.
- `sen_high_factor = 0.2`, `sen_low_factor = 0.5` — Global sensitivity multipliers.
- Per-category config blocks: `clean_bed`, `noodle`, `residue`, `nozzle` — each with `enable`, `check_window`, and `sensitivity`.

### Detection Categories and Confirm Codes
- `CONFIRM_DIRTY_BED = 1`, `CONFIRM_NOODLE = 2`, `CONFIRM_RESIDUE = 3`, `CONFIRM_DIRTY_NOZZLE = 4`

### MQTT Topics
- `camera/request`, `camera/response`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `mqtt` extra, `print_task_config`, and an on-board camera service implementing the `camera.*` JSON-RPC methods.
- `DEFECT_DETECTION_DETECT` and `DEFECT_DETECTION_DETECT_BED` are synchronous (use `send_request_with_response` with 5 s timeout), blocking the G-code thread.
- The `ignore_detect_start_layer` tracking logic assumes `print_stats.info_current_layer` is populated — requires fork-modified `print_stats`.
- Sliding-window history (`check_noodle_result`, `check_residue_result`) is a plain Python list with no size cap, only reset on print start.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, os, copy
+from .jsonrpc import *
+
+TIME_INTERVAL    = 3.5
+REQUEST_TIMEOUT  = 5.0
+
+CONFIRM_DIRTY_BED    = 1
+CONFIRM_NOODLE       = 2
+CONFIRM_RESIDUE      = 3
+CONFIRM_DIRTY_NOZZLE = 4
+
+class DefectDetection:
+    def __init__(self, config):
+        ...
+        self.gcode.register_command("DEFECT_DETECTION_CONFIG", ...)
+        self.gcode.register_command("DEFECT_DETECTION_START", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT_BED", ...)
+        self.gcode.register_command("DEFECT_DETECTION_DETECT_NOZZLE", ...)
+        webhooks.register_endpoint("defect_detection/config", ...)
+
+def load_config(config):
+    return DefectDetection(config)
```
</details>

---

# extruder_config_bak.py

## Summary
`extruder_config_bak.py` implements `ExtruderConfigBak`, a Klipper extra that backs up extruder park position configuration (XY park coordinates and Y idle position) from the Klipper config file to a persistent JSON file (`extruder_config.json` in the `persistent` config directory). This ensures that extruder park calibration data survives a Klipper config reset or firmware update. At load time (`load_config`) it calls `extruder_config_bak()` which reads all `[extruder]`/`[extruder<N>]` sections, extracts `xy_park_position`, `y_idle_position`, and optionally `base_position`, and writes them to the persistent file if it does not already exist. It also handles migration from an older single-file format to the new split-file format (park data vs. base-position data). A `DELETE_EXTRUDER_BACKUP_CONFIG` command allows authorised deletion of the backup files.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: automatic backup of extruder park positions to a persistent JSON file with atomic writes and migration support | U1's tool-changer stores calibrated park positions in the Klipper config; this module ensures they are preserved in a separate persistent location across config resets |

## Additions

### Classes
- **`ExtruderConfigBak`** — Klipper extra loaded as `[extruder_config_bak]`.

### G-code Commands
- **`DELETE_EXTRUDER_BACKUP_CONFIG`** — Delete the persistent backup files. Gated by `printer.check_extruder_config_permission()` — a fork-specific API that checks for a permission file.

### Key Config Files
- `extruder_config.json` (persistent dir) — Contains `xy_park_position` and `y_idle_position` per extruder.
- `extruder_base_position.json` (snapmaker config dir) — Contains `base_position` per extruder.

### Public API
- `get_extruder_config(extruder_name, field_name=None)` — Read a field from the JSON backup. Supports dotted-path field names and integer indices (e.g. `'xy_park_position.0'`).
- `update_extruder_config(extruder_name, field_name=None, value=None)` — Atomically update a field in the JSON backup using `queuefile.sync_write_file`.
- `extruder_config_bak(config)` — Called at load time to perform the initial backup (or migration) if the persistent file does not exist.
- `_migrate_existing_backup()` — Reads old-format single-file backup and splits it into park-data and base-position files.

### Atomic Write
- `_save_config_atomically(config_path, data)` — Uses `queuefile.sync_write_file(..., safe_write=True)` for atomic JSON persistence.

### Extruder Sections Scanned
All `[extruder]` and `[extruder1]`–`[extruder98]` sections present in the Klipper config.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `queuefile` (fork-specific Python extension) for atomic writes.
- `printer.get_snapmaker_config_dir("persistent")` is a fork-specific API; the "persistent" sub-directory is separate from the normal Snapmaker config dir to survive firmware updates.
- `printer.check_extruder_config_permission()` is not defined in upstream Klipper; without it, `DELETE_EXTRUDER_BACKUP_CONFIG` will always raise an error.
- If `xy_park_position` or `y_idle_position` are missing from any extruder section, `extruder_config_bak()` raises a `config.error` at load time, preventing Klipper from starting.
- The migration code comments out the rename of the old file after migration (left as `.tmp`), which means re-running migration will overwrite the new file each time.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import json, os, tempfile, logging, queuefile
+
+EXTRUDER_CONFIG_FILE = "extruder_config.json"
+EXTRUDER_BASE_POSITION_FILE = "extruder_base_position.json"
+
+class ExtruderConfigBak:
+    def __init__(self, config):
+        self.config_path = os.path.join(
+            self.printer.get_snapmaker_config_dir("persistent"),
+            EXTRUDER_CONFIG_FILE)
+        ...
+        gcode.register_command('DELETE_EXTRUDER_BACKUP_CONFIG', ...)
+
+    def extruder_config_bak(self, config):
+        # scan all [extruder] sections
+        # extract xy_park_position, y_idle_position, base_position
+        # write to persistent JSON if not already present
+        ...
+
+    def update_extruder_config(self, extruder_name, field_name=None, value=None):
+        # atomic JSON update via queuefile.sync_write_file
+        ...
+
+def load_config(config):
+    extruder_bak = ExtruderConfigBak(config)
+    extruder_bak.extruder_config_bak(config)
+    return extruder_bak
```
</details>

---

# setup.py

## Summary
`setup.py` is a standard Python `setuptools` build script placed inside `klippy/extras/` to compile the `flow_calculator.pyx` Cython extension that is required by `flow_calibrator.py`. It calls `cythonize("flow_calculator.pyx")` and registers the resulting C extension with setuptools. This file is not a Klipper extra and has no `load_config` entry point; it exists solely to support the `python setup.py build_ext --inplace` workflow needed to build the `flow_calculator` shared library before Klipper can import `flow_calibrator`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New file: `setuptools`/`Cython` build script for the `flow_calculator` C extension | The flow calibration algorithm is performance-sensitive and implemented in Cython; this file provides the standard build mechanism |

## Additions

### Build Configuration
- **`cythonize("flow_calculator.pyx")`** — Compiles `flow_calculator.pyx` to a C extension.
- `include_dirs=[]` — No NumPy headers included by default (NumPy include path is commented out with a note that it can be added for local testing).
- `zip_safe=False`

### No Classes, G-code Commands, or Config Options
This file is purely a build artifact; it defines no Klipper objects.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `Cython` and a C compiler in the build environment; the standard Klipper deployment process does not include a Cython build step.
- If `flow_calculator.pyx` is not compiled before Klipper starts, `flow_calibrator.py` will fail to import with `ModuleNotFoundError: No module named 'flow_calculator'`.
- The `setup.py` is placed inside `klippy/extras/` rather than the repository root, making `python setup.py build_ext --inplace` the expected invocation from that directory.
- The file is empty of any `install_requires` or version metadata, making it unsuitable as a distributable package; it is purely for in-place builds.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+from setuptools import setup
+from Cython.Build import cythonize
+
+# for local test
+# import numpy as np
+# include_dirs=[np.get_include()]
+include_dirs=[]
+
+setup(
+    ext_modules=cythonize("flow_calculator.pyx"),
+    include_dirs=include_dirs,
+    zip_safe=False,
+)
```
</details>

---

# Major Upstream-Modified Extras

## Summary
Five upstream Klipper extras have been significantly rewritten in the fork to support Snapmaker U1 hardware features. The most extensive change is `virtual_sdcard.py`, which gains a comprehensive power-loss recovery (PLR) subsystem. `heaters.py` adds per-heater dynamic power limits and PID profiles. `probe.py` reverts newer upstream abstractions. `bed_mesh.py` integrates the inductance coil probe and adds new G-code commands. `resonance_tester.py` removes Z-axis vibration support and adds a fast state-machine calibration mode.

---

## `virtual_sdcard.py` — Power-Loss Recovery Engine

### Summary
The upstream virtual SD card module handles G-code file streaming from a directory. The fork transforms it into a comprehensive print job supervisor that continuously snapshots the full printer state (temperatures, positions, flow rates, fan speeds, mesh, tool assignments, pressure advance, object exclusions) to `/home/lava/printer_data/klippy/` so that a print can resume after power loss or shutdown.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Simple G-code line streaming from `path` directory | Same streaming plus continuous state serialisation to 10 JSON environment files | Power-loss recovery for U1 hardware |
| No tool-change awareness | Tracks `T0`–`T31` tool commands, pre-extrude logic, `NO_PRE_EXTRUDE_COMMANDS` set | U1 has up to 4 extruders (T0–T3) with complex tool-change protocol |
| G-code line not tracked | `self.lines` counter, `self.current_line_gcode`, per-line parsing via embedded `GCodeParser` | Needed to seek to resume line on recovery |
| No shutdown handler | Registers `klippy:shutdown` → `handle_shutdown()` | Flush PLR state on unexpected shutdown |
| Standard `_reset_file()` | `exit_to_idle(rm_pl_env_file)`, `_pl_recovery_reset_file()`, `_reset_file()` with PLR cleanup | Maintain separation between normal end vs recovery reset |
| No MCU flash interaction | Registers `power_loss_check:mcu_update_complete` → `handle_get_mcu_pl_flash_data()`, calls `notify_mcu_enable_power_loss()` | Reads/writes stepper Z position to MCU flash via `power_loss_check` |

### Additions
**New constants (all paths under `/home/lava/printer_data/klippy/`):**
- `PL_RECORD_FILE_DIR`, `PL_PRINT_FILE_ENV`, `PL_PRINT_FILE_MOVE_ENV`, `PL_PRINT_TEMPERATURE_ENV`, `PL_PRINT_FLOW_AND_SPEED_FACTOR_ENV`, `PL_PRINT_PRESSURE_ADVANCE_ENV`, `PL_PRINT_LAYER_INFO_ENV`, `PL_PRINT_FAN_INFO_ENV`, `PL_PRINT_Z_ADJUST_POSITION_ENV`, `PL_PRINT_OBJECTS_ENV`, `PL_PRINT_EXCLUDE_OBJECTS_ENV`
- `MAX_TOOL_NUMBER = 32`, `GENERIC_MOVE_GCODE`, `TOOL_CHANGE_COMMANDS`, `NO_PRE_EXTRUDE_COMMANDS`, `USE_REALTIME_TEMP_GCODE`

**New G-code commands:**
- `SDCARD_PRINT_TEST` — internal test hook
- `SDCARD_PRINT_PL_RESTORE` — trigger power-loss restore sequence
- `SDCARD_PRINT_PL_CLEAR_ENV` — clear all PLR environment files

**New public methods (PLR API used by other modules):**
- `record_pl_print_file_env()`, `force_record_pl_print_file_env()`, `get_pl_print_file_env()`
- `record_pl_print_temperature_env()`, `get_pl_print_temperature_env()`
- `record_pl_print_flow_and_speed_factor()`, `get_pl_print_flow_and_speed_factor()`
- `record_pl_print_pressure_advance()`, `get_pl_print_pressure_advance()`
- `record_pl_print_layer_info()`, `get_pl_print_layer_info()`
- `record_pl_print_fan_env()`, `get_pl_print_fan_env()`
- `record_pl_print_z_adjust_position()`, `get_pl_print_z_adjust_position()`, `rm_pl_print_z_adjust_position()`
- `record_pl_print_file_move_env()`, `parse_power_loss_move_env()`, `pl_find_latest_move_env()`
- `record_pl_print_objects_env()`, `get_pl_print_objects_env()`
- `record_pl_print_exclude_objects_env()`, `get_pl_print_exclude_objects_env()`
- `notify_mcu_enable_power_loss()`, `config_pl_allow_save_env()`
- `backup_print_env_info()`, `power_loss_info_check()`, `rm_power_loss_info()`
- `restore_print()`, `pl_bed_mesh_restore()`, `flush_pl_print_env()`
- `save_environment_data()` — atomic write via `queuefile`
- `get_pl_env_flag()`, `_valid_power_loss_condition()`, `_valid_power_loss_condition_with_pause()`
- `wait_until_not_homing()`

**New embedded class `GCodeParser`:** Stateful per-line G-code parser used during streaming to track positions, speeds, temperatures, flow factors, and objects for PLR snapshotting.

### Risks / Compatibility Notes
- Hard-coded path `/home/lava/printer_data/klippy/` — fails on non-U1 systems unless `printer.get_snapmaker_config_dir()` fallback works
- Uses `queuefile` (fork-exclusive) for async atomic JSON writes
- Depends on `power_loss_check` extra (fork-exclusive); `power_loss_check:mcu_update_complete` event will never fire on upstream
- The `GCodeParser` duplicates some gcode parsing logic, creating a maintenance risk if upstream `gcode.py` changes its command format
- `SDCARD_PRINT_PL_RESTORE` bypasses normal `SDCARD_RESET_FILE` flow — callers must use the correct restore sequence

### Raw Diff
<details>
<summary>View Diff (first 120 lines)</summary>

```diff
--- a/klippy/extras/virtual_sdcard.py
+++ b/klippy/extras/virtual_sdcard.py
+import json, re, copy, tarfile, threading, queuefile
+MAX_TOOL_NUMBER = 32
+GENERIC_MOVE_GCODE = {'G0', 'G1', 'G2', 'G3'}
+TOOL_CHANGE_COMMANDS = {f'T{i}' for i in range(MAX_TOOL_NUMBER)}
+NO_PRE_EXTRUDE_COMMANDS = TOOL_CHANGE_COMMANDS | {'BED_MESH_CALIBRATE'}
+USE_REALTIME_TEMP_GCODE = {'BED_MESH_CALIBRATE'}
+PL_RECORD_FILE_DIR = "/home/lava/printer_data/klippy"
+PL_PRINT_FILE_ENV = "pl_print_file_env.json"
+# ... 9 more PL_PRINT_*_ENV constants ...
+        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
+        self.printer.register_event_handler("power_loss_check:mcu_update_complete",
+                                            self.handle_get_mcu_pl_flash_data)
+        self.pl_switch = False
+        self.pl_mcu_flash_valid_line = 0xFFFFFFFF
+        self.pl_mcu_flash_stepper_z_pos = 0xFFFFFFFF
+        self.pl_mcu_flash_resume_line = 0xFFFFFFFF
```
</details>

---

## `heaters.py` — Dynamic Power Limits & PID Profiles

### Summary
The fork modifies the core heater control module to add per-heater dynamic maximum power limits (enabling reduced power in idle/active states) and a JSON-backed PID profile store (`SET_PID_PROFILE`). It also relaxes the fault detection timeout from 3 s to 7 s, adds temperature overshoot allowances, and changes the PWM update threshold variable name.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `MAX_HEAT_TIME = 3.0` (PWM output watchdog) | `MAX_HEAT_TIME = 7.0` | U1 extruders have higher thermal mass; 3 s caused false watchdog trips |
| `MAX_MAINTHREAD_TIME = 5.0`, `QUELL_STALE_TIME = 7.0` | Removed; replaced with `READ_TIME_TOL = 0.45`, `MIN_UPDATE_RATIO = 0.15` | Different sensor update scheduling approach |
| `MIN_PWM_CHANGE_RATIO = 0.05` | `pwm_min_set_diff` config option (default 0.05) | Made configurable per-heater |
| Fixed `min_temp`/`max_temp` bounds | `min_temp_overshoot` and `max_temp_overshoot` config options expand bounds | Allows small thermal excursion without fault during tool changes |
| Single fixed `max_power` | `idle_hold_max_power`, `active_hold_max_power` config options + `set_dynamic_max_power()` | U1 uses lower power for idle extruders to reduce heat creep |
| No PID profile management | `SET_PID_PROFILE HEATER=<name> [PROFILE=<name>]` G-code + JSON file backing | Allows pre-calibrated PID sets per material/tool |

### Additions
**New config options** (per `[extruder]`/`[heater_bed]` section):
- `min_temp_overshoot`: float, default 0 — extends min_temp check downward
- `max_temp_overshoot`: float, default 0 — extends max_temp check upward
- `idle_hold_max_power`: float 0–1, optional — max PWM when heater is idle
- `active_hold_max_power`: float 0–1, optional — max PWM when heater is printing
- `pwm_min_set_diff`: float, default 0.05 — minimum PWM delta before update
- `allow_pid_calibrate`: bool, default True — whether `PID_CALIBRATE` is permitted

**New G-code command:**
- `SET_PID_PROFILE HEATER=<name> PROFILE=<name>` — load a named PID profile from JSON

**New methods:**
- `get_dynamic_max_power()` / `set_dynamic_max_power(power, delay_increase=True)`
- `cmd_SET_PID_PROFILE()`, `set_pid_profile()`
- `_load_heater_pid_profiles_from_json()`, `_save_heater_pid_profiles_to_json()`
- `_validate_pid_profile()`
- `update_pending_extruder()`, `remove_pending_extruder()` — heating queue management

### Risks / Compatibility Notes
- `MAX_HEAT_TIME = 7.0` means the PWM watchdog allows 7 s between heater callbacks; upstream uses 3 s — this increases risk of thermal runaway going undetected on non-U1 hardware
- `allow_pid_calibrate = False` silently prevents `PID_CALIBRATE` without error; could confuse users unaware of the option
- PID profile JSON format is undocumented; if the JSON is corrupted, heater init will fail

### Raw Diff
<details>
<summary>View Diff (key additions)</summary>

```diff
-MAX_HEAT_TIME = 3.0
+MAX_HEAT_TIME = 7.0
+        min_temp_overshoot = config.getfloat('min_temp_overshoot', 0, minval=0)
+        max_temp_overshoot = config.getfloat('max_temp_overshoot', 0, minval=0)
+        self.sensor.setup_minmax(self.min_temp - min_temp_overshoot,
+                                 self.max_temp + max_temp_overshoot)
+        self.idle_hold_max_power = config.getfloat('idle_hold_max_power', None, above=0., maxval=1.)
+        self.active_hold_max_power = config.getfloat('active_hold_max_power', None, above=0., maxval=1.)
+        self.allow_pid_calibrate = config.getboolean('allow_pid_calibrate', True)
+        gcode.register_mux_command("SET_PID_PROFILE", "HEATER",
+                                   short_name, self.cmd_SET_PID_PROFILE, ...)
```
</details>

---

## `probe.py` — ProbeResult Removal & API Simplification

### Summary
The fork reverts upstream's introduction of `manual_probe.ProbeResult` namedtuple and the `can_set_z_offset` guard on `PROBE_CALIBRATE`/`Z_OFFSET_APPLY_PROBE`. It returns plain `list` from `_calc_mean_position()` instead of a named tuple, and simplifies `ProbeSessionHelper.__init__`.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `_calc_mean_position()` returns `ProbeResult` namedtuple with `.bed_x`/`.bed_y`/`.bed_z` | Returns plain `list` of 3 floats indexed by `[2]` etc. | Fork diverged before ProbeResult was introduced |
| `ProbeSessionHelper.__init__` takes `can_set_z_offset=True` flag | No `can_set_z_offset` param; `PROBE_CALIBRATE`/`Z_OFFSET_APPLY_PROBE` always registered | Fork does not use the can_set_z_offset gate |
| `self.last_probe_position = gcode.Coord(...)` | `self.probe_calibrate_z = 0.` | Simpler scalar tracking |
| `self.probe_calibrate_info` dict | Removed | Not needed without ProbeResult |

### Additions
- `probing_coil_move(mcu_probe, pos, speed)` — custom move method used by inductance coil probe (calls `homing.probing_coil_move`)

### Removals / Overrides
- `ProbeResult` namedtuple usage (replaced with plain list)
- `can_set_z_offset` constructor parameter
- `self.probe_calibrate_info` tracking dict

### Risks / Compatibility Notes
- Any plugin calling `result.bed_z` on a probe result will get `AttributeError` — incompatible with upstream extras that expect `ProbeResult`
- The `position[2]` indexing is fragile if position list length ever changes

### Raw Diff
<details>
<summary>View Diff (key changes)</summary>

```diff
-        inv_count = 1. / float(len(positions))
-        return manual_probe.ProbeResult(
-            *[sum([pos[i] for pos in positions]) * inv_count for i in range(len(positions[0]))])
+        count = float(len(positions))
+        return [sum([pos[i] for pos in positions]) / count for i in range(3)]
-    z_sorted = sorted(positions, key=(lambda p: p.bed_z))
+    z_sorted = sorted(positions, key=(lambda p: p[2]))
-    def __init__(self, config, probe, query_endstop=None, can_set_z_offset=True):
+    def __init__(self, config, probe, query_endstop=None):
```
</details>

---

## `bed_mesh.py` — Inductance Coil Integration & New Commands

### Summary
The fork integrates the inductance coil probe as an alternative bed-levelling sensor, adds three new G-code commands for the U1 calibration workflow, adds a `BedMeshProbeState` management class, and changes persistent profile storage from Klipper's `save_variables` to custom JSON files (one per profile, stored on disk). It also imports `probe_inductance_coil` (fork-exclusive) and adds an abort mechanism accessible via Moonraker webhooks.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Only standard probe or eddy current probe | Also supports `inductance_coil` probe via `is_inductance_coil_probe` flag | U1 uses inductive probes for bed levelling |
| Single `BedMeshCalibrate` class | Added `BedMeshProbeState` class with state tracking | Multi-step calibration workflow for U1 |
| No webhook abort | `_handle_abort_probe_mesh` registered on `webhooks` endpoint | Allow Moonraker/UI to cancel in-progress mesh calibration |
| No profile file output | `BED_MESH_OUTPUT_FILE` G-code dumps grid to file | Allows logging/saving mesh data externally |
| Profiles saved via Klipper's config system | `_save_profile_custom()` / `_load_profile_custom()` / `_remove_profile_custom()` using JSON files | Fork-specific storage path outside Klipper config |
| No manual levelling check | `check_manual_leveling_needed()`, `BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED` | U1 workflow requires tram check before mesh |
| `import probe` only | `from . import probe, probe_inductance_coil` | Needed for inductance coil probe helper |

### Additions
**New constants:**
- `BED_VERSION_202507_OEM = "/oem/.bed_202507"` — hardware version sentinel file
- `BED_VERSION_202507_UDATA = "/userdata/.bed_202507"` — user data hardware version sentinel

**New exception class:**
- `BedMeshActiveAbort` — raised when bed mesh calibration is aborted mid-run

**New G-code commands:**
- `BED_MESH_OUTPUT_FILE` — dump current mesh interpolated grid to a file
- `BED_MESH_CALIBRATE_PREPARE` — prepare state for upcoming calibration run
- `BED_PRELEVELING_SCAN` — perform pre-levelling inductance scan
- `BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED` — clear the "needs manual levelling" flag

**New webhook endpoint:**
- `handle: _handle_abort_probe_mesh` — cancels active calibration via Moonraker

**New class `BedMeshProbeState`:** Manages state for multi-step calibration sequences including `probe_point_callback()`, `abort_probe()`, `check_manual_leveling_needed()`, `print_probed_matrix()`, and custom profile I/O.

### Risks / Compatibility Notes
- `from . import probe_inductance_coil` will fail on upstream Klipper (module doesn't exist)
- Custom profile JSON files at undocumented paths won't be imported by standard Klipper profile management
- `BedMeshActiveAbort` exception bypasses normal error handling path
- Typo in comments (`retreive commma`) from fork revert of upstream comment fixes

### Raw Diff
<details>
<summary>View Diff (key additions)</summary>

```diff
+import logging, math, json, collections, os, queuefile
+from . import probe, probe_inductance_coil
+BED_VERSION_202507_OEM   = "/oem/.bed_202507"
+BED_VERSION_202507_UDATA = "/userdata/.bed_202507"
+class BedMeshActiveAbort(Exception):
+    pass
+        self.gcode.register_command('BED_MESH_OUTPUT_FILE', ...)
+        self.gcode.register_command('BED_MESH_CALIBRATE_PREPARE', ...)
+        self.gcode.register_command('BED_PRELEVELING_SCAN', ...)
+        self.gcode.register_command('BED_MESH_CLEAR_MANUAL_LEVELING_REQUIRED', ...)
+        webhooks.register_endpoint(...)  # abort handler
+        if config.get_prefix_sections("inductance_coil"):
+            self.is_inductance_coil_probe = True
+            self.probe_helper = probe_inductance_coil.ProbePointsHelper(...)
```
</details>

---

## `resonance_tester.py` — Z-Axis Removal & Fast Shaper Calibration

### Summary
The fork removes Z-axis vibration testing (all vibration directions are reduced from 3D to 2D), removes the `SweepingVibrationsTestGenerator` class and `ResonanceTestExecutor` class, renames `VibrationPulseTestGenerator` to `VibrationPulseTest`, and adds a state machine (`STATE_IDLE`/`STATE_SHAPER_CALIBRATING`/`STATE_COMPLETED`/`STATE_FAILED`) plus a new `SM_FAST_SHAPER_CALIBRATE` command for automated one-shot calibration.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Vibration axes are 3D tuples `(x, y, z)` | Vibration axes are 2D tuples `(x, y)` | U1's LIS2DW accelerometers mounted on print heads; Z not relevant for XY corexy shaping |
| `vib_dir` format: `(1., 0., 0.)` for X | `vib_dir` format: `(1., 0.)` for X | Consistent with 2D removal |
| `chip_axis` Z check `if self._vib_dir[2] and 'z' in chip_axis` | Removed Z check | No Z-axis vibration testing |
| `VibrationPulseTestGenerator` class | Renamed to `VibrationPulseTest` | Simplification (no longer "generator" pattern) |
| `SweepingVibrationsTestGenerator` class | Removed | Fork does not support sweep mode |
| `ResonanceTestExecutor` class | Removed | Replaced by simplified state machine approach |
| `import itertools` | Removed | Not needed after removal of zip-grouped chip iteration |
| No state management | `STATE_IDLE/SHAPER_CALIBRATING/COMPLETED/FAILED` string constants + `self.state` | Moonraker can poll `get_status()` to track calibration progress |
| `get_status()` returns basic info | Returns `{'state': ..., ...}` | Exposes state to Fluidd/Mainsail UI |

### Additions
- `STATE_IDLE`, `STATE_SHAPER_CALIBRATING`, `STATE_COMPLETED`, `STATE_FAILED` — state constants
- `SM_FAST_SHAPER_CALIBRATE` G-code command — performs automated X+Y shaper calibration in sequence
- `cmd_SM_FAST_SHAPER_CALIBRATE()` — implementation
- `check_homed()` — pre-check that axes are homed before calibration
- `_run_test()` — internal helper wrapping the calibration sequence
- `get_status()` — now returns `state` field for Moonraker status polling

### Removals / Overrides
- `VibrationPulseTestGenerator` → `VibrationPulseTest` (rename)
- `SweepingVibrationsTestGenerator` class removed
- `ResonanceTestExecutor` class removed
- Z-axis support removed from all vibration direction tuples
- `itertools` import removed

### Risks / Compatibility Notes
- Z-axis shaper tuning completely unavailable — if upstream Z motion compensation features are used with this fork, they will fail silently or error
- `SM_FAST_SHAPER_CALIBRATE` is U1-specific and requires the LIS2DW accelerometers to be properly configured
- Removal of `SweepingVibrationsTestGenerator` means `TEST_RESONANCES SWEEP=1` (if present in user configs) will error

### Raw Diff
<details>
<summary>View Diff (key changes)</summary>

```diff
-import itertools, logging, math, os, time
+import logging, math, os, time
+STATE_IDLE                              = 'idle'
+STATE_SHAPER_CALIBRATING                = 'shaper_calibrating'
+STATE_COMPLETED                         = 'completed'
+STATE_FAILED                            = 'failed'
-class VibrationPulseTestGenerator:
+class VibrationPulseTest:
-class SweepingVibrationsTestGenerator:
-class ResonanceTestExecutor:
-            self._vib_dir = [(1., 0., 0.), (0., 1., 0.), (0., 0., 1.)][ord(axis)-ord('x')]
+            self._vib_dir = (1., 0.) if axis == 'x' else (0., 1.)
-    return TestAxis(vib_dir=(dir_x, dir_y, dir_z))
+    return TestAxis(vib_dir=(dir_x, dir_y))
+        self.gcode.register_command("SM_FAST_SHAPER_CALIBRATE",
+                                    self.cmd_SM_FAST_SHAPER_CALIBRATE, ...)
```
</details>

---

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

---

# coded_exception.py

## Summary
A fork-exclusive module that introduces `CodedException`, a structured exception base class used throughout the Snapmaker U1 firmware layer. Every exception carries a machine-readable identity tuple (`id`, `index`, `code`), a severity `level`, behavioural flags (`oneshot`, `is_persistent`, `proactive_report`), and an optional `action` string. This allows the host software stack (Klipper → exception_manager → Moonraker) to route, deduplicate, and persist errors in a structured way rather than relying on free-form strings. Upstream Klipper has no equivalent; all errors are plain `Exception` subclasses or `configparser.Error`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Errors are plain Python `Exception` subclasses with a free-form string message | `CodedException` carries `id`, `index`, `code`, `level`, `oneshot`, `is_persistent`, `proactive_report` metadata | Enables structured error reporting to Moonraker/UI without string parsing |
| No error identity system | Errors have a numeric identity in the format `LLLL-IIII-NNNN-CCCC` (level-id-index-code) | Enables deduplication and persistence across restarts |
| N/A — new file | `from_exception()` class method wraps any plain exception in a `CodedException` | Lets older code that raises plain exceptions interoperate with the new system |

## Additions
- `CodedException` class — extends `Exception` with structured metadata fields.
  - Constructor parameters: `message`, `action`, `id`, `index`, `code`, `oneshot`, `level`, `is_persistent`, `proactive_report`
  - Default values: `id=522`, `index=0`, `code=0`, `level=3`, `oneshot=1`, `is_persistent=0`, `proactive_report=1`, `action='cancel'`
- `CodedException.to_dict()` — serialises all instance attributes to a `dict`.
- `CodedException.structured_code()` — returns the full `LLLL-IIII-NNNN-CCCC` string representation.
- `CodedException.basic_structured_code()` — returns the shorter `IIII-NNNN-CCCC` form used in persistence keys.
- `CodedException.from_exception(exc, **kwargs)` — class method that either returns `exc` unchanged if it is already a `CodedException`, or wraps a plain exception in a new `CodedException` with optional field overrides.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `gcode.CommandError`, `configfile.ConfigError`, `pins.error`, and `msgproto.error` all inherit from `CodedException`. Any code that catches `Exception` broadly will still work, but code specifically catching the original `Exception` types will now receive objects with extra fields.
- Default `id=522` maps to `MODULE_ID_MOTION` in `exception_manager.py`. If an exception is raised without overriding `id`, it will always appear as a motion-subsystem error in the UI.
- `proactive_report=1` means exceptions propagate to Moonraker by default. Setting it to `0` silences the report without preventing the exception from propagating in Python.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/coded_exception.py
@@ -0,0 +1,74 @@
+DEFAULT_ACTION = 'cancel'
+DEFAULT_MESSAGE = 'class CodedException'
+DEFAULT_ID = 522
+DEFAULT_INDEX = 0
+DEFAULT_CODE = 0
+DEFAULT_ONESHOT = 1
+DEFAULT_LEVEL = 3
+DEFAULT_PERSISTENT = 0
+DEFAULT_PROACTIVE_REPORT = 1
+
+class CodedException(Exception):
+    default_action = DEFAULT_ACTION
+    default_id = DEFAULT_ID
+    ...
+    def __init__(self, message, action, id, index, code, oneshot, level,
+                 is_persistent, proactive_report): ...
+    def to_dict(self) -> dict: ...
+    def structured_code(self) -> str: ...
+    def basic_structured_code(self) -> str: ...
+    @classmethod
+    def from_exception(cls, exc: Exception, **kwargs): ...
```

</details>

---

# exception_manager.py

## Summary
A fork-exclusive Klipper module that provides a centralised, structured error-reporting bus between the klippy host process and the Moonraker API layer. `ExceptionManager` maintains an in-memory list of active exceptions (keyed by `id`, `index`, `code` triples), optionally persists them to `exception_persistent.json` in the Snapmaker config directory, and forwards them to Moonraker via `webhooks.call_remote_method('raise_exception', ...)`. It also registers four G-code commands (`RAISE_EXCEPTION`, `CLEAR_EXCEPTION`, `QUERY_EXCEPTION`, `RM_EXCEPTION_PERSISTENT_FILE`) for manual inspection and testing. The module has no upstream counterpart; it is the back-end that `klippy.py`'s `raise_structured_code_exception` and `raise_coded_exception` helpers delegate to.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No structured exception bus exists | `ExceptionManager` bridges klippy exceptions to Moonraker via `webhooks.call_remote_method` | Allows the UI to display user-friendly error codes without parsing log strings |
| Errors are not persisted across restarts | Non-oneshot exceptions with `is_persistent=1` are written to `exception_persistent.json` and replayed on startup | Preserves error state (e.g. power-loss events) through firmware restarts |
| N/A | `ExceptionList` class enumerates all Snapmaker module IDs (522–2052) and error codes | Provides a single source of truth for the numeric error taxonomy |

## Additions
- `ExceptionList` class — module-ID and error-code constants:
  - `MODULE_ID_MOTION=522`, `MODULE_ID_TOOLHEAD=523`, `MODULE_ID_CAMERA=524`, `MODULE_ID_FEEDING=525`, `MODULE_ID_HEATER_BED=526`, `MODULE_ID_CAVITY=527`, `MODULE_ID_HOMING=528`, `MODULE_ID_GCODE=529`, `MODULE_ID_PROBE_OR_CALIBRATION=530`, `MODULE_ID_PRINT_FILE=531`, `MODULE_ID_DEFECT_DETECTION=532`, `MODULE_ID_SYSTEM=2052`.
- `ExceptionManager` class:
  - `__init__` — loads persisted exceptions from `exception_persistent.json`, registers G-code commands, starts timers.
  - `_parse_structured_code(coded_string)` — static; parses `LLLL-IIII-NNNN-CCCC` → `dict`.
  - `_parse_basic_code(coded_string)` — static; parses `IIII-NNNN-CCCC` → `dict`.
  - `raise_exception_async(id, index, code, message, oneshot, level, is_persistent, action)` — queues an exception for delivery on the reactor thread.
  - `raise_exception(id, index, code, message, oneshot, level, is_persistent)` — delivers immediately; deduplicates non-oneshot exceptions; calls `webhooks.call_remote_method('raise_exception', ...)`.
  - `clear_exception(id, index, code, gcmd)` — removes from in-memory list, clears persistence, calls `webhooks.call_remote_method('clear_exception', ...)`.
  - `has_exception(id, index, code)` → bool.
  - `get_status(eventtime)` → `{'exceptions': [...]}` for Moonraker subscriptions.
  - `save_persistent_exception` / `clear_persistent_exception` / `remove_persistent_exceptions` — JSON file I/O via `queuefile`.
- G-code commands:
  - `RAISE_EXCEPTION ID=<n> INDEX=<n> CODE=<n> [ONESHOT=1] [LEVEL=3] [IS_PERSISTENT=0] [MSG=<text>]`
  - `CLEAR_EXCEPTION ID=<n> INDEX=<n> CODE=<n>`
  - `QUERY_EXCEPTION` — prints all active exceptions in `LLLL-IIII-NNNN-CCCC` format.
  - `RM_EXCEPTION_PERSISTENT_FILE` — clears all persisted exceptions.
- `add_early_printer_objects(printer)` — installs `ExceptionManager` at printer startup.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `allow_moonraker_throw` is set only after `webhooks.has_remote_method('raise_exception')` returns `True`. During the first ~1 second of startup, exceptions are silently dropped to Moonraker (but still logged).
- Persistence file path is derived from `printer.get_snapmaker_config_dir()` which is a fork-only method on `Printer`. This file will not be created in stock Klipper.
- The `_handle_async_exception` timer uses a 1 ms delay between queued exceptions; a storm of exceptions (e.g. ADC spam) will cause many timer callbacks.
- `clear_exception` always calls `clear_persistent_exception` even when the exception is not in `self.exceptions`, which results in a redundant file I/O path.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/exception_manager.py
@@ -0,0 +1,~230 @@
+# New file – no upstream equivalent
+class ExceptionList:
+    MODULE_ID_MOTION = 522
+    MODULE_ID_GCODE  = 529
+    ...
+
+class ExceptionManager:
+    def __init__(self, printer): ...
+    def raise_exception_async(...): ...
+    def raise_exception(...): ...
+    def clear_exception(...): ...
+    def get_status(eventtime): ...
+    # G-code: RAISE_EXCEPTION, CLEAR_EXCEPTION, QUERY_EXCEPTION,
+    #         RM_EXCEPTION_PERSISTENT_FILE
+
+def add_early_printer_objects(printer):
+    printer.add_object('exception_manager', ExceptionManager(printer))
```

</details>

---

# printer_device_scan.py

## Summary
A fork-exclusive utility script used during initial Snapmaker U1 machine setup to auto-detect and map physical MCU serial ports into `printer.cfg`. It scans USB devices for a CAN adapter (identified by the string `"Geschwister Schneider CAN adapter"`) to locate the main SoC MCU on `/dev/ttyS6`, and then probes `/dev/serial/by-id/` for up to four extruder MCUs identified by the `"usb-Klipper"` prefix. The results are written back into the relevant `[mcu]`/`[mcu E0]`–`[mcu E3]` sections of `printer.cfg`. The file contains substantial `TODO` comments indicating power-cycle and boot-pin sequencing that has not yet been implemented. It has no upstream equivalent and appears to be a standalone provisioning/factory-setup tool rather than a module loaded at runtime.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| N/A — no MCU auto-detection exists in upstream | `scan_mcu_device()` calls `lsusb` and `ls /dev/serial/by-id/` to locate up to 5 MCU serial ports | Automates printer setup for the U1's multi-MCU architecture (1 main + 4 extruder MCUs) |
| N/A | `update_printer_cfg()` reads and surgically rewrites `printer.cfg` to add/update `serial:` options | Avoids requiring manual config editing during provisioning |

## Additions
- `run_shell_command(command)` — thin wrapper around `subprocess.run`; returns `[returncode, stdout, stderr]`.
- `scan_mcu_device()` — detects up to 5 MCU serial paths and returns `[scan_count, main_mcu_path, e0_path, e1_path, e2_path, e3_path]`:
  - Main MCU: searches `lsusb` output for `SOC_MCU_STRING = "Geschwister Schneider CAN adapter"`; assigns `/dev/ttyS6`.
  - Extruder MCUs E0–E3: searches `/dev/serial/by-id/` for entries containing `EXTRUDER_MCU_STRING = "usb-Klipper"`.
- `update_printer_cfg(cfg_file_path, info_list, section_name_list, option)` — reads `printer.cfg` line-by-line, adding missing sections/options and updating out-of-date values for the `serial:` option in `[mcu]`, `[mcu E0]`, `[mcu E1]`, `[mcu E2]`, `[mcu E3]`.
- Module constants: `CFG_MCU_SECTION_NAME`, `SCAN_RESULT_MAP_INDEX`, `OPTION_NAME = 'serial'`.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- **Incomplete implementation**: boot-pin configuration and power-cycle sequencing are all stubbed out with `TODO` / `pass`. The current scan is passive (no hardware toggling), meaning it will only detect MCUs that are already powered and enumerated.
- Hardcodes `/dev/ttyS6` for the main MCU — this will silently produce a wrong path on any board where the SoC UART is mapped differently.
- `update_printer_cfg` uses a line-by-line text replacement strategy that may corrupt config files with unusual formatting or multi-line values.
- The file's `__main__` block calls `scan_mcu_device()` but the `update_printer_cfg` call is commented out, so running it directly makes no persistent change.
- Not loaded by any `[module]` section in the normal printer startup path; it is invoked externally during provisioning.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/printer_device_scan.py
@@ -0,0 +1,~110 @@
+# New file – no upstream equivalent
+SOC_MCU_STRING = "Geschwister Schneider CAN adapter"
+EXTRUDER_MCU_STRING = "usb-Klipper"
+
+def scan_mcu_device():
+    # scans lsusb + /dev/serial/by-id/ for up to 5 MCU serial ports
+    # TODO: power-cycle and boot-pin sequencing not yet implemented
+    ...
+
+def update_printer_cfg(cfg_file_path, info_list, section_name_list, option):
+    # surgically rewrites [mcu] / [mcu E0..E3] serial: options
+    ...
```

</details>

---

# queuefile.py

## Summary
A fork-exclusive module that provides a thread-safe, background-queue-based file I/O system for the klippy host process. All file writes, appends, and deletes are off-loaded to a single daemon thread (`QueueListener._bg_thread`) so that the reactor event loop is never blocked by disk I/O. The module supports both fire-and-forget async operations and synchronised blocking calls that integrate with the klippy reactor's `pause()` mechanism. Safe atomic writes use a `.tmp` rename pattern. The module is set up once in `klippy.py`'s `main()` via `setup_bg_file_operations()` and torn down via `clear_bg_file_operations()`. It is used extensively by `exception_manager.py` and indirectly by `klippy.py`'s `update_snapmaker_config_file()` to write JSON config and exception state.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| N/A — upstream does all file I/O synchronously on calling threads | Background thread with a `queue.Queue(maxsize=1000)` decouples file I/O from the reactor | Prevents disk latency from stalling the real-time print loop |
| N/A | Atomic safe-write via write-to-`.tmp` then `os.replace()` | Ensures config/exception files are never left in a half-written state on power loss |

## Additions
- `FileOperation` dataclass — encapsulates a single pending file operation (`op_type`, `filename`, `content`, `flush`, `sync`, `timeout`, `safe_write`, `timestamp`, `future`).
- `FileOperationException` / `FileOperationTimeout` — custom exception types.
- `QueueHandler` — puts `FileOperation` objects onto `bg_queue`; raises `FileOperationException` if the queue is full:
  - `write_file(filename, content, flush, safe_write)`
  - `delete_file(filename)`
  - `append_file(filename, content, flush, safe_write)`
- `QueueListener` — owns the background thread and queue:
  - `_bg_thread()` — consumer loop; processes operations in order.
  - `_process_operation(op)` — dispatches to write / delete / append logic; handles `.tmp` safe-write and directory creation.
  - `stop()` — sends `None` sentinel to terminate the background thread.
- Module-level singleton API:
  - `setup_bg_file_operations()` → `QueueListener` (creates singleton `MainQueueHandler`).
  - `clear_bg_file_operations()` — stops and destroys the singleton.
  - `async_write_file(filename, content, flush, safe_write)` — non-blocking write.
  - `async_delete_file(filename)` — non-blocking delete.
  - `async_append_file(filename, content, flush, safe_write)` — non-blocking append.
  - `sync_write_file(reactor, filename, content, flush, safe_write, timeout)` — blocking write; polls `op.future` via `reactor.pause()`.
  - `sync_delete_file(reactor, filename, timeout)` — blocking delete.
  - `sync_append_file(reactor, filename, content, flush, safe_write, timeout)` — blocking append.
- Constants: `QUEUE_SIZE=1000`, `QUEUE_TIMEOUT=1.0`, `DEFAULT_SYNC_TIMEOUT=30.0`.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `sync_write_file` and friends spin-poll `op.future.done()` with 10 ms `reactor.pause()` sleeps. Under heavy scheduler load this can block for longer than the 30 s `DEFAULT_SYNC_TIMEOUT`.
- If `bg_queue` fills to 1000 entries (e.g. from exception spam), new write requests raise `FileOperationException` and are dropped silently at the caller.
- `_process_operation` catches all exceptions generically (`except Exception`) and only surfaces them if `op.sync` is `True`; async failures are swallowed.
- `os.fsync` calls are commented out in the safe-write path, so "safe" writes are only atomic against process crashes, not power loss.
- `concurrent.futures.Future` is used for synchronisation but `op.future.cancel()` is never called; stale futures from timed-out operations may hold references.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/queuefile.py
@@ -0,0 +1,~200 @@
+# New file – no upstream equivalent
+class FileOperation: ...
+class QueueHandler:
+    def write_file / delete_file / append_file: ...
+class QueueListener:
+    def _bg_thread(self): ...
+    def _process_operation(self, op): ...  # safe_write via .tmp + os.replace
+
+def async_write_file / async_delete_file / async_append_file: ...
+def sync_write_file / sync_delete_file / sync_append_file: ...
```

</details>

---

# klippy.py

## Summary
`klippy.py` is the main host process entry point and the `Printer` class that wires together all subsystems. The fork has heavily extended this file to support Snapmaker U1's multi-MCU hardware architecture (1 main MCU + up to 4 extruder MCUs with independent power rails), the structured exception system, and various Snapmaker-specific operational concerns. Key additions include: hardware power rail control (`set_extruder_power`, `set_main_mcu_power`), a JSON config helper API (`load_snapmaker_config_file`, `update_snapmaker_config_file`), the structured exception dispatch bridge (`raise_structured_code_exception`, `raise_coded_exception`, `clear_structured_code_exception`), a JSON message extraction helper (`extract_encoded_message`, `extract_coded_message_field`), process-level real-time scheduling (`set_sched_fifo`), user switching (`switch_user_group`), and firmware version reporting from `/etc/FULLVERSION`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `Printer.__init__` registers `gcode` and `webhooks` for early init | Also registers `exception_manager` | Exception infrastructure must be available before other modules |
| On `klippy:connect` error: `_set_state(str(e) + message_restart)` | Wraps error in a JSON coded-message (`"0003-0522-0000-0003/0004"`) and calls `raise_structured_code_exception` | Feeds structured errors to the Moonraker error bus |
| On MCU shutdown error: `_set_state(msg)` | Wraps with `"0003-0522-0000-0005"` code; sends structured exception | Same |
| `klippy:ready` callbacks run inside `reactor.assert_no_pause()` | `assert_no_pause()` context manager removed; callbacks run unguarded | `assert_no_pause()` was removed from the fork's reactor |
| `invoke_shutdown` sets state and runs handlers in `assert_no_pause` | Adds per-MCU coded exceptions for "Timer too close", "Shutdown due to webhooks", "Shutdown due to M112"; notifies `virtual_sdcard` to record print state; emits `klippy:notify_mcu_shutdown` event | Rich error classification for UI |
| Startup reads `util.get_device_info()` and `util.get_linux_version()` | Both calls removed; version comes from `/etc/FULLVERSION` via `util.get_full_firmware_version()` | Snapmaker firmware ships a canonical version file |
| No CLI `--user` or `--factory` options | `-u/--user` (default `"lava"`) and `-f/--factory` flags added | Process must drop root to the `lava` user after binding hardware |
| Main process starts without RT priority | `set_sched_fifo()` sets `SCHED_FIFO` priority 10 after startup | Reduces jitter on the Snapmaker SoC |
| `queuefile` not initialised | `queuefile.setup_bg_file_operations()` called in `main()`, torn down in cleanup | Background file I/O for config and exception persistence |

## Additions

**`Printer` methods (new):**
- `get_config_dir()` — returns the directory of the active config file.
- `get_snapmaker_config_dir(dir_name="snapmaker")` — returns (creating if needed) a `snapmaker/` subdirectory of the config dir.
- `set_extruder_power(state, extruder=['all'])` — controls `HEAD_MCU_POWER` GPIO via `lava_io set` shell command; also sets `HEAD_MCU*_BOOT` lines.
- `set_main_mcu_power(state)` — controls `MAIN_MCU_POWER` GPIO via `lava_io set`.
- `check_extruder_config_permission()` — checks for `.allow_extruder_modification` marker file in config or USB disk.
- `is_valid_json_format(obj)` → bool.
- `load_snapmaker_config_file(path, default_config, format, create_if_not_exist)` — JSON config loader with defaults merging and `queuefile`-based creation.
- `update_snapmaker_config_file(path, config_info, default_config, format)` — atomic JSON config writer via `queuefile.async_write_file`.
- `extract_encoded_message(message)` — extracts the first `{...}` JSON object from a string.
- `extract_coded_message_field(input_data, field_name='msg')` — returns the `msg` field from an embedded JSON object, or the raw string if none.
- `raise_structured_code_exception(structured_code, message, oneshot, is_persistent, action)` — parses a `LLLL-IIII-NNNN-CCCC` code and calls `exception_manager.raise_exception_async`.
- `clear_structured_code_exception(structured_code)` — calls `exception_manager.clear_exception`.
- `clear_exception(id, index, code)` — direct delegation to `exception_manager`.
- `raise_coded_exception(exception, parse_coded_msg)` — extracts structured fields from a `CodedException` (with optional embedded JSON parsing) and dispatches to `exception_manager`.

**Module-level functions (new):**
- `set_sched_fifo()` — sets `SCHED_FIFO` priority 10 using `ctypes` and `libc.sched_setscheduler`.
- `switch_user_group(user_name)` — drops root to the named user via `os.setreuid`/`os.setregid`/`os.setgroups`.

**CLI options (new):**
- `-u/--user` (`default="lava"`) — user to switch to after startup.
- `-f/--factory` — enables factory mode (stored in `start_args['factory_mode']`).

## Removals / Overrides
- `start_args['device']` and `start_args['linux_version']` fields removed; `get_device_info()` and `get_linux_version()` no longer called.
- `reactor.assert_no_pause()` context manager removed from `klippy:ready` callback dispatch and `invoke_shutdown` handler dispatch.
- `klippy:analyze_shutdown` event removed from handler registration (replaced by direct exception dispatch in `invoke_shutdown`).

## Risks / Compatibility Notes
- `set_extruder_power` and `set_main_mcu_power` call `os.system("lava_io set ...")` — these will silently fail on any machine that does not have the `lava_io` binary on `PATH`.
- `switch_user_group` only works when Klipper starts as `root`. Running as a non-root user with `-u lava` will emit a warning and continue as-is.
- `set_sched_fifo()` requires `CAP_SYS_NICE`; on systems without it the call fails and logs a warning, with no fallback.
- Error codes `"0003-0522-0000-0003"` through `"0003-0522-0000-0005"` are hardcoded in `_connect`. If the exception taxonomy changes in `exception_manager.py`, these codes will be stale.
- Power-cycling MCUs in `invoke_shutdown` via `virtual_sdcard.force_record_pl_print_file_env` adds latency to the shutdown path on every MCU shutdown, not just power-loss events.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/klippy.py
+++ b/klippy/klippy.py
@@ -7,9 +7,11 @@
-import sys, os, gc, optparse, logging, time, collections, importlib
-import util, reactor, queuelogger, msgproto
-import gcode, configfile, pins, mcu, toolhead, webhooks
+import sys, os, gc, optparse, logging, time, collections, importlib, json, copy, re
+import pwd, grp
+import util, reactor, queuelogger, msgproto, queuefile
+import gcode, configfile, pins, mcu, toolhead, webhooks, exception_manager, \
+       coded_exception, printer_device_scan

 # New Printer methods: get_config_dir, set_extruder_power, set_main_mcu_power,
 # get_snapmaker_config_dir, check_extruder_config_permission,
 # load_snapmaker_config_file, update_snapmaker_config_file,
 # extract_encoded_message, extract_coded_message_field,
 # raise_structured_code_exception, clear_structured_code_exception,
 # clear_exception, raise_coded_exception

 # New module-level: set_sched_fifo, switch_user_group
 # New CLI: -u/--user, -f/--factory
```

</details>

---

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

---

# toolhead.py

## Summary
`toolhead.py` implements the `ToolHead` class that manages the motion planner (look-ahead queue, trapezoid queue, step generation). The fork's changes are substantial and reflect an older Klipper architecture: the upstream's `MotionQueuing` helper class is not used; instead, `ToolHead` directly owns trapq, flush timer, step generators, and all MCU coordination. The look-ahead queue algorithm returns to the older `max_smoothed_v2`/`smooth_delta_v2` velocity smoothing approach (upstream replaced this with the `minimum_cruise_ratio` / `mcr_pseudo_accel` algorithm). The fork also adds U1-specific features: configurable `max_logical_extruder_num` / `max_physical_extruder_num`, flow-calibration mode that disables junction smoothing, `SWITCH_OF_EXTENDED_EXTRUDER` G-code command, new `SET_MAX_Z_ACCEL` and `SET_MAX_Z_VELOCITY` commands, coded error messages for "Must home axis" and "Move out of range" errors, and an auto-activate-extruder callback on `klippy:ready`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `ToolHead` uses `MotionQueuing` for trapq, step gen, flush | Directly owns `trapq`, `flush_timer`, `step_generators`, `kin_flush_times` | Older architecture; `MotionQueuing` not present in fork |
| `LookAheadQueue` flushes and returns move list for external processing | `LookAheadQueue` calls `toolhead._process_moves()` directly on flush | Tighter coupling; removes the intermediate list |
| `LookAheadQueue.is_empty()` method | Removed; callers use `not self.lookahead.queue` directly | Minor simplification |
| `minimum_cruise_ratio` / `mcr_pseudo_accel` velocity smoothing | `max_accel_to_decel` / `max_smoothed_v2` / `smooth_delta_v2` smoothing | Older algorithm; `minimum_cruise_ratio` config key still accepted via migration |
| `Move.next_junction_v2` + `limit_next_junction_speed()` | Removed; replaced by `max_smoothed_v2` | Corresponds to the look-ahead algorithm reversion |
| `Move.calc_junction` uses multiple extra-axis results | Uses single `extruder.calc_junction` result | `extra_axes` list removed; single extruder only |
| `ToolHead.extra_axes` list supports multiple extra axes | `self.extruder` single reference; `add_extra_axis`, `remove_extra_axis`, `get_extra_axes` removed | Single-extruder simplification |
| `ToolHeadCommandHelper` separate class registers G-code commands | Commands registered directly in `ToolHead.__init__` | Merged; `ToolHeadCommandHelper` class removed |
| `LOOKAHEAD_FLUSH_TIME = 0.150` | `LOOKAHEAD_FLUSH_TIME = 0.250` | Larger flush window for slower MCU comms |
| `BUFFER_TIME_HIGH = 1.0` | `BUFFER_TIME_LOW = 1.0`, `BUFFER_TIME_HIGH = 2.0` | Larger buffer for multi-MCU latency |
| Drip mode uses `motion_queuing.drip_update_time` | `DripModeEndSignal` exception + `_update_drip_move_time` loop | Self-contained drip mode without `MotionQueuing` |
| `set_max_velocities()` separate method | Logic inlined into `cmd_SET_VELOCITY_LIMIT` | Simplification |
| `M204` calls `toolhead.set_max_velocities(None, accel, ...)` | Directly sets `self.max_accel` and calls `_calc_junction_deviation()` | Removes indirection |
| `get_status()` returns `extra_axes` dict | Removed from status response | `extra_axes` concept removed |
| Default modules loaded by `load_printer_objects`: includes `garbage_collection` | `garbage_collection` removed; `machine_state_manager` added | U1-specific module; upstream GC module not used |

## Additions
- Config keys (new): `max_logical_extruder_num` (int), `max_physical_extruder_num` (int).
- `Move.line` field — stores the print file line number for each move; passed to firmware via `queue_step` command.
- Structured error dispatch in `Move.move_error()` for `"Must home X/Y/Z axis first"` (codes `0003-0522-{0..2}-0012`) and `"Move out of range on X/Y/Z axis"` (codes `0003-0522-{0..2}-0013`).
- `ToolHead.is_calibrating_flow` flag — set by `flow_calibration:begin` / `flow_calibration:end` events; disables junction smoothing during flow calibration.
- `ToolHead.print_file_line` attribute — current G-code line number, stamped onto each move.
- `ToolHead.is_grab_complete` flag — tracks whether extruder grab/activate sequence completed.
- `ToolHead._handle_ready()` / `_extruder_auto_activate()` — on `klippy:ready`, schedules extruder auto-activation after 3 s.
- `ToolHead.register_step_generator(handler)` — registers a step-generation callback.
- `ToolHead.note_step_generation_scan_time(delay, old_delay)` — manages `kin_flush_delay`.
- `ToolHead.note_mcu_movequeue_activity(mq_time, set_step_gen_time)` — updates `need_flush_time` and kicks flush timer.
- `ToolHead._advance_flush_time(flush_time)` / `_advance_move_time(next_print_time)` — batched step generation.
- `ToolHead._process_moves(moves)` — replaces upstream's two-step lookahead flush + trapq injection.
- `ToolHead.set_accel(accel)` — sets `max_accel` and recomputes junction deviation; waits for moves to complete.
- `ToolHead.set_grab_complete(enable)` — sets `is_grab_complete` flag.
- `DripModeEndSignal` exception class.
- `_update_drip_move_time(next_print_time)` — drip mode pacing without `MotionQueuing`.
- G-code commands (new/moved):
  - `SWITCH_OF_EXTENDED_EXTRUDER INDEX=<n>` — activates a logical extruder above `max_physical_extruder_num`.
  - `SET_MAX_Z_ACCEL A=<accel>` — overrides `kin.max_z_accel` at runtime.
  - `SET_MAX_Z_VELOCITY V=<vel>` — overrides `kin.max_z_velocity` at runtime.
- Constants added: `BUFFER_TIME_LOW`, `BGFLUSH_LOW_TIME`, `BGFLUSH_BATCH_TIME`, `BGFLUSH_EXTRA_TIME`, `MIN_KIN_TIME`, `MOVE_BATCH_TIME`, `STEPCOMPRESS_FLUSH_TIME`, `SDS_CHECK_TIME`, `MOVE_HISTORY_EXPIRE`, `DRIP_SEGMENT_TIME`, `DRIP_TIME`.

## Removals / Overrides
- `ToolHeadCommandHelper` class — removed; commands merged into `ToolHead`.
- `ToolHead.add_extra_axis`, `remove_extra_axis`, `get_extra_axes` — removed.
- `ToolHead.extra_axes` list — replaced by `self.extruder`.
- `ToolHead.set_max_velocities()` — removed; logic inlined.
- `LookAheadQueue.is_empty()` — removed.
- `Move.next_junction_v2`, `Move.limit_next_junction_speed()`, `Move.max_mcr_start_v2`, `Move.mcr_delta_v2` — removed.
- `ToolHead.motion_queuing` — not used; `MotionQueuing` object not created.
- Default module `garbage_collection` — removed from auto-loaded list.

## Risks / Compatibility Notes
- The `max_smoothed_v2` look-ahead algorithm produces different (generally lower) junction velocities than the upstream `minimum_cruise_ratio` method. Print quality and speed may differ, particularly on short moves.
- `LOOKAHEAD_FLUSH_TIME` increased to 0.250 s means the planner holds more moves in the queue before flushing; this increases latency between the host and first step output.
- `SWITCH_OF_EXTENDED_EXTRUDER` requires `print_task_config` object to be present; if it is absent, the command raises an error.
- `_extruder_auto_activate()` runs 3 seconds after `klippy:ready` and silently calls `run_script("ACTIVATE_EXTRUDER ...")` — this could conflict with a print that starts immediately.
- `set_accel(accel)` calls `wait_moves()` which blocks the reactor; calling it frequently could stall the print loop.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/toolhead.py
+++ b/klippy/toolhead.py
 # Key structural changes:
 # - ToolHeadCommandHelper removed; commands merged into ToolHead
 # - LookAheadQueue: max_smoothed_v2 algorithm (older); calls _process_moves directly
 # - ToolHead: owns trapq, flush_timer, step_generators directly
 # - extra_axes list replaced by single self.extruder
 # - New: max_logical_extruder_num, max_physical_extruder_num config keys
 # - New G-code: SWITCH_OF_EXTENDED_EXTRUDER, SET_MAX_Z_ACCEL, SET_MAX_Z_VELOCITY
 # - DripModeEndSignal + _update_drip_move_time for self-contained drip mode
 # - is_calibrating_flow flag; flow_calibration events
 # - LOOKAHEAD_FLUSH_TIME: 0.150 -> 0.250; BUFFER_TIME_HIGH: 1.0 -> 2.0
```

</details>

---

# gcode.py

## Summary
`gcode.py` is the G-code parser and command dispatcher. The fork's changes fall into three areas: (1) `CommandError` now inherits from `CodedException` so all G-code errors carry structured error codes; (2) the command parsing and dispatch loop gains thread-local tracking to avoid duplicate exception reporting on nested calls; (3) several minor parsing fixes and one new G-code command (`SWITCH_OF_EXTENDED_EXTRUDER`) are wired through `toolhead`. Additionally, `Coord` is reverted from an upstream-2025 optimised subclass back to a plain `collections.namedtuple`, and the extended-command (`shlex`) regex and parsing are adjusted.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class CommandError(Exception)` | `class CommandError(CodedException)` | All G-code errors carry structured `id`/`code`/`level` |
| `Coord` is an optimised `tuple` subclass with `__slots__` and property accessors | `Coord = collections.namedtuple('Coord', ('x', 'y', 'z', 'e'))` | Reverted to an older simpler implementation |
| `_process_commands` calls handlers directly; a `gcode.command_error` propagates without coded dispatch | Wrapped in `try/finally` with thread-local `_thread_local.in_process_commands`; on error calls `printer.raise_coded_exception(e)` | Prevents duplicate exception reports for nested command calls |
| `get_value` / `get_float` / `get_int` raise plain `CommandError` | Raise `CommandError(..., id=529, code=N, level=3)` | Error codes 529-0 through 529-5 map to GCode module errors |
| Extended command regex: `args_r = re.compile('([A-Z_]+|[A-Z*])')` | Adds `/` to character class: `([A-Z_]+|[A-Z*/])` | Supports file-path parameters in extended commands |
| Command dispatch for `M117`/`M118` uses `' '.join` split then special-cases `M23` | Uses `cmd.startswith("M117 ")` check; dispatches to `cmd[:4]` | Simpler and removes M23 special-case |
| `klippy:analyze_shutdown` event handler `_handle_analyze_shutdown` | Renamed to `_dump_debug`; `klippy:analyze_shutdown` event removed | Fork removed the `analyze_shutdown` event |
| `register_event_handler` calls placed at end of `__init__` | Moved to earlier in `__init__` (before command registrations) | Ordering fix |
| `mux command` registration raises plain `config_error` | Raises `config_error` with embedded JSON coded string (`"0003-0529-0000-0007"`) | Structured error |
| `cmd_default` raises plain error for unknown mux value | Raises `gcmd.error(..., id=529, code=9, level=1)` | Structured error |

## Additions
- `from coded_exception import CodedException` import.
- `_thread_local = threading.local()` module-level thread-local for nested dispatch guard.
- `GCodeCommand.get_raw_command_parameters()` — fork reverts the 2025 upstream refactor; now handles `M117`/`M118` prefix stripping inline.
- `GCodeDispatch._process_commands()` — `is_top_level` guard using `_thread_local.in_process_commands` to suppress duplicate exception reporting.
- `extended_r` compiled regex on `GCodeDispatch` for extended command parsing (replaces `shlex`-only parsing).
- `GCodeDispatch.exception_manager` attribute initialised to `None` in `__init__`.

## Removals / Overrides
- `Coord` optimised tuple subclass (upstream 2025 addition) replaced with `namedtuple`.
- `import operator` replaced by `import threading`.
- `klippy:analyze_shutdown` handler registration removed from `GCodeDispatch.__init__`.
- Upstream 2025 improvements to `GCodeCommand.get_raw_command_parameters` (line-number skipping via slice arithmetic) reverted.
- `register_event_handler` for `klippy:ready` / `klippy:shutdown` moved earlier in `__init__`.

## Risks / Compatibility Notes
- `Coord` is now a `namedtuple`. Upstream 2025 code that uses `Coord.x`, `Coord.y`, `Coord.z`, `Coord.e` as attribute access still works. Code that relies on `Coord` being exactly a `tuple` subclass also works. However, the upstream `Coord.__new__` pads short tuples to length 4; the fork's `namedtuple` requires exactly 4 positional arguments.
- Thread-local `in_process_commands` is never cleaned up if `handler(gcmd)` raises a non-`self.error` exception (caught by the bare `except:` block that calls `invoke_shutdown`). The `finally` block ensures cleanup, so this is safe.
- Error codes `529-0` through `529-9` are hardcoded in `get_value`, `get_float`, `get_int`, `get_raw_command_parameters`, and `cmd_default`. If the GCode module ID changes in `exception_manager.py` (currently `MODULE_ID_GCODE=529`), these will be stale.
- The `M23` special-case in `cmd_default` was removed. If any caller sends `M23 filename`, it will now fall through to the default handler.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/gcode.py
+++ b/klippy/gcode.py
@@ -6 +6 @@
-import os, re, logging, collections, shlex, operator
+import os, re, logging, collections, shlex, threading
+from coded_exception import CodedException
+_thread_local = threading.local()

@@ -8 +12 @@
-class CommandError(Exception):
+class CommandError(CodedException):

@@ -11,11 +15 @@
-class Coord(tuple):
-    __slots__ = ()
-    ...
+Coord = collections.namedtuple('Coord', ('x', 'y', 'z', 'e'))

 # get_value/get_float/get_int: add id=529, code=N, level=3 to errors
 # _process_commands: wrap in try/finally with thread-local guard
 # cmd_default: M117/M118 dispatch simplified; mux error is coded
 # _handle_analyze_shutdown renamed to _dump_debug
```

</details>

---

# webhooks.py

## Summary
`webhooks.py` implements the Unix socket server that connects klippy to Moonraker. The fork's changes: (1) remove the optional `msgspec` fast JSON encoder/decoder in favour of always using the standard `json` module; (2) replace the `klippy:analyze_shutdown` event subscription with a simpler `klippy:shutdown` handler; (3) integrate the structured exception system (on API errors, extract the coded message field and call `printer.raise_coded_exception`); (4) add `has_remote_method(method)` for probing Moonraker capability; (5) remove the `reactor.assert_no_pause()` wrapper from the status-subscription dispatch loop.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Tries to `import msgspec` for fast JSON; falls back to `json` | Always uses `import json`; `msgspec` import removed | Simplification; `msgspec` not available on Snapmaker SoC |
| `WebhookServer` subscribes to `klippy:analyze_shutdown` → `_handle_analyze_shutdown(msg, details)` | Subscribes to `klippy:shutdown` → `_handle_shutdown()` (no arguments) | `analyze_shutdown` event removed from klippy.py |
| `_handle_analyze_shutdown` logs and sets shutdown message | `_handle_shutdown` performs the same function without `msg`/`details` args | Matches simplified event |
| API request error: `web_request.set_error(WebRequestError(str(e)))` | Also calls `printer.extract_coded_message_field(str(e))` and `printer.raise_coded_exception(e)` for non-`gcode/script` methods | Routes API errors to exception bus |
| Status subscription loop runs inside `reactor.assert_no_pause()` | `assert_no_pause()` removed; loop runs unguarded | `assert_no_pause()` removed from the fork's reactor |
| `send_buffer` built with `json_dumps(data) + b"\x03"` | Built with `json.dumps(data, ...).encode() + b"\x03"` | No `msgspec` |
| `json.loads(request, object_hook=json_loads_byteify)` | Same, but `json_loads_byteify` only defined for Python 2 (dead code in Python 3) | Python 2 compatibility code retained but irrelevant |

## Additions
- `WebhookServer.has_remote_method(method)` → `bool` — checks if `method` is registered in `_remote_methods`. Used by `ExceptionManager` to gate exception forwarding.
- `ClientConnection.exception_manager` attribute set to `self.printer.lookup_object('exception_manager', None)` in `_handle_ready`.

## Removals / Overrides
- `msgspec` optional import and `json_dumps`/`json_loads` wrappers removed.
- `klippy:analyze_shutdown` event handler registration removed.
- `reactor.assert_no_pause()` context removed from `_handle_subscriptions`.

## Risks / Compatibility Notes
- Removing `msgspec` reduces JSON serialisation throughput. On a heavily subscribed status feed, this could increase CPU load on the SoC.
- `raise_coded_exception` is called for every non-`gcode/script` API error, including benign user errors. This may generate spurious entries in the exception log.
- `_handle_shutdown` no longer receives the shutdown message or details dict; if these were needed for UI error display, that information is now only available via the coded exception system.
- The `json_loads_byteify` Python 2 compatibility code is still present but never executed under Python 3.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/webhooks.py
+++ b/klippy/webhooks.py
@@ -9,30 +8 @@
-try:
-    import msgspec
-    json_dumps = msgspec.json.encode
-    json_loads = msgspec.json.decode
-except ImportError:
-    import json
-    ...
+import logging, socket, os, sys, errno, json, collections

@@ -139 +127 @@
-    "klippy:analyze_shutdown", self._handle_analyze_shutdown)
+    "klippy:shutdown", self._handle_shutdown)

 # _handle_analyze_shutdown(msg, details) -> _handle_shutdown()
 # API error path: extract_coded_message_field + raise_coded_exception
 # has_remote_method(method) added
 # assert_no_pause() removed from _handle_subscriptions
```

</details>

---

# stepper.py

## Summary
`stepper.py` implements `MCU_stepper`, the low-level stepper motor driver that manages the `stepcompress` queue and iterative solver. The fork's changes align with the older architecture in the rest of the fork: `MotionQueuing`/`syncemitter` is replaced with direct `stepcompress` allocation; `MCU_stepper.__init__` takes a name string instead of a config object; `generate_steps()` is added as a combined check-active + step-generation callback; and the `config_stepper` MCU firmware command gains `type=%u index=%u` parameters for the power-loss recovery system. A module-level helper (`get_stepper_type_and_index`) maps stepper names to a `(type, index)` tuple that the MCU firmware stores alongside each `queue_step` message for recovery after power loss.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `MCU_stepper.__init__(config, step_pin_params, ...)` — takes full config object | `MCU_stepper.__init__(name, step_pin_params, ...)` — takes name string | Decouples stepper from config; matches older API |
| `self._name = config.get_name()` | `self._name = name` (passed in) | Same |
| Uses `motion_queuing.allocate_syncemitter(mcu, sname)` | Directly allocates via `ffi_lib.stepcompress_alloc(oid)` | `MotionQueuing` / `syncemitter` not present in fork |
| `_stepqueue = ffi_lib.syncemitter_get_stepcompress(syncemitter)` | `_stepqueue = ffi_lib.stepcompress_alloc(oid)` with `ffi_main.gc(...)` | Direct allocation |
| `mcu.register_stepqueue` not called | `self._mcu.register_stepqueue(self._stepqueue)` called in `__init__` | Registers with MCU for flushing |
| `ffi_lib.itersolve_set_stepper_kinematics(syncemitter, sk)` | `ffi_lib.itersolve_set_stepcompress(sk, stepqueue, step_dist)` | Different FFI function signature |
| `ffi_lib.syncemitter_queue_msg` for raw message queuing | `ffi_lib.stepcompress_queue_msg(stepqueue, data, len)` | Direct stepcompress API |
| `ffi_lib.itersolve_set_trapq(sk, tq, step_dist)` | `ffi_lib.itersolve_set_trapq(sk, tq)` — `step_dist` removed | Different FFI signature |
| `set_trapq()` method name | `set_stepper_kinematics()` with new call | Method rename on kinematics set |
| Step-both-edge: checks `STEPPER_STEP_BOTH_EDGE`, `STEPPER_BOTH_EDGE`, `STEPPER_OPTIMIZED_UNSTEP` constants | Only checks `STEPPER_BOTH_EDGE`; simpler logic | Older MCU firmware support |
| `MIN_BOTH_EDGE_DURATION = 0.000000500` / `MIN_OPTIMIZED_BOTH_EDGE_DURATION` | `MIN_BOTH_EDGE_DURATION = 0.000000200` | Tighter constraint for AT32 hardware |
| `MAX_STEPCOMPRESS_ERROR = 0.000025` constant | `mcu.get_max_stepper_error()` config-driven | Per-MCU configurable error |
| `config_stepper oid=%d pin=%s dir=%s step=%s ticks=%u` MCU command | Appends `type=%u index=%u` | Power-loss recovery: MCU stores stepper identity with each move |
| `queue_step oid=%c interval=%u count=%hu add=%hi` | `queue_step oid=%c interval=%u count=%hu add=%hi line=%u` | Stores print file line number for power-loss recovery |
| `_check_active` registered as a flush callback via `motion_queuing` | Replaced by `generate_steps(flush_time)` which combines active check + step generation | Self-contained step generation without `MotionQueuing` |
| `get_mcu_position(cmd_pos=None)` — optional arg | `get_mcu_position()` — no argument; always uses current commanded position | Simplification |
| Short name for thread: slices `'stepper'` prefix differently | `if short and self._name.startswith('stepper_'):` (adds underscore) | Fix for stepper name format |

## Additions
- `power_loss_need_save_steppers = ['stepper_x', 'stepper_y', 'stepper_z', 'extruder']` module constant.
- `get_stepper_type_and_index(stepper)` — maps a stepper name string to `(type_index, axis_index)` for power-loss data. Returns `(0xFF, 0xFF)` for unrecognised names.
- `MCU_stepper._stepper_type` and `_stepper_index` attributes — populated by `get_stepper_type_and_index`.
- `MCU_stepper.generate_steps(flush_time)` — combined active-check and step-generation method; replaces `_check_active` flush callback pattern.

## Removals / Overrides
- `MIN_OPTIMIZED_BOTH_EDGE_DURATION` and `MAX_STEPCOMPRESS_ERROR` constants removed.
- `MCU_stepper._syncemitter` — not allocated; `_stepqueue` directly allocated.
- `MCU_stepper.set_trapq()` — renamed/replaced by `set_stepper_kinematics()`.
- `MCU_stepper._check_active` / `_check_active` flush callback registration via `motion_queuing` — removed.
- `MCU_stepper.get_mcu_position(cmd_pos=None)` optional argument removed.
- `configfile.deprecate_mcu_code` call for `STEPPER_STEP_BOTH_EDGE` removed (that method was also removed from configfile).

## Risks / Compatibility Notes
- The `type=%u index=%u` addition to `config_stepper` MCU command requires matching firmware that understands these fields. Running this host software against stock Klipper firmware will produce a protocol error at config time.
- `queue_step` gains a `line=%u` field — same firmware requirement as above.
- `generate_steps` is called directly by `ToolHead._advance_flush_time` (registered via `register_step_generator`). If this callback raises, it propagates through the flush timer and could crash the reactor.
- `get_stepper_type_and_index` uses `startswith` matching; a stepper named `stepper_x1` will match `stepper_x` and return index `0` rather than `1` because the remaining suffix `"1"` is a digit after `"stepper_x"`.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/stepper.py
+++ b/klippy/stepper.py
@@ +11 @@
+power_loss_need_save_steppers = ['stepper_x', 'stepper_y', 'stepper_z', 'extruder']
+def get_stepper_type_and_index(stepper): ...

@@ -23,3 +36 @@
-MIN_BOTH_EDGE_DURATION = 0.000000500
-MIN_OPTIMIZED_BOTH_EDGE_DURATION = 0.000000150
-MAX_STEPCOMPRESS_ERROR = 0.000025
+MIN_BOTH_EDGE_DURATION = 0.000000200

 # MCU_stepper.__init__: name string instead of config; stepcompress_alloc directly
 # config_stepper: type=%u index=%u appended
 # queue_step: line=%u appended
 # generate_steps() replaces _check_active flush callback
```

</details>

---

# reactor.py

## Summary
`reactor.py` is the green-thread event loop at the heart of klippy. The fork tracks back to an older version of the reactor (circa Klipper 0.10/2020): `ReactorPreventPause` / `assert_no_pause()` / `verify_can_pause()` are removed; the `ReactorError` exception class is absent; the FD-tracking data structures are simplified; the `run()` loop no longer creates a new dispatch greenlet per iteration; and the `_cached_dispatch_greenlets` / `_prevent_pause_count` state is simplified. The `ReactorFileHandler` gains a `fileno()` method. The `select`-based and `poll`-based reactor variants both have their FD registration logic reworked to use `file_handler` objects directly (no integer FD dict lookup for the select variant). A minor bug introduced by the fork's `_dispatch_loop`: `self.write_fds` (typo, missing underscore) — though this was likely corrected in practice.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `ReactorPreventPause` context manager + `assert_no_pause()` / `verify_can_pause()` | Removed entirely | Simplification; code paths that called it were also changed |
| `ReactorError` exception class | Removed | Only used by `verify_can_pause()` |
| `run()` creates a new `ReactorGreenlet` on every iteration of `while self._process` | Creates exactly one `ReactorGreenlet`, switches to it once | Simpler lifecycle |
| `pause()` checks `_prevent_pause_count` before switching | Pause check removed | `_prevent_pause_count` removed |
| `_fds` dict keyed by integer FD for select variant | List-based read/write FD tracking directly on `file_handler` objects | No integer FD lookup needed |
| `_check_fds` dispatch method for select events | Inlined into `_dispatch_loop` with per-object callbacks | Removes indirection |
| `timer_handler.timer_is_running` flag set/unset around timer execution | Flag removed from timer dispatch | `timer_is_running` attribute removed |
| `_gc_checking` bool → `_check_gc` method | `_check_gc` is now the bool; GC logic inlined in `_check_timers` | Minor naming change |
| `ReactorGreenlet` pool: `_cached_dispatch_greenlets` | Renamed `_greenlets` | Minor rename |
| Poll variant: `_fds` dict keyed by integer FD | `_fds` dict keyed by `file_handler`; copy-on-write via `fds = self._fds.copy()` | Thread-safety attempt for concurrent registration |
| `register_fd` returns `file_handler` and stores `fd` in `self._fds[fd]` | select: uses list; poll: uses copy dict with `file_handler` key | Different tracking |

## Additions
- `ReactorFileHandler.fileno()` method — returns `self.fd`; makes file handlers directly usable as `select`/`poll` descriptors.

## Removals / Overrides
- `ReactorError` exception class — removed.
- `ReactorPreventPause` context manager class — removed.
- `Reactor.assert_no_pause()` — removed.
- `Reactor.verify_can_pause()` — removed.
- `Reactor._prevent_pause_count` attribute — removed.
- `ReactorTimer.timer_is_running` attribute — removed.
- `Reactor._check_fds` method — logic inlined into `_dispatch_loop`.
- `Reactor._check_gc` method — replaced by inline GC logic.
- `_cached_dispatch_greenlets` renamed to `_greenlets`.

## Risks / Compatibility Notes
- Any code that calls `reactor.assert_no_pause()` (e.g. as a context manager) will raise `AttributeError`. The fork removes all call sites in `klippy.py`, `webhooks.py`, and `toolhead.py`, but any extra module that calls it will break.
- `reactor.verify_can_pause()` is also gone; extras that probe for pause safety have no equivalent.
- The `self.write_fds` typo in `_dispatch_loop` (should be `self._write_fds`) was present in the diff reviewed; if not corrected in a later commit it would cause an `AttributeError` at runtime whenever write FDs are monitored.
- The single-greenlet `run()` loop means that if the dispatch greenlet exits unexpectedly, the reactor terminates rather than creating a new one. This may cause klippy to exit rather than recover on certain greenlet exceptions.
- Copy-on-write `_fds` dict in the poll variant adds allocation overhead on every `register_fd`/`unregister_fd` call.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/reactor.py
+++ b/klippy/reactor.py
@@ -13,3 -13 @@
-class ReactorError(Exception): pass
-
@@ -96,8 @@
-class ReactorPreventPause: ...
+# ReactorPreventPause removed

 # ReactorTimer: timer_is_running removed
 # Reactor: _prevent_pause_count, assert_no_pause, verify_can_pause removed
 # Reactor._gc_checking -> _check_gc (bool, inline)
 # run(): single greenlet instead of per-iteration new greenlet
 # _fds / _check_fds: simplified to direct file_handler lists
 # ReactorFileHandler.fileno() added
```

</details>

---

# configfile.py

## Summary
`configfile.py` handles loading, parsing, and saving `printer.cfg`. The fork merges what upstream splits into `ConfigFileReader`, `ConfigAutoSave`, and `ConfigValidate` into a single `PrinterConfig` class, adopts a custom `ConfigError` that inherits from both `CodedException` and `configparser.Error`, and simplifies the internal two-pass config loading path. The `deprecate()` helper signature is also simplified. Upstream's `deprecate_gcode()` and `deprecate_mcu_code()` methods are removed as the fork does not use them.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `error = configparser.Error` (plain exception) | `class ConfigError(CodedException, configparser.Error)` | Structured error routing through exception_manager |
| `ConfigFileReader` is a separate class; `ConfigAutoSave` and `ConfigValidate` are separate helpers | All merged into `PrinterConfig` as private methods | Simplification / reduced indirection |
| `deprecate(section, option, value, msg)` builds a detailed dict and deduplicates | Simplified: passes a pre-built `msg` string directly to `pconfig.deprecate(...)` | Reduced complexity |
| `load_main_config()` returns `(regular_fileconfig, autosave_fileconfig)` tuple | `read_main_config()` returns a single merged `ConfigWrapper` | Cleaner API |
| `check_unused_options` uses `ConfigValidate.check_unused(fileconfig)` | Inlined into `PrinterConfig.check_unused_options(config)` | Single-class design |
| `runtime_warning` deduplicates via `_add_deprecated` | `runtime_warning` appends to `self.runtime_warnings` directly, sets `self.status_warnings` | Simplified deduplication |
| `get_status` returns `settings`, `config`, `warnings` merged from three sub-objects | Returns `config` and `warnings` from `PrinterConfig` directly | Same data, simpler path |

## Additions
- `ConfigError` class — dual-inherits from `CodedException` and `configparser.Error`.
- `PrinterConfig._read_config_file(filename)` — reads and normalises line endings (moved from `ConfigFileReader`).
- `PrinterConfig._parse_config_buffer`, `_resolve_include`, `_parse_config`, `_build_config_wrapper`, `_build_config_string` — include-file resolution and config building moved from `ConfigFileReader` into `PrinterConfig`.
- `PrinterConfig.read_config(filename)` — reads an arbitrary config file into a `ConfigWrapper`.
- `PrinterConfig.read_main_config()` — replaces `load_main_config()`; now returns one `ConfigWrapper`.

## Removals / Overrides
- `ConfigFileReader` class — removed; its methods inlined into `PrinterConfig`.
- `ConfigAutoSave` class — removed; merged into `PrinterConfig`.
- `ConfigValidate` class — removed; merged into `PrinterConfig`.
- `PrinterConfig.deprecate_gcode(cmd, param, value, msg)` — removed.
- `PrinterConfig.deprecate_mcu_code(mcu, feature, msg)` — removed.
- `PrinterConfig._add_deprecated(data)` — removed; deduplication replaced with simpler list append.

## Risks / Compatibility Notes
- Any extra module calling `pconfig.deprecate_gcode(...)` or `pconfig.deprecate_mcu_code(...)` will raise `AttributeError`.
- `ConfigError` now inherits from `CodedException` with default `id=522`. All config errors will appear in the Moonraker exception bus with the Motion module ID unless overridden.
- The single-pass `read_main_config()` return value changed from a tuple to a single object; any code that unpacks `(regular_fileconfig, autosave_fileconfig)` from `load_main_config()` will break (not an issue in the fork which already uses the new API).
- `status_settings` dict still populated via `_build_status`; format compatible with upstream Moonraker's `configfile.settings` subscription.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/configfile.py
+++ b/klippy/configfile.py
@@ -8,2 +9 @@
-error = configparser.Error
+class ConfigError(CodedException, configparser.Error):
+    pass
+error = ConfigError

 # ConfigFileReader, ConfigAutoSave, ConfigValidate classes removed;
 # their methods merged into PrinterConfig.

 # deprecate_gcode() and deprecate_mcu_code() removed from PrinterConfig.
```

</details>

---

# serialhdl.py

## Summary
`serialhdl.py` manages the low-level serial/CAN communication with MCUs. The fork's changes focus on two areas: (1) the `SerialReader` constructor is redesigned to accept a `mcu` back-reference instead of deriving state from `mcu_name`, enabling richer error reporting; (2) the "Timer too close" and "Power loss info saved" MCU notification messages are intercepted in `_handle_unexpected_error` to translate them into structured exception codes and log system-time estimates alongside the raw clock values.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `SerialReader.__init__(reactor, mcu_name="")` — name string | `SerialReader.__init__(reactor, warn_prefix="", mcu=None)` — explicit `mcu` object reference | Enables back-references to `mcu.estimate_clock_systime()` and `mcu.clock32_to_clock64()` |
| `warn_prefix` computed from `mcu_name` inside `__init__` | `warn_prefix` passed directly as parameter | Caller responsibility |
| `sq_name` (thread name) derived from `mcu_name` and passed to `serialqueue_alloc` | `sq_name` removed; `serialqueue_alloc` called without it | Matching older FFI signature |
| Debug log for sent messages: `"Sent %d %f %f %d: %s"` (receive_time, sent_time, len) | `"Sent %d %f %f min_t=%f req_t=%f %d: %s"` — adds system-time estimates for `min_clock` and `req_clock` | Aids diagnosis of "Timer too close" errors |
| `_handle_unexpected_error` handles MCU `output` messages generically | Additional logic: if message starts with `"Timer too close: "`, parses `waketime` and `timer_read_time`, converts to system time, logs them | Translates MCU clock ticks to wall-clock times |
| No "Power loss info saved" intercept | If `msg == "Power loss info saved"`, raises a coded exception `"0003-0522-{mcu_index}-0017"` | Routes power-loss notification through exception bus |
| `CommandQueryWrapper.get_response(..., retry=True)` — optional retry | `retry` parameter removed; always retries | Consistent with mcu.py change |

## Additions
- `clock_to_systime(clock)` local function inside `_log_sequence` — converts a 64-bit MCU clock to estimated system time using `self._mcu.estimate_clock_systime(clock)`.
- `_handle_unexpected_error`: "Timer too close" parsing block — extracts `waketime` and `timer_read_time` from the message, converts to 64-bit clocks via `mcu.clock32_to_clock64`, then to system times, and logs them.
- `_handle_unexpected_error`: "Power loss info saved" intercept — maps `mcu._name` to a 0–4 index and raises coded exception `"0003-0522-{index}-0017"` via `mcu.get_printer().raise_structured_code_exception(...)`.

## Removals / Overrides
- `mcu_name` constructor parameter — replaced by `warn_prefix` + `mcu`.
- `sq_name` internal attribute and its use in `serialqueue_alloc` calls — removed.
- Thread naming via `self.ffi_lib.set_thread_name(name_short.encode())` removed.
- `get_response(..., retry=True)` `retry` parameter removed.

## Risks / Compatibility Notes
- Any caller that previously passed `mcu_name=` as a keyword argument to `SerialReader.__init__` will raise `TypeError`. The only caller is `MCU.__init__` in `mcu.py`, which was updated accordingly.
- The "Timer too close" parser uses `dict(item.split('=', 1) for item in content.split(','))` — any variation in the MCU's message format (e.g. extra spaces) will silently skip the enriched log.
- The "Power loss info saved" coded exception uses a hardcoded dict `{'mcu': 0, 'e0': 1, 'e1': 2, 'e2': 3, 'e3': 4}` to map MCU name to index. MCUs with names outside this set get `mcu_index=255`, which produces code `"0003-0522-0255-0017"`.
- Removing `sq_name` from `serialqueue_alloc` requires matching C-side FFI (`serialqueue_alloc` must no longer expect a name argument).

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/serialhdl.py
+++ b/klippy/serialhdl.py
@@ -15 +15 @@
-    def __init__(self, reactor, mcu_name=""):
+    def __init__(self, reactor, warn_prefix="", mcu=None):

 # sq_name derived and passed to serialqueue_alloc removed
 # _log_sequence: min_t/req_t system-time added to "Sent" line
 # _handle_unexpected_error:
 #   "Timer too close:" -> parse + log system times
 #   "Power loss info saved" -> raise coded exception 0003-0522-N-0017
 # get_response: retry param removed
```

</details>

---

# pins.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#pinspy) for the full analysis of this file.

**Summary of changes:**
- `pins.error` now inherits from `CodedException` instead of `Exception`.

---

# util.py

## Summary
`util.py` provides miscellaneous host-side utilities (version detection, CPU info, build info). The fork's key change is to replace `get_version_from_file()` with `get_full_firmware_version()` which reads `/etc/FULLVERSION` — a Snapmaker-specific file that contains the complete firmware version string. Three helper functions (`_try_read_file`, `get_device_info`, `get_linux_version`) are removed, and several file-read calls are inlined as `try/except` blocks. The rest of the version/build utilities are unchanged.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `_try_read_file(filename, maxsize)` utility for safe reads | Removed; replaced by inline `try/except open(...)` blocks at each call site | Minor refactoring |
| `get_device_info()` reads `/proc/device-tree/model` or `/sys/class/dmi/id/product_name` | Function removed; `start_args['device']` key not set | Not needed on Snapmaker hardware |
| `get_linux_version()` reads `/proc/version` | Function removed | Not logged in startup |
| `git_info["version"] = get_version_from_file(klippy_src)` | `git_info["version"] = get_full_firmware_version()` | Use Snapmaker firmware version |
| No `/etc/FULLVERSION` support | `get_full_firmware_version()` reads `/etc/FULLVERSION`, logs it, falls back to `"?"` | Snapmaker firmware ships a canonical version |

## Additions
- `get_full_firmware_version()` — reads `/etc/FULLVERSION` and returns its content; logs on success, logs error on failure, returns `"?"` on any exception.

## Removals / Overrides
- `_try_read_file(filename, maxsize=32*1024)` — removed; call sites use inline try/except.
- `get_device_info()` — removed.
- `get_linux_version()` — removed.

## Risks / Compatibility Notes
- `get_full_firmware_version()` returns `"?"` on any machine that does not have `/etc/FULLVERSION`. Moonraker and the UI will show `"?"` as the firmware version in those environments.
- `get_device_info()` and `get_linux_version()` are no longer called from `klippy.py`; removing them here is safe but breaks any external code that imports and calls them.
- Inline file-read blocks do not enforce the 32 KiB `maxsize` that `_try_read_file` used for `/proc/cpuinfo`. On systems with very large `/proc/cpuinfo`, this reads the entire file into memory.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/util.py
+++ b/klippy/util.py
@@ -54,9 -54 @@
-def _try_read_file(filename, maxsize=32*1024):
-    try:
-        with open(filename, 'r') as f:
-            return f.read(maxsize)
-    except (IOError, OSError) as e:
-        ...
-        return None

@@ -126,14 @@
-def get_device_info():
-    ...
-def get_linux_version():
-    ...

@@ -235 +225 @@
-    git_info["version"] = get_version_from_file(klippy_src)
+    git_info["version"] = get_full_firmware_version()
+
+def get_full_firmware_version():
+    try:
+        with open("/etc/FULLVERSION", "r") as f:
+            fullver = f.read().strip()
+        logging.info("Full firmware version: %s", fullver)
+        return fullver
+    except Exception as e:
+        logging.error("Error getting full firmware version: %s", e)
+    return "?"
```

</details>

---

# Minor Core Changes (pins.py, mathutil.py, queuelogger.py, msgproto.py)

Upstream files with small diffs (fewer than ~20 substantive lines changed) are batched here.

---

## pins.py

### Summary
The only change is that `pins.error` now inherits from `CodedException` (via `from coded_exception import CodedException`) instead of the plain `Exception`. This makes all pin-configuration errors structurally typed so they can be routed through the `exception_manager`.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class error(Exception)` | `class error(CodedException)` | Uniform structured error reporting |

### Additions
- `from coded_exception import CodedException` import.

### Removals / Overrides
- None.

### Risks / Compatibility Notes
- Any code catching `pins.error` by type still works. Code catching bare `Exception` also still works. However, `isinstance(e, CodedException)` will now be `True` for pin errors.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/pins.py
+++ b/klippy/pins.py
@@ -6,0 +7 @@
+from coded_exception import CodedException
@@ -8 +9 @@
-class error(Exception):
+class error(CodedException):
```

</details>

---

## mathutil.py

### Summary
Two 3×3 matrix helper functions (`matrix_det` and `matrix_inv`) that exist in upstream Klipper have been removed from the fork. No new code was added to replace them. All other vector/matrix utilities (`matrix_cross`, `matrix_dot`, `matrix_mul`) remain. The removal is likely a code-cleanliness decision: none of the Snapmaker-specific extras modules use these functions.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `matrix_det(a)` computes 3×3 determinant | Function removed | Not used by any Snapmaker module |
| `matrix_inv(a)` computes 3×3 inverse using cofactors | Function removed | Not used by any Snapmaker module |

### Additions
- None.

### Removals / Overrides
- `matrix_det(a)` — upstream function removed.
- `matrix_inv(a)` — upstream function removed.

### Risks / Compatibility Notes
- Any extra module that calls `mathutil.matrix_det` or `mathutil.matrix_inv` will raise `AttributeError` at runtime. Stock Klipper extras that use these (e.g. certain bed-levelling helpers) would be broken if ported without re-adding the functions.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/mathutil.py
+++ b/klippy/mathutil.py
@@ -138,15 +137,0 @@
-######################################################################
-# Matrix helper functions for 3x3 matrices
-######################################################################
-
-def matrix_det(a):
-    x0, x1, x2 = a
-    return matrix_dot(x0, matrix_cross(x1, x2))
-
-def matrix_inv(a):
-    x0, x1, x2 = a
-    inv_det = 1. / matrix_det(a)
-    return [matrix_mul(matrix_cross(x1, x2), inv_det),
-            matrix_mul(matrix_cross(x2, x0), inv_det),
-            matrix_mul(matrix_cross(x0, x1), inv_det)]
```

</details>

---

## queuelogger.py

### Summary
The log rotation strategy has been changed from time-based (`TimedRotatingFileHandler` rotating at midnight, keeping 5 files) to size-based (`RotatingFileHandler` rotating at 10 MiB, keeping 15 files). Additionally, a custom `MillisecondFormatter` has been added to include milliseconds in every log timestamp (`HH:MM:SS.mmm`). The `setup_bg_logging` function now accepts a `maxBytes` parameter. These changes are consistent with an embedded system where wall-clock time may be unreliable but log verbosity is high.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `TimedRotatingFileHandler` rotates at midnight, keeps 5 backups | `RotatingFileHandler` rotates at 10 MiB, keeps 15 backups | Size-based rotation is more predictable on embedded systems |
| Timestamps use default `logging.Formatter` (no milliseconds) | `MillisecondFormatter` appends `.mmm` to every timestamp | Millisecond precision aids debugging of real-time events |
| `setup_bg_logging(filename, debuglevel)` | `setup_bg_logging(filename, debuglevel, maxBytes=FILE_SIZE)` | Allows caller to override log file size limit |

### Additions
- `FILE_SIZE = 10 * 1024 * 1024` (10 MiB) and `FILE_COUNT = 15` constants.
- `MillisecondFormatter` class — overrides `formatTime` to produce `HH:MM:SS.mmm` timestamps.

### Removals / Overrides
- `TimedRotatingFileHandler` base class replaced by `RotatingFileHandler`.
- `doRollover` still overridden but now calls `RotatingFileHandler.doRollover`.

### Risks / Compatibility Notes
- Log files no longer rotate at midnight; a long-running print could produce a single large file up to 10 MiB before rotation.
- 15 backups × 10 MiB = up to 150 MiB of log storage. On a memory-constrained device this could be significant.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/queuelogger.py
+++ b/klippy/queuelogger.py
@@ -7,0 +8,13 @@
+FILE_SIZE  = 10 * 1024 * 1024
+FILE_COUNT = 15
+
+class MillisecondFormatter(logging.Formatter):
+    def formatTime(self, record, datefmt=None):
+        ...
+        return "%s.%03d" % (s, (record.msecs % 1000))
+
@@ -24,4 +37,7 @@
-class QueueListener(logging.handlers.TimedRotatingFileHandler):
-    def __init__(self, filename):
-        logging.handlers.TimedRotatingFileHandler.__init__(
-            self, filename, when='midnight', backupCount=5)
+class QueueListener(logging.handlers.RotatingFileHandler):
+    def __init__(self, filename, maxBytes=FILE_SIZE, backupCount=FILE_COUNT):
+        logging.handlers.RotatingFileHandler.__init__(
+            self, filename, maxBytes=maxBytes, backupCount=backupCount)
+        formatter = MillisecondFormatter("%(asctime)s:%(message)s")
+        self.setFormatter(formatter)
```

</details>

---

## msgproto.py

### Summary
Two changes: (1) `msgproto.error` now inherits from `CodedException` instead of `Exception`, consistent with `pins.error` and `gcode.CommandError`; (2) the `create_dummy_response` method on `MessageParser` has been removed entirely; (3) a minor fix changes an empty-list return (`return []`) to an empty-string return (`return ""`) in the command-argument encoding path. The `create_dummy_response` removal is related to the removal of `DummyResponse` in `mcu.py`—the fork no longer supports the file-output debugging mode that used it.

### Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `class error(Exception)` | `class error(CodedException)` | Uniform structured error reporting |
| `MessageParser.create_dummy_response(msgname, params)` exists | Method removed | `DummyResponse` in `mcu.py` was also removed; file-output debug mode not supported |
| Command argument encoding returns `[]` on empty | Returns `""` | Likely a downstream consumers fix |

### Additions
- `from coded_exception import CodedException` import.

### Removals / Overrides
- `MessageParser.create_dummy_response(msgname, params={})` — 20-line method removed.

### Risks / Compatibility Notes
- Any code that calls `msgparser.create_dummy_response()` will raise `AttributeError`. This only mattered for the `DummyResponse` class in `mcu.py` which is also gone.

### Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/msgproto.py
+++ b/klippy/msgproto.py
@@ -6,0 +7 @@
+from coded_exception import CodedException
@@ -26 +27 @@
-class error(Exception):
+class error(CodedException):
@@ -327 +328 @@
-            return []
+            return ""
@@ -356,20 +356,0 @@
-    def create_dummy_response(self, msgname, params={}):
-        ...
```

</details>

---

# mathutil.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#mathutispy) for the full analysis of this file.

**Summary of changes:**
- `matrix_det(a)` and `matrix_inv(a)` removed. All other math utilities unchanged.

---

# msgproto.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#msgprotospy) for the full analysis of this file.

**Summary of changes:**
- `error` now inherits from `CodedException` instead of `Exception`.
- `MessageParser.create_dummy_response()` removed.
- Empty argument encoding returns `""` instead of `[]`.

---

# queuelogger.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#queueloggerpy) for the full analysis of this file.

**Summary of changes:**
- Log rotation changed from time-based (`TimedRotatingFileHandler`, midnight, 5 backups) to size-based (`RotatingFileHandler`, 10 MiB, 15 backups).
- `MillisecondFormatter` added for `HH:MM:SS.mmm` timestamps.
- `setup_bg_logging` gains a `maxBytes` parameter.

---

# kinematics/extruder.py

## Summary
`extruder.py` implements Klipper's extruder kinematics and G-code interface. In the Snapmaker U1 fork this file has grown by ~1833 diff lines relative to upstream. The most significant additions are the `ExtruderSwitchRecorder` class (which tracks per-extruder switch, retry, and error counts in a persistent JSON file and exposes G-code commands for inspection and reset), a full park/pick subsystem for dual-extruder tool-change management (park position config options, park-detector integration, and six new G-code commands), and a set of custom exception classes used by the park/pick flow. The `DummyExtruder` class was also updated: its `check_move` and `calc_junction` signatures were simplified and a new `update_move_time` stub was added.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Copyright year: 2016–2025 | Copyright year: 2016–2022 | Fork was branched from an earlier upstream snapshot |
| `import stepper, chelper` only | Also imports `coded_exception`, `queuefile`, `os`, `json`, `copy` | Required by new persistence and exception subsystems |
| No extruder-switch tracking | `ExtruderSwitchRecorder` class persists switch/retry/error counts to JSON | Maintenance alerting and warranty tracking for Snapmaker hardware |
| No park/pick concept | Full park position config (`xy_park_position`, `y_idle_position`, `y_park_position`) + `park_detector` integration | Dual-carriage tool-change requires safe parking positions |
| `DummyExtruder.check_move(move, ea_index)` | `DummyExtruder.check_move(move)` — `ea_index` removed | Simplified move-check interface; `ea_index` concept dropped |
| `DummyExtruder.calc_junction` takes `ea_index` | `ea_index` parameter removed | Consistent with `check_move` simplification |
| `DummyExtruder.get_axis_gcode_id()` returns a value | Raises `command_error` instead | Prevents silent misuse of dummy extruder as a real axis |
| No `update_move_time` on `DummyExtruder` | `update_move_time(flush_time, clear_history_time)` stub added (no-op) | Interface parity required by the toolhead dispatcher |
| `load_config_prefix` only instantiates the extruder | Also creates `ExtruderSwitchRecorder` (for index 0) and validates `park_detector` config consistency across all extruders | Ensures recorder and detector are set up exactly once and consistently |

## Additions

- **Exception classes**: `ExtruderParkAction`, `ExtruderUnknownParkStatus`, `ExtruderPickAbnormal` — used by the park/pick state machine.
- **Constants**: `PARK_DETECTOR_LOOP_CHECK_INTERVAL = 0.1`, `PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10`, `MAX_ALLOWED_DIFFERENCE = 3.0`, `EXTRUDER_SWITCH_RECORDER = "extruder_switch_recorder.json"`, `STRUCTURED_CODE_LIST = []`.
- **`ExtruderSwitchRecorder` class**:
  - Tracks per-extruder switch, retry, and error counts.
  - Persists data to JSON in the printer's persistent config directory.
  - Supports data migration from a legacy path.
  - Periodic auto-save timer.
  - Maintenance threshold checking with structured exception codes (`0001-0523-0000-0037` family).
  - G-code commands: `GET_EXTRUDER_SWITCH_RECORDER`, `RESET_EXTRUDER_SWITCH_RECORDER`, `RESET_EXTRUDER_MAINTENANCE_COUNT`.
- **Park position management**:
  - Config options: `xy_park_position`, `y_idle_position`, `y_park_position`.
  - `park_detector` object integration for physical park/pick detection.
  - `active_binding_probe()` method.
  - `extruder_list` object registered with the printer for multi-extruder enumeration.
- **G-code commands**: `PICK_EXTRUDER`, `PARK_EXTRUDER`, `SET_PARK_POSITION`, `ENTER_PARK_POINT_MANUAL_CALIBRATION`, `EXIT_PARK_POINT_MANUAL_CALIBRATION`, `MOVE_TO_PARK_CALIBRATION_POINT`, `VERIFY_PARK_POSITION`.

## Removals / Overrides

- `ea_index` parameter removed from `DummyExtruder.check_move` and `DummyExtruder.calc_junction`.
- `DummyExtruder.get_axis_gcode_id()` no longer returns a value; replaced with a `command_error` raise.
- Upstream copyright year range truncated (cosmetic but signals divergence point).

## Risks / Compatibility Notes

- The simplified `check_move(move)` / `calc_junction` signatures are **incompatible** with any upstream code that passes `ea_index`; merging upstream changes to these methods will require manual reconciliation.
- `ExtruderSwitchRecorder` writes to the printer's persistent config directory; misconfiguration of that path will silently skip persistence.
- `PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10` and `MAX_ALLOWED_DIFFERENCE = 3.0` are hard-coded constants — they are not exposed as config options and cannot be tuned per-machine without a code change.
- The structured exception codes (`0001-0523-0000-0037`) are Snapmaker-specific and will not be understood by generic Klipper tooling.
- `park_detector` config consistency is validated at startup; a mismatch across extruder config sections will raise an error that may be confusing without Snapmaker documentation.
- This file has diverged substantially from upstream (1833 diff lines); rebasing onto a newer Klipper release will be a significant effort.

## Raw Diff

<details>
<summary>View Diff</summary>

```diff
3c3
< # Copyright (C) 2016-2025  Kevin O'Connor <kevin@koconnor.net>
---
> # Copyright (C) 2016-2022  Kevin O'Connor <kevin@koconnor.net>
7c7,239
< import stepper, chelper
---
> import stepper, chelper, coded_exception, queuefile
> import os, json, copy
>
> class ExtruderParkAction(Exception):
>     pass
>
> class ExtruderUnknownParkStatus(Exception):
>     pass
>
> class ExtruderPickAbnormal(Exception):
>     pass
>
> PARK_DETECTOR_LOOP_CHECK_INTERVAL = 0.1
> PARK_DETECTOR_MAX_EXCEPTION_COUNT = 10
> MAX_ALLOWED_DIFFERENCE = 3.0
> STRUCTURED_CODE_LIST = []
>
> EXTRUDER_SWITCH_RECORDER = "extruder_switch_recorder.json"
>
> class ExtruderSwitchRecorder:
>     def __init__(self, config):
>         self.printer = config.get_printer()
>         self.configfile = self.printer.lookup_object('configfile')
>         self._data = {}
>         self._save_timer = None
>         self._load()
>         self._register_commands()
>         self._schedule_save()
>     def _load(self):
>         # Load from persistent config dir; migrate from old path if needed
>         ...
>     def _schedule_save(self):
>         # Periodic JSON save via reactor timer
>         ...
>     def record_switch(self, extruder_index):
>         ...
>     def record_retry(self, extruder_index):
>         ...
>     def record_error(self, extruder_index):
>         ...
>     def check_maintenance_threshold(self, extruder_index):
>         # Raises coded_exception with code 0001-0523-0000-0037 if threshold exceeded
>         ...
>     def _register_commands(self):
>         gcode = self.printer.lookup_object('gcode')
>         gcode.register_command('GET_EXTRUDER_SWITCH_RECORDER', ...)
>         gcode.register_command('RESET_EXTRUDER_SWITCH_RECORDER', ...)
>         gcode.register_command('RESET_EXTRUDER_MAINTENANCE_COUNT', ...)
>
> # ... (extruder park/pick classes and config additions) ...
>
> # Park position config options added to PrinterExtruder.__init__:
> #   xy_park_position, y_idle_position, y_park_position
> # park_detector object looked up and integrated
> # active_binding_probe() method added
> # extruder_list registered with printer
>
> # New G-code commands registered:
> #   PICK_EXTRUDER, PARK_EXTRUDER, SET_PARK_POSITION,
> #   ENTER_PARK_POINT_MANUAL_CALIBRATION,
> #   EXIT_PARK_POINT_MANUAL_CALIBRATION,
> #   MOVE_TO_PARK_CALIBRATION_POINT, VERIFY_PARK_POSITION

295c1929,1931
<     def check_move(self, move, ea_index):
---
>     def update_move_time(self, flush_time, clear_history_time):
>         pass
>     def check_move(self, move):
```

</details>

---

# kinematics/idex_modes.py

## Summary
`idex_modes.py` implements the IDEX (Independent Dual EXtruder) carriage mode management — PRIMARY, COPY, and MIRROR motion modes — used by dual-carriage 3D printers. In the Snapmaker U1 fork this file has ~473 diff lines relative to upstream and represents a **deliberate API freeze at an older, simpler interface**: the fork manages exactly two carriages on a single axis, while upstream has been refactored into a generalized multi-axis / multi-carriage architecture. The fork removes the `INACTIVE` mode, simplifies the constructor to take two explicit rails and one axis, removes the named-carriage dict from status output, and strips out the `collections` and `logging` imports that the upstream redesign required.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Copyright year: 2023–2025 | Copyright year: 2023 | Fork branched before upstream's multi-axis redesign |
| `import collections, logging, math` | `import math` only | `collections`/`logging` only needed by upstream's complex stepper setup |
| `VALID_MODES = [INACTIVE, PRIMARY, COPY, MIRROR]` | `VALID_MODES = [PRIMARY, COPY, MIRROR]` | `INACTIVE` mode concept removed; carriages are always in an active mode |
| `DualCarriages.__init__(printer, primary_rails, dual_rails, axes, safe_dist)` | `DualCarriages.__init__(dc_config, rail_0, rail_1, axis)` | Fork's simpler two-rail, single-axis model |
| `_init_steppers` method with complex multi-rail kinematics setup | Method removed; fork uses simpler stepper registration | Not needed for single-axis dual-carriage |
| `get_axes()` returns list of managed axes | Removed; replaced by `get_rails()` returning a 2-tuple | Single-axis assumption makes `get_axes()` unnecessary |
| `get_primary_rail(axis)` takes an axis argument | `get_primary_rail()` takes no argument | Only one axis is managed |
| `get_dc_rail_wrapper(rail)` | Removed | Not needed in simplified architecture |
| `get_transform(axis)` | Removed | Transform concept not used |
| `is_active(dc_rail)` | Removed | Mode state tracked differently |
| `toggle_active_dc_rail(dc_rail)` takes a `dc_rail` object | Takes an integer index (0 or 1) | Simpler index-based API |
| `home(homing_state, axis)` takes an axis argument | `home(homing_state)` — no axis arg | Always homes the single managed axis |
| `get_status()` returns dict with named carriages sub-dict | Returns simpler dict with `carriage_0` / `carriage_1` keys at top level | Upstream named-carriage structure not implemented |
| `get_kin_range(axis)` | `get_kin_range(mode)` — takes mode instead of axis | Range depends on mode, not axis, in single-axis model |
| `DualCarriagesRail.__init__` with complex multi-rail params | Simpler `DualCarriagesRail.__init__(rail, axis, active)` | Matches the two-rail, single-axis model |

## Additions

- `get_rails()` — returns a 2-tuple of `DualCarriagesRail` objects (replacement for `get_axes()`).
- Integer-index API for `toggle_active_dc_rail(index)`.

## Removals / Overrides

- `INACTIVE` mode removed from `VALID_MODES`.
- `_init_steppers` method removed.
- `get_axes()` removed.
- `get_primary_rail(axis)` replaced by `get_primary_rail()`.
- `get_dc_rail_wrapper()`, `get_transform()`, `is_active()` removed.
- `home(homing_state, axis)` `axis` parameter removed.
- Named carriages dict removed from `get_status()` output.
- `get_kin_range(axis)` parameter changed to `mode`.
- `collections` and `logging` imports removed.

## Risks / Compatibility Notes

- This module is **API-incompatible** with current upstream `idex_modes.py`. Any kinematics file (`cartesian.py`, `hybrid_corexy.py`, etc.) that calls `get_axes()`, `get_primary_rail(axis)`, `home(state, axis)`, or passes an `INACTIVE` mode will need to be adapted — and indeed, the fork's versions of those kinematics files have been updated accordingly.
- The removal of `INACTIVE` mode means carriages cannot be logically deactivated through the mode system; if upstream adds features that depend on `INACTIVE`, they cannot be merged without re-adding the mode.
- `get_status()` output format differs from upstream; any macros or host software that parses the named carriages dict will break if run against this fork.
- Rebasing onto upstream's multi-axis redesign would require a full rewrite of this module.

## Raw Diff

<details>
<summary>View Diff</summary>

```diff
4c4
< # Copyright (C) 2023-2025  Dmitry Butyugin <dmbutyugin@google.com>
---
> # Copyright (C) 2023  Dmitry Butyugin <dmbutyugin@google.com>
7c7
< import collections, logging, math
---
> import math
16,43c16,20
< INACTIVE = 'INACTIVE'
< PRIMARY = 'PRIMARY'
< COPY = 'COPY'
< MIRROR = 'MIRROR'
<
< class DualCarriagesRail:
<     VALID_MODES = [INACTIVE, PRIMARY, COPY, MIRROR]
<     def __init__(self, printer, primary_rails, dual_rails, axes, safe_dist):
<         self._printer = printer
<         self._axes = axes
<         self._safe_dist = safe_dist
<         self._primary_rails = primary_rails
<         self._dual_rails = dual_rails
<         self._named_carriages = collections.OrderedDict()
<         ...
<     def _init_steppers(self):
<         # Complex per-axis stepper kinematics setup
<         ...
<     def get_axes(self):
<         return list(self._axes)
<     def get_primary_rail(self, axis):
<         ...
<     def get_dc_rail_wrapper(self, rail):
<         ...
<     def get_transform(self, axis):
<         ...
<     def is_active(self, dc_rail):
<         ...
<     def toggle_active_dc_rail(self, dc_rail):
<         ...
<     def home(self, homing_state, axis):
<         ...
<     def get_kin_range(self, axis):
<         ...
<     def get_status(self):
<         return {
<             'mode': self._mode,
<             'active_carriage': ...,
<             'carriages': self._named_carriages,
<         }
---
> PRIMARY = 'PRIMARY'
> COPY = 'COPY'
> MIRROR = 'MIRROR'
>
> class DualCarriagesRail:
>     VALID_MODES = [PRIMARY, COPY, MIRROR]
>     def __init__(self, dc_config, rail_0, rail_1, axis):
>         self._rail_0 = rail_0
>         self._rail_1 = rail_1
>         self._axis = axis
>         ...
>     def get_rails(self):
>         return (self._rail_0, self._rail_1)
>     def get_primary_rail(self):
>         ...
>     def toggle_active_dc_rail(self, index):
>         ...
>     def home(self, homing_state):
>         ...
>     def get_kin_range(self, mode):
>         ...
>     def get_status(self):
>         return {
>             'mode': self._mode,
>             'carriage_0': ...,
>             'carriage_1': ...,
>         }
```

</details>

---

# kinematics/ — Minor Changes (all files except extruder.py and idex_modes.py)

## Summary
A consistent set of small but cross-cutting changes has been applied to every kinematics file in the fork. The changes fall into four recurring themes: (1) a `toolhead.Coord` call-signature fix (positional args / splat instead of a list, plus explicit `e=0.`), (2) mandatory `register_step_generator` calls for each stepper so the toolhead scheduler knows about them, (3) replacement of `clear_homing_state` with per-axis `note_<axis>_not_homed` methods and a `_motor_off` event handler wired to `stepper_enable:motor_off`, and (4) use of integer axis indices everywhere instead of string names like `"xyz"`. Additionally, `corexy.py` gains an `ignore_check_move_limit` safety flag that the Snapmaker U1 uses during certain tool-change manoeuvres, and several files switch from `stepper.LookupRail` to `stepper.PrinterRail` and from `DualCarriages` direct construction to explicit `DualCarriagesRail` wrapper creation.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `toolhead.Coord([x, y, z])` — passes a list | `toolhead.Coord(*[x,y,z], e=0.)` or `toolhead.Coord(x, y, z, 0.)` — positional args + explicit `e` | Upstream changed `Coord` constructor; fork backports the call-site fix |
| Steppers not explicitly registered with scheduler | `toolhead.register_step_generator(s.get_step_gen())` called for each stepper | Required by the fork's toolhead dispatcher |
| `clear_homing_state()` resets all axes | Per-axis `note_z_not_homed()`, `note_x_not_homed()`, `note_y_not_homed()` methods; `_motor_off` handler resets only what the kinematic owns | Finer-grained homing state tracking |
| `stepper_enable:motor_off` event not handled | Each kinematics registers `_motor_off` callback that resets limits/homed state | Ensures limits are invalidated on motor disable |
| Homing loops iterate over string `"xyz"` | Loops iterate over integer indices `(0, 1, 2)` | Matches new homing-state API |
| `set_position([0,0,0], "")` | `set_position([0,0,0], ())` | Empty tuple instead of empty string for "no homed axes" |
| `homing_axes == "xyz"` | `tuple(homing_axes) == (0, 1, 2)` | Integer-index homing axes API |
| `stepper.LookupRail(...)` | `stepper.PrinterRail(...)` (deltesian, hybrid_corexy, hybrid_corexz, polar, rotary_delta) | `LookupRail` removed/renamed in the fork's stepper layer |
| `DualCarriages(dc_config, rail_0, rail_1, axis)` constructed directly | Explicit `DualCarriagesRail` wrappers created first, then passed in (cartesian, hybrid_corexy, hybrid_corexz) | Required by the fork's simplified `idex_modes.py` API |
| `dc_module.get_primary_rail(axis).get_rail()` called with axis arg | `dc_module.get_primary_rail().get_rail()` — no axis arg | Matches `idex_modes.py` `get_primary_rail()` signature change |
| `dc_module.home(homing_state, axis)` | `dc_module.home(homing_state)` — no axis arg | Matches `idex_modes.py` `home()` signature change |
| `corexy`: no move-limit bypass | `ignore_check_move_limit` flag; `set_ignore_check_move_limit(enable)` method; `check_move`/`check_endstops` skip limits when flag is set | Needed during Snapmaker U1 tool-change to allow out-of-bounds park moves |
| `corexy`: generic error `"Must home axis first"` | `"Must home X axis first"` / `"Must home Y axis first"` / `"Must home Z axis first"` | Clearer error messages |

## Additions

### cartesian.py (61 lines diff)
- `DualCarriagesRail` wrapper objects created before `DualCarriages` construction.
- `toolhead.register_step_generator` calls for each stepper.
- `stepper_enable:motor_off` → `_motor_off` handler (resets position limits).
- `_motor_off` method.

### corexy.py (62 lines diff)
- `ignore_check_move_limit` instance flag (default `False`).
- `set_ignore_check_move_limit(enable)` method.
- `note_z_not_homed()`, `note_x_not_homed()`, `note_y_not_homed()` methods.
- `_motor_off` method; `stepper_enable:motor_off` event registration.
- `register_step_generator` calls.
- Per-axis error messages in `check_move`.

### corexz.py (26 lines diff)
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### delta.py (27 lines diff)
- `register_step_generator` calls.
- `_motor_off` method (resets `limit_xy2` and `need_home`); `stepper_enable:motor_off` registration.

### deltesian.py (36 lines diff)
- `register_step_generator` calls.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### hybrid_corexy.py (57 lines diff)
- `DualCarriagesRail` wrappers before `DualCarriages` construction.
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### hybrid_corexz.py (57 lines diff)
- Identical additions to `hybrid_corexy.py`.

### none.py (7 lines diff)
- (No new methods added; changes are removals/fixes only.)

### polar.py (37 lines diff)
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### rotary_delta.py (39 lines diff)
- `register_step_generator` calls.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### winch.py (14 lines diff)
- `register_step_generator` calls.

## Removals / Overrides

- `clear_homing_state()` removed from all kinematics files (replaced by `_motor_off` and per-axis `note_<axis>_not_homed` methods).
- `none.py`: `clear_homing_state` stub removed; `Coord` list form removed.
- `delta.py`, `rotary_delta.py`: `homing_axes == "xyz"` string comparison removed.

## Risks / Compatibility Notes

- The `ignore_check_move_limit` flag in `corexy.py` **disables XY and Z move-limit detection** when set. If it is left enabled accidentally (e.g., after a failed tool-change), subsequent moves will not be bounds-checked, which could cause crashes. The fork must ensure this flag is always cleared after the manoeuvre that requires it.
- Replacing `clear_homing_state` with per-axis `note_<axis>_not_homed` means that if any kinematics file still calls `clear_homing_state` after a merge it will raise `AttributeError` at runtime.
- The `stepper.LookupRail` → `stepper.PrinterRail` change is load-bearing; if upstream renames `PrinterRail` or changes its constructor the affected files (deltesian, hybrid_*, polar, rotary_delta) will break.
- `register_step_generator` calls are required by the fork's toolhead; omitting them for any stepper (e.g., after adding a new stepper) will cause silent scheduling issues.
- Integer homing-axis indices are incompatible with any upstream code that still passes string names; merging upstream homing changes requires careful review.
- All changes are self-consistent within the fork but represent a significant divergence from upstream in every kinematics file, making future rebases labour-intensive.

## Raw Diff

<details>
<summary>View Diff — cartesian.py (representative excerpt)</summary>

```diff
# cartesian.py
-        self.axes_min = toolhead.Coord([rail.get_range()[0] for rail in rails] + [0.])
-        self.axes_max = toolhead.Coord([rail.get_range()[1] for rail in rails] + [0.])
+        self.axes_min = toolhead.Coord(*[rail.get_range()[0] for rail in rails], e=0.)
+        self.axes_max = toolhead.Coord(*[rail.get_range()[1] for rail in rails], e=0.)

-        dc = idex_modes.DualCarriages(dc_config, rail, dc_rail, axis)
+        dc_rail_0 = idex_modes.DualCarriagesRail(dc_config, rail, axis, True)
+        dc_rail_1 = idex_modes.DualCarriagesRail(dc_config, dc_rail, axis, False)
+        dc = idex_modes.DualCarriages(dc_config, dc_rail_0, dc_rail_1, axis)

+        for s in self.get_steppers():
+            toolhead.register_step_generator(s.get_step_gen())

+        self.printer.register_event_handler("stepper_enable:motor_off",
+                                            self._motor_off)

-            pos = dc_module.get_primary_rail(axis).get_rail().get_homing_info()
+            pos = dc_module.get_primary_rail().get_rail().get_homing_info()

-        dc_module.home(homing_state, axis)
+        dc_module.home(homing_state)

+    def _motor_off(self, print_time):
+        self.limits = [(1.0, -1.0)] * 3
```

</details>

<details>
<summary>View Diff — corexy.py (representative excerpt)</summary>

```diff
# corexy.py
+        self.ignore_check_move_limit = False
+        self.printer.register_event_handler("stepper_enable:motor_off",
+                                            self._motor_off)

+    def set_ignore_check_move_limit(self, enable):
+        self.ignore_check_move_limit = enable

     def check_move(self, move):
+        if not self.ignore_check_move_limit:
             limits = self.limits
             xpos, ypos = move.end_pos[:2]
             if (xpos < limits[0][0] or xpos > limits[0][1]
                 or ypos < limits[1][0] or ypos > limits[1][1]):
-                self._check_endstops(move)
+                self._check_endstops(move)  # only when limit checking enabled

-                raise self.printer.command_error("Must home axis first")
+                raise self.printer.command_error("Must home X axis first")

+    def note_x_not_homed(self):
+        self.limits[0] = (1., -1.)
+    def note_y_not_homed(self):
+        self.limits[1] = (1., -1.)
+    def note_z_not_homed(self):
+        self.limits[2] = (1., -1.)
+    def _motor_off(self, print_time):
+        self.limits = [(1.0, -1.0)] * 3
```

</details>

<details>
<summary>View Diff — delta.py / rotary_delta.py (representative excerpt)</summary>

```diff
# delta.py
-        self.set_position([0., 0., 0.], "")
+        self.set_position([0., 0., 0.], ())

-        if homing_axes == "xyz":
+        if tuple(homing_axes) == (0, 1, 2):

-    def clear_homing_state(self, axes):
-        ...
+    def _motor_off(self, print_time):
+        self.limit_xy2 = -1.
+        self.need_home = True
```

</details>

<details>
<summary>View Diff — deltesian.py / polar.py / rotary_delta.py (LookupRail → PrinterRail)</summary>

```diff
-        self.rails = [stepper.LookupRail(config, 'stepper_x'),
-                      stepper.LookupRail(config, 'stepper_y')]
+        self.rails = [stepper.PrinterRail(config.getsection('stepper_x')),
+                      stepper.PrinterRail(config.getsection('stepper_y'))]
```

</details>

<details>
<summary>View Diff — none.py</summary>

```diff
-        self.axes_min = toolhead.Coord((0., 0., 0.))
-        self.axes_max = toolhead.Coord((0., 0., 0.))
+        self.axes_min = toolhead.Coord(0., 0., 0., 0.)
+        self.axes_max = toolhead.Coord(0., 0., 0., 0.)

-    def clear_homing_state(self, axes):
-        pass
```

</details>

---

# klippy/chelper — C Helper Layer Changes

## Summary
The `chelper` directory contains the C extension library that Klipper compiles into `c_helper.so` for performance-critical path planning. The fork diverges from upstream in two key ways: it removes the newer `steppersync` refactor (reverting to the older `steppersync_alloc`/`flush` API) and drops `kin_generic.c`, while adding a standalone `Makefile` for cross-compilation targeting the U1's AArch64 host processor.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Uses `steppersync.c`/`steppersync.h` with `syncemitter`, `steppersyncmgr` API | Uses older `steppersync_alloc`/`steppersync_free`/`steppersync_flush` API inline in `stepcompress.c` | Fork is based on older Klipper; the steppersync refactor was not backported |
| Includes `kin_generic.c` (generic stepper kinematics) | No `kin_generic.c` | Generic kinematics module added to upstream after fork diverged |
| chelper compiled only via Python `__init__.py` build system | Fork-exclusive `Makefile` for cross-compilation with `CROSS_COMPILE=` override | Needed to produce `c_helper.so` for AArch64 U1 host without Python build env |
| `defs_steppersync` uses `syncemitter`/`steppersyncmgr` structs | Uses classic `steppersync_alloc(sq, sc_list, sc_num, move_num)` | API revert to match older `stepcompress.c` |
| `stepcompress_fill` takes `(sc, oid, max_error, ...)` | Takes `(sc, max_error, ...)` — no `oid` param | Signature regression from older code |
| `itersolve_get_gen_steps_count()` / window functions present | These functions absent | Upstream added performance monitoring; fork does not have them |

## Additions
- **`klippy/chelper/Makefile`** (fork-exclusive): Standalone GNU Makefile that compiles all chelper C sources directly. Key features:
  - `CROSS_COMPILE` variable to set AArch64 cross-compiler prefix
  - `PROJECT := Klippy chelper`, `TARGET := c_helper.so`
  - `V=1` verbose mode toggle
  - `clean` and `disclean` targets
  - Compiles exactly the same source list as `__init__.py`'s `SOURCE_FILES`

## Removals / Overrides
- `steppersync.c` and `steppersync.h` removed (upstream-only)
- `kin_generic.c` removed (upstream-only)
- `defs_steppersync` in `__init__.py` reverted to older API (no `syncemitter`, no `steppersyncmgr`)
- `check_build_c_library()` function differs — fork has simpler build path
- Most chelper `.c`/`.h` file differences are small downstream divergences from an earlier upstream snapshot (e.g. copyright dates, minor refactors that occurred after the fork point)

## Risks / Compatibility Notes
- Any plugin or klippy module using `steppersync` must use the old API — **incompatible with upstream `stepper.py`** which expects the new `steppersyncmgr` API
- The `Makefile` hard-codes the source file list; if new `.c` files are added to `__init__.py`, the `Makefile` must be updated manually
- Cross-compiled `c_helper.so` is AArch64 binary; cannot be used on x86 dev machines without recompiling

## Raw Diff
<details>
<summary>View Diff (chelper/__init__.py)</summary>

```diff
--- a/klippy/chelper/__init__.py
+++ b/klippy/chelper/__init__.py
@@ -17,16 +17,16 @@
 SOURCE_FILES = [
-    'pyhelper.c', 'serialqueue.c', 'stepcompress.c', 'steppersync.c',
-    'itersolve.c', 'trapq.c', 'pollreactor.c', 'msgblock.c', 'trdispatch.c',
+    'pyhelper.c', 'serialqueue.c', 'stepcompress.c', 'itersolve.c', 'trapq.c',
+    'pollreactor.c', 'msgblock.c', 'trdispatch.c',
     'kin_cartesian.c', 'kin_corexy.c', 'kin_corexz.c', 'kin_delta.c',
     'kin_deltesian.c', 'kin_polar.c', 'kin_rotary_delta.c', 'kin_winch.c',
-    'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c', 'kin_generic.c'
+    'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c',
 ]
 # defs_steppersync reverted from syncemitter/steppersyncmgr to classic API
-    struct syncemitter *steppersync_alloc_syncemitter(...)
-    int32_t steppersyncmgr_gen_steps(...)
+    struct steppersync *steppersync_alloc(struct serialqueue *sq,
+        struct stepcompress **sc_list, int sc_num, int move_num);
+    int steppersync_flush(struct steppersync *ss, uint64_t move_clock,
+        uint64_t clear_history_clock);
```
</details>

---

# src/stm32/at32f403a.c

## Summary
A fork-exclusive C source file providing board-level initialisation for the **Artery AT32F403A** microcontroller (an STM32F4-compatible 32-bit ARM Cortex-M4 MCU from Artery Technology). It sets up the system clock, configures the USB 48 MHz clock using either the internal RC oscillator (HICK) with ACC auto-calibration or the external crystal (HEXT) depending on the selected PLL multiplier, provides a debug UART on USART3 / PB10, and optionally configures GPIO remaps for UART5, CAN2, and SPI4. The file bridges the AT32 vendor SDK (`at32f403a_407.h`) into Klipper's firmware HAL layer (`sched.h`, `command.h`, `armcm_boot.h`).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32F403A support | `at32f403a_clock_setup()` called by `DECL_INIT` equivalent to set system clock and USB clock | Snapmaker U1 main SoC MCU uses AT32F403A |
| N/A | Debug UART on USART3/PB10 with optional `RESERVE_PINS_debug_uart_tx_pin` constant | Factory/debug logging on embedded hardware |

## Additions

**Functions:**
- `uart_debug_print_init(uint32_t baudrate)` — configures USART3/PB10 as a TX-only UART for debug output; enables clocks via `crm_periph_clock_enable`.
- `at32f403a_log(char* log)` — writes a NUL-terminated string byte-by-byte to USART3; used as a low-level print function.
- `PUTCHAR_PROTOTYPE` (`__io_putchar` or `fputc`) — retargets C `printf` to USART3.
- `usb_clock48m_select(usb_clk48_s clk_s)` — selects the USB 48 MHz source:
  - `USB_CLK_HICK` path: enables `CRM_ACC_PERIPH_CLOCK`, writes ACC calibration constants (`c1=7980`, `c2=8000`, `c3=8020`), enables HICK auto-trim.
  - `USB_CLK_HEXT` path: sets `CRM_USB_DIV_*` based on `SystemCoreClock` (48/72/96/120/144/168/192 MHz).
- `mcu_uart_gpio_remap()` — enables `UART5_GMUX_0001` remap (conditional on `CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9`).
- `mcu_can2_gpio_remap()` — enables `CAN2_GMUX_0001`.
- `mcu_spi4_gpio_remap()` — enables `SPI4_GMUX_0001`.
- `at32f403a_clock_setup()` — calls `system_clock_config()`, `usb_clock48m_select(USB_CLK_HICK)`, and enables the USB peripheral clock.

**Config constants:**
- `RESERVE_PINS_debug_uart_tx_pin = "PB10"` (if `CONFIG_AT32_ENABLE_DEBUG_USART`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `usb_clock48m_select(USB_CLK_HICK)` uses ACC auto-calibration with fixed C1/C2/C3 constants (7980/8000/8020). These are tuned for an 8 MHz HICK target; if the AT32F403A variant in the U1 has a different trim range, USB enumeration may fail.
- `at32f403a_log` blocks in a tight loop waiting for `USART_TDBE_FLAG`; calling this during time-critical ISR code will introduce latency.
- `PUTCHAR_PROTOTYPE` targets GCC `__io_putchar`; clang uses `fputc`. The `#if` guards handle this, but mixing toolchains requires care.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/at32f403a.c
@@ -0,0 +1,~160 @@
+// New file – AT32F403A board-level init
+void uart_debug_print_init(uint32_t baudrate);
+void at32f403a_log(char* log);
+static void usb_clock48m_select(usb_clk48_s clk_s);
+void mcu_uart_gpio_remap(void);
+void mcu_can2_gpio_remap(void);
+void mcu_spi4_gpio_remap(void);
+void at32f403a_clock_setup(void);  // called by DECL_INIT chain
```

</details>

---

# src/stm32/at32f415rc.c

## Summary
A fork-exclusive C source file providing board-level initialisation for the **Artery AT32F415RC** microcontroller (ARM Cortex-M4, 128 KB flash, USB OTG FS). This is the chip used on Snapmaker U1 extruder MCU boards (E0–E3). It configures the system clock via `system_clock_config()`, sets up USB OTG with the external crystal as the 48 MHz source, and provides a debug UART on USART3/PB10 (same pin as the AT32F403A). The file is structurally simpler than `at32f403a.c` because the AT32F415 uses a single USB clock divider path and has a built-in USB OTG peripheral (no external CAN bus clock mux needed).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32F415 support | Full clock and USB OTG init for AT32F415RC | Snapmaker U1 extruder MCU is AT32F415RC |
| N/A | Debug UART on USART3/PB10 | Factory/debug output on extruder boards |

## Additions

**Functions:**
- `uart_debug_print_init(uint32_t baudrate)` — configures USART3/PB10 as debug TX UART; uses `crm_periph_clock_enable` for CRM_USART3 and CRM_GPIOB clocks.
- `at32f415_log(char* log)` — byte-by-byte string write to USART3 (mirrors `at32f403a_log`).
- `usb_clock48m_select(usb_clk48_s clk_s)` — sets USB clock divider based on `system_core_clock` value (48/72/96/120/144 MHz → `CRM_USB_DIV_1` through `CRM_USB_DIV_3`).
- `at32f415rc_clock_setup()` — calls `system_clock_config()` only; called by Klipper's `DECL_INIT` equivalent.
- `at32f415rc_usbotg_clock_config()` — enables `OTG_CLOCK` (`crm_periph_clock_enable`) and calls `usb_clock48m_select(USB_CLK_HEXT)`.

**Config constants:**
- `RESERVE_PINS_debug_uart_tx_pin = "PB10"` (if `CONFIG_AT32_ENABLE_DEBUG_USART`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `usb_clock48m_select` uses `USB_CLK_HEXT` in `at32f415rc_usbotg_clock_config()` — requires a stable external crystal. If the crystal is absent or out of tolerance, USB enumeration will fail silently.
- Unlike the AT32F403A file, there is no ACC auto-calibration fallback; the AT32F415 does not support ACC for HEXT.
- The AT32F415RC has only 128 KB of flash. The `power_loss_check.c` file defines two 1 KB flash sectors at the top of this flash range (`0x0801F800`, `0x0801FC00`); any build that approaches 128 KB will corrupt the power-loss data.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/at32f415rc.c
@@ -0,0 +1,~100 @@
+// New file – AT32F415RC board-level init
+void uart_debug_print_init(uint32_t baudrate);
+void at32f415_log(char* log);
+void usb_clock48m_select(usb_clk48_s clk_s);
+void at32f415rc_clock_setup(void);
+void at32f415rc_usbotg_clock_config(void);
```

</details>

---

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

---

# src/stm32/power_loss_check.c

## Summary
A fork-exclusive MCU firmware module that detects power-supply brownout/loss events and saves the current stepper motor positions to on-chip flash so that a print can be resumed after power is restored. The module monitors a voltage-sense GPIO (PB8 on AT32F415, PB7 on AT32F403A) using a 10 kHz timer, applies duty-cycle-based debouncing to distinguish genuine power loss from noise, and when confirmed uses a dual-sector wear-levelling scheme (two 1 KB/2 KB flash sectors with alternating sequence numbers) to atomically write a `power_loss_env` record containing all registered stepper positions. On startup, `load_save_flash_info()` reads back the valid sector and makes the saved data available for query. The module also reports back to the host via `serialhdl`'s "Power loss info saved" notification which `serialhdl.py` in the klippy host intercepts.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No power-loss recovery at firmware level | Timer-driven GPIO monitoring + flash save on brownout | Snapmaker U1 requirement for print resume after power loss |
| N/A | Dual-sector wear-levelled flash storage with sequence numbers | Prevents data loss if a second power cut occurs during the flash write |
| N/A | `stepper.c` extended with `type`/`index` fields in `config_stepper` and `line` field in `queue_step` | MCU firmware can associate each step with a stepper identity and print line for recovery |

## Additions

**Key constants (per-chip, gated by `CONFIG_MACH_AT32F415` / `CONFIG_MACH_AT32F403A`):**
- `FLASH_SECTOR_SIZE` — 1024 (AT32F415) or 2048 (AT32F403A) bytes.
- `RECORD_FLASH_SECTOR_ADDR1` / `RECORD_FLASH_SECTOR_ADDR2` — two sectors at the top of flash.
- `DETECTION_GPIO` / `DETECTION_GPIO_PIN` — PB8 (AT32F415) or PB7 (AT32F403A).
- `TRM_OVER_FREQ = 10000` / `TRM_PR_DIV_VALUE` — 10 kHz sampling timer.
- `MAX_ALLOW_SAVE_STEPPER_NUM = 16` — maximum steppers in a save record.
- `ENV_VALID_FLAG = 0x12345678` — magic number for flash record validation.

**Key data structures:**
- `power_loss_check_dev` struct — per-OID state: `report_state`, `need_save`, `print_act`, `voltage_type` (Type1/Type2 auto-detected), `high_level_tick`/`low_level_tick`, `duty_cycle_threshold`, `power_loss_trigger_time`, debounce counters, `power_loss_flag`.
- `power_loss_env` struct (2-byte aligned) — `flag`, `step_info_num`, `step_info_arry[16]` (from `stepper.h`).
- `SectorInfo` struct — `addr`, `seq_num`, `valid`, `is_init` for each of the two flash sectors.

**Functions:**
- `flash_read(addr, buf, n)` — byte-by-byte flash read.
- `flash_write_nocheck(addr, buf, n)` / `flash_write(addr, buf, n)` — halfword-mode flash write with optional sector-erase-and-rewrite logic.
- `flash_sector_erase_ex(sector_address)` — unlocks flash, erases one sector, re-locks.
- `power_loss_rotate_sector()` — implements wear-levelling: writes new record to the inactive sector with incremented sequence number, then erases the old sector.
- `load_save_flash_info()` — on startup, reads both sectors, validates flags and checksums, selects the sector with the higher sequence number as the current valid record.
- `power_loss_check_task_init()` — `DECL_INIT`; sets up GPIO, detection timer, and wake task.

**MCU commands (via `DECL_COMMAND`):**
- `command_config_power_loss_check_dev` — allocates OID and configures thresholds, debounce, and report interval.
- `query_power_loss_status oid=%c` — returns current `power_loss_flag` and `voltage_type`.
- `command_update_report_interval` — updates the periodic reporting interval at runtime.
- `command_enable_power_loss` — arms/disarms power-loss detection (`print_act` flag + `print_mark` identifier).
- `query_power_loss_flash_valid oid=%c` — checks whether valid stepper data exists in flash.
- `query_power_loss_stepper_info oid=%c type=%u index=%u` — retrieves saved stepper position for a specific `(type, index)` pair (matched against `step_info_arry`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- Flash write operations (`flash_halfword_program`) are performed inside the timer ISR path (via `power_loss_check_task`). Flash writes on AT32 stall instruction fetch from flash for the duration; if other ISRs fire during this window they will be delayed.
- The dual-sector scheme assumes that `power_loss_rotate_sector` completes before a second power loss occurs. If power is lost during the sector write, both sectors may be invalid on next boot.
- `MAX_ALLOW_SAVE_STEPPER_NUM = 16` is a compile-time constant. If `stepper.h`'s `get_all_stepper_info()` returns more than 16 steppers, the excess are silently ignored.
- `voltage_type` auto-detection uses a continuous-recognition counter (`type_confirm_threshold`, default 3 measurements). During startup there is a window where the type is `0xFF` (uninitialized) and the duty-cycle threshold uses a default that may not match the actual hardware.
- The module sends `"Power loss info saved"` as an MCU output message when a save completes. `serialhdl.py` in the host intercepts this string to raise a coded exception — if this string format ever changes, the host-side intercept will silently stop working.
- `RECORD_FLASH_SECTOR_ADDR1/2` for AT32F403A sit at `0x080FF000`/`0x080FF800` — the very last two sectors of a 1 MB device. Any firmware build larger than ~1020 KB will overwrite these sectors.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/power_loss_check.c
@@ -0,0 +1,~700 @@
+// New file – power-loss detection and stepper state save to flash
+// AT32F415: sectors at 0x0801F800/0x0801FC00 (1 KB), GPIO PB8
+// AT32F403A: sectors at 0x080FF000/0x080FF800 (2 KB), GPIO PB7
+// DECL_COMMAND: config_power_loss_check_dev, query_power_loss_status,
+//   command_update_report_interval, command_enable_power_loss,
+//   query_power_loss_flash_valid, query_power_loss_stepper_info
+// DECL_INIT: power_loss_check_task_init
```

</details>

---

# Hardware Libraries (lib/at32f403a, lib/at32f415, lib/rp2040)

## Summary
The fork adds two complete Artery Technology HAL (Hardware Abstraction Layer) libraries for the AT32 microcontrollers used in Snapmaker U1 hardware: `lib/at32f403a/` for the main board MCU and `lib/at32f415/` for the extruder head MCUs. These libraries provide the low-level peripheral drivers that Klipper's `src/stm32/` MCU code calls. The fork also patches `lib/rp2040/` with a minor change. None of these library directories exist in upstream Klipper.

---

## `lib/at32f403a/` — AT32F403A/407 HAL Library

### Summary
Complete Artery Technology HAL for the **AT32F403A/407** family (used as the U1 main board MCU). The AT32F403A is an STM32F103-compatible MCU from Artery Technology featuring up to 240 MHz clock, 256 KB flash, 96 KB RAM, and hardware-accelerated USB. The library provides peripheral drivers, startup code, linker scripts, and clock configuration.

### Contents
```
lib/at32f403a/
├── at32f403a_407.h              # Master include file
├── at32f403a_407_clock.c/h      # PLL/clock configuration (240 MHz via ACC)
├── at32f403a_407_conf.h         # HAL configuration switches
├── at32f403a_407_int.c/h        # Interrupt vector table
├── startup_at32f403a_407.s      # ARM assembly startup (CMSIS-compatible)
├── system_at32f403a_407.c/h     # SystemInit(), SystemCoreClock
├── usb_conf.h                   # USB device configuration
├── hal/
│   ├── inc/                     # HAL peripheral headers
│   └── src/                     # HAL peripheral drivers:
│       ├── at32f403a_407_acc.c  # Auto Clock Calibration (ACC) peripheral
│       ├── at32f403a_407_adc.c  # ADC driver
│       ├── at32f403a_407_bpr.c  # Battery-powered registers
│       ├── at32f403a_407_can.c  # CAN bus driver
│       ├── at32f403a_407_crc.c  # CRC calculation
│       ├── at32f403a_407_crm.c  # Clock and Reset Management
│       ├── at32f403a_407_dac.c  # DAC driver
│       ├── at32f403a_407_debug.c # Debug/CoreSight
│       ├── at32f403a_407_dma.c  # DMA controller
│       ├── at32f403a_407_emac.c # Ethernet MAC (AT32F407 only)
│       ├── at32f403a_407_exint.c # External interrupt
│       ├── at32f403a_407_flash.c # Flash erase/program (used by power_loss_check)
│       ├── at32f403a_407_gpio.c  # GPIO
│       ├── at32f403a_407_i2c.c  # I2C master/slave
│       ├── at32f403a_407_misc.c  # NVIC/SysTick
│       ├── at32f403a_407_pwc.c  # Power control
│       ├── at32f403a_407_rtc.c  # Real-time clock
│       ├── at32f403a_407_sdio.c # SDIO
│       ├── at32f403a_407_spi.c  # SPI master/slave
│       ├── at32f403a_407_tmr.c  # Timer (used by inductance_coil)
│       ├── at32f403a_407_usart.c # UART/USART
│       └── ...
├── linker/
│   ├── AT32F403AxC_FLASH.ld     # 256 KB flash linker script
│   ├── AT32F403AxE_FLASH.ld     # 512 KB variant
│   ├── AT32F403AxG_FLASH.ld     # 1024 KB variant
│   ├── AT32F407xC_FLASH.ld      # F407 256 KB variant
│   └── ...
├── usbd_class/                  # USB device class drivers (CDC, HID)
└── usbd_drivers/                # USB device stack
```

### Integration with Klipper
- `src/stm32/at32f403a.c` includes `at32f403a_407.h` and calls `at32f403a_407_clock.c` functions to initialise the 240 MHz PLL with ACC auto-calibration
- `src/stm32/inductance_coil.c` uses `at32f403a_407_tmr.c` for Timer2 frequency counting
- `src/stm32/power_loss_check.c` uses `at32f403a_407_flash.c` for wear-levelled state storage
- The Klipper build system (`lava/at32f403a_config`) selects `CONFIG_BOARD_DIRECTORY="stm32"` and uses `CONFIG_MCU="stm32f103xe"` — the AT32 is treated as STM32F103xe-compatible by the Klipper build, but the AT32-specific `at32f403a.c` overrides clock init and peripheral remapping

### Key Differences from STM32F103
The AT32F403A is pin/peripheral compatible with STM32F103 but adds:
- **ACC (Auto Clock Calibration)** peripheral — allows USB-trimmed 240 MHz clock without external crystal
- **Extended flash** — dual-bank flash with larger sectors, used by `power_loss_check.c`
- **Additional UART/SPI/CAN peripherals** — enables CAN2 on PA12/PB12, SPI4, UART5
- **240 MHz max clock** — requires Klipper timing calculations to account for 3× higher MCU frequency

---

## `lib/at32f415/` — AT32F415RC HAL Library

### Summary
Complete Artery Technology HAL for the **AT32F415** family (used as U1 extruder head MCUs, one per extruder). The AT32F415RC is an STM32F105-compatible MCU featuring 144 MHz clock, 256 KB flash, 32 KB RAM, and USB OTG. Each extruder head (T0–T3) has one AT32F415RC.

### Contents
```
lib/at32f415/
├── at32f415.h                   # Master include
├── at32f415_clock.c/h           # PLL config (144 MHz via USB OTG PLL)
├── at32f415_conf.h              # HAL configuration switches
├── at32f415_int.c/h             # Interrupt vector table
├── system_at32f415.c/h          # SystemInit()
├── usb_conf.h                   # USB device/host configuration
├── hal/
│   ├── inc/                     # Headers for AT32F415 peripherals
│   └── src/                     # Peripheral drivers (ADC, CAN, CRM, DMA,
│                                #   EXINT, FLASH, GPIO, I2C, MISC, PWC,
│                                #   SPI, TMR, USART, etc.)
├── usb_drivers/                 # USB OTG device stack (lower level)
├── usbd_class/                  # USB CDC, HID classes
├── usbh_class/                  # USB host class (Host mode capability)
└── startup / linker scripts
```

### Integration with Klipper
- `src/stm32/at32f415rc.c` includes `at32f415.h` and uses `at32f415_clock.c` to initialise USB OTG PLL at 144 MHz
- The Klipper build uses `CONFIG_MCU="stm32f105xc"` (STM32F105 compatible) and `CONFIG_USBSERIAL=y` — each extruder head communicates with the SoC host over USB CDC serial
- AT32F415 has no EMAC (no Ethernet); the HAL is smaller than AT32F403A
- USB host capability (`usbh_class/`) is present in the HAL but unused by Klipper firmware

---

## `lib/rp2040/` — RP2040 Library Patch

The fork includes a small patch file `lib/rp2040/rp2040.patch` applied to the upstream RP2040 library. This appears to be a minor build compatibility fix. The RP2040 library itself is otherwise identical to upstream; the patch adjusts linker script handling for the fork's build environment.

**Note:** The U1 does not use an RP2040; this patch is likely a carry-over from development tooling or a build system compatibility fix.

---

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32 HAL libraries | `lib/at32f403a/`, `lib/at32f415/` added | U1 uses Artery AT32 MCUs |
| RP2040 library unpatched | `rp2040.patch` applied | Build environment compatibility |

## Additions
- `lib/at32f403a/` — 50+ HAL source files + linker scripts + USB stack
- `lib/at32f415/` — 40+ HAL source files + linker scripts + USB OTG stack + USB host

## Risks / Compatibility Notes
- The AT32 HAL libraries are proprietary Artery Technology code — license must be verified before redistribution (they appear to use a permissive BSD-like license based on standard embedded HAL practices)
- `CONFIG_MCU="stm32f103xe"` / `"stm32f105xc"` aliases work only because AT32 is register-compatible; any upstream Klipper change that adds AT32-specific register differences would require updating these aliases
- The 240 MHz / 144 MHz clock speeds require that all Klipper timing constants that depend on MCU frequency are correctly calculated — errors would cause stepper timing glitches
- USB by-path addressing in `lava/printer.cfg` is tied to the specific USB hub topology of the U1 PCB assembly

---

# lava/ — Snapmaker U1 Production Configuration Directory

## Summary
The `lava/` directory is entirely fork-exclusive and contains the complete production configuration for the Snapmaker U1 multi-material 3D printer. It includes the main `printer.cfg` (the actual running configuration used on U1 devices), the Fluidd UI configuration (`fluidd.cfg`), an XYZ offset calibration workflow script (`xyz_offset_calibration.cfg`), and three pre-built Klipper firmware `.config` files for the U1's three microcontrollers. None of these files exist in upstream Klipper; they are the definitive reference for how all fork-exclusive modules are wired together on real hardware.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No `lava/` directory | Complete production printer config | U1 ships with this config pre-installed |
| No AT32 MCU firmware configs | `at32f403a_config`, `at32f415_config`, `klippy_mcu_config` | AT32 MCUs are U1-specific hardware |

---

## `lava/printer.cfg`

**96 configuration sections** covering the full U1 hardware. Key structure:

### MCU Configuration
| Section | MCU | Connection | Purpose |
|---------|-----|-----------|---------|
| `[mcu]` | AT32F403A | `/dev/ttyS6`, 460800 baud | Main motion controller board |
| `[mcu host]` | Linux (AArch64 SoC) | `/tmp/klipper_host_mcu` | Host MCU for GPIO/SPI access |
| `[mcu e0]`–`[mcu e3]` | AT32F415RC × 4 | USB by-path (`xhci-hcd.0.auto`) | Per-extruder MCUs (T0–T3) |

### Motion System
- `kinematics: corexy` with `max_velocity: 500`, `max_accel: 20000`, `max_z_velocity: 30`
- X: `position_max: 271`, sensorless homing via `tmc2240_stepper_x:virtual_endstop`
- Y: `position_max: 335`, sensorless homing via `tmc2240_stepper_y:virtual_endstop`
- Z: `position_max: 275`, sensorless homing via `tmc2209_stepper_z:virtual_endstop`
- All axes use `homing_precise_corexy` for improved sensorless accuracy

### Extruder System (× 4, T0–T3)
Each extruder (`extruder`, `extruder1`, `extruder2`, `extruder3`) has:
- `[tmc2209 extruderN]` — stepper driver on `[mcu eN]`
- `[park_detector extruderN]` — detects if tool is parked
- `[fan_generic eN_fan]`, `[heater_fan eN_nozzle_fan]` — cooling fans
- `[output_pin eN_heat_sw]` — heater power switch
- `[filament_motion_sensor eN_filament]` — motion-based runout
- `[filament_entangle_detect eN_filament]` — tangle detection
- `[inductance_coil extruderN]` — inductive Z probe
- `[lis2dw eN_lis2dw]` — accelerometer for resonance testing
- `[power_loss_check eN]` — per-extruder power loss state flash

### Connectivity & Peripherals
- `[mqtt]` — Snapmaker app communication
- `[timelapse]` with `frame_rate: 24`
- `[fm175xx_reader]` — NFC reader on SoC SPI bus 2 with 4 channels (2 on SoC SPI, 2 on extra SPI)
- `[filament_detect]` — filament presence across all slots
- `[flow_calibrator]` — extrusion multiplier calibration
- `[resonance_tester]`/`[input_shaper]` — vibration compensation
- `[adc_current_sensor I_AD]` — current monitoring
- `[purifier]` — air filtration control

### Bed & Enclosure
- `[heater_bed]`, `[verify_heater heater_bed]`
- `[temperature_sensor cavity]`, `[fan_generic cavity_fan]`, `[led cavity_led]`
- `[bed_mesh]`, `[auto_screws_tilt_adjust]`

### Power Loss Recovery
- `[power_loss_check]` — main board PLR
- `[gcode_macro _PL_SAVE_VARIABLE]` — PLR state G-code variable block

### G-code Macros
| Macro | Purpose |
|-------|---------|
| `AUTO_BED_MESH_CALIBRATE` | Automated bed levelling sequence |
| `SHAKE_Z` | Z-axis vibration for self-check |
| `SENSORLESS_HOME_X/Y/Z` | Sensorless homing sequences |
| `_HOMING_PRECISE_COREXY_ADVANCED` | Advanced homing with stall detection |
| `_CLIENT_VARIABLE` | Fluidd/KlipperScreen variable overrides |
| `_FILAMENT_FEED_VARIABLE` | Filament feed system parameters |

### Filament Feed System
- `[filament_feed left]` / `[filament_feed right]` — filament loader motors
- `[filament_parameters]` — per-material configuration
- `[defect_detection]` — print defect detection integration

---

## `lava/fluidd.cfg`

Standard Fluidd UI client macro definitions (pause/resume/cancel/start G-codes). This is the community-standard `fluidd.cfg` included by the U1 config. Identical to the upstream Fluidd community file — no U1-specific changes.

---

## `lava/xyz_offset_calibration.cfg`

**Extruder nozzle XYZ offset calibration workflow.** Contains a sequence of G-code macros for semi-automated calibration of extruder-to-extruder offsets:

- `_EXTRUDER_OFFSET_ACTION_PRESTART` — initialise calibration session (heat, home, clean)
- `_EXTRUDER_OFFSET_ACTION_PREHEAT` — heat nozzles for calibration
- `_EXTRUDER_OFFSET_ACTION_PREHOMING` — home axes before calibration
- `_EXTRUDER_OFFSET_ACTION_AUTO_CLEAN` / `_EXTRUDER_OFFSET_ACTION_MANUAL_CLEAN` — nozzle wipe
- `_EXTRUDER_OFFSET_ACTION_HEAT` / `_EXTRUDER_OFFSET_ACTION_WAIT_COOL` — thermal management
- `_EXTRUDER_OFFSET_ACTION_PROBE_CALIBRATE` — measure nozzle height offset for T0–T3
- `_EXTRUDER_OFFSET_ACTION_DETECT_PLATE` — detect build plate presence
- `_EXTRUDER_OFFSET_ACTION_EXIT` — finalise and save offsets

All macros accept `TOOL_ID=T0|T1|T2|T3` parameter. The sequence is designed for the 4-extruder U1 but each step can be called individually.

---

## `lava/at32f403a_config`

Klipper `.config` file for the **AT32F403A main board MCU**. Key settings:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_STM32=y` | STM32-compatible build | AT32F403A uses STM32-compatible HAL |
| `CONFIG_MCU="stm32f103xe"` | Identifies as STM32F103 | AT32F403A is pin/peripheral compatible |
| `CONFIG_CLOCK_FREQ=240000000` | 240 MHz | AT32F403A maximum clock (vs 72 MHz for real STM32F103) |
| `CONFIG_SERIAL=y` | UART communication | Connects to host at 460800 baud |
| `CONFIG_FLASH_SIZE=0x40000` | 256 KB flash | AT32F403A flash size |
| `CONFIG_RAM_SIZE=0x18000` | 96 KB RAM | AT32F403A RAM size |

---

## `lava/at32f415_config`

Klipper `.config` file for the **AT32F415RC extruder MCUs** (one per extruder head).

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_STM32=y` | STM32-compatible | AT32F415 uses STM32-compatible HAL |
| `CONFIG_MCU="stm32f105xc"` | Identifies as STM32F105 | AT32F415 is peripheral-compatible |
| `CONFIG_CLOCK_FREQ=144000000` | 144 MHz | AT32F415 maximum clock |
| `CONFIG_USBSERIAL=y` | USB CDC serial | Connects to host via USB |
| `CONFIG_FLASH_SIZE=0x40000` | 256 KB flash | AT32F415RC flash |
| `CONFIG_RAM_SIZE=0x8000` | 32 KB RAM | AT32F415RC RAM |

---

## `lava/klippy_mcu_config`

Klipper `.config` file for the **Linux host MCU** (runs on the U1 SoC itself).

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_LINUX=y` | Linux process MCU | Runs as user-space process |
| `CONFIG_CLOCK_FREQ=50000000` | 50 MHz (nominal) | Linux MCU soft clock |
| `CONFIG_WANT_GPIO_BITBANGING=y` | Software GPIO | Required for SPI NFC reader |
| `CONFIG_USB_VENDOR_ID=0x1d50` | OpenMoko VID | Standard Klipper USB identity |

---

## Risks / Compatibility Notes
- The `lava/printer.cfg` references fork-exclusive config sections (`[mqtt]`, `[timelapse]`, `[fm175xx_reader]`, `[filament_detect]`, `[inductance_coil *]`, `[park_detector *]`, `[power_loss_check *]`, `[homing_precise_corexy]`, etc.) — **this config cannot run on upstream Klipper** without removing all U1-specific sections
- The AT32F403A is identified as `stm32f103xe` in the config — if Klipper upstream adds stricter MCU type validation, this alias may break
- The `CONFIG_CLOCK_FREQ=240000000` for AT32F403A is 3× higher than a real STM32F103; timing-sensitive code must account for this
- NFC reader (fm175xx_reader) requires SoC SPI device node access (`/dev/spidev2.0`, `/dev/spidev2.1`) — Linux kernel must have SPI enabled in device tree
- USB by-path addresses for extruder MCUs (`platform-xhci-hcd.0.auto-usb-0:1.N:1.0`) are hardware-specific and will differ on any other system

---

# config/ — Upstream Config Changes

## Summary
The fork's `config/` directory is a near-copy of upstream Klipper's example printer configuration files, updated to the fork's base snapshot. The main differences are: replacement of `spi_bus` with explicit software SPI pin definitions across several BigTreeTech board configs (likely because the fork's underlying MCU SPI bus naming differs), removal of a TMC2130 section from one config, minor comment corrections, and the absence of two upstream-only config files. No new U1-specific configs exist in this directory; U1-specific configuration lives in `lava/` instead.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `spi_bus: spi3_PC11_PC12_PC10` in BTT Manta E3EZ TMC2130 sections | Replaced with `spi_software_miso_pin`, `spi_software_mosi_pin`, `spi_software_sclk_pin` | Fork's `mcu.py` may handle SPI bus names differently; explicit pins more portable |
| `generic-bigtreetech-skr-2.cfg` includes TMC2130 section | TMC2130 section removed | TMC2130 requires `spi_bus` that fork handles differently |
| `example-generic-caretesian.cfg` exists | Absent from fork | File missing; likely not copied when fork was created |
| `generic-mellow-fly-e3-v2.cfg` exists | Absent from fork | File added to upstream after fork diverged |
| Various BTT/Creality/Voron/kit configs have minor comment/spacing differences | Minor divergences | Snapshot in time of upstream configs |

## Additions
None — no new config files added to `config/` for U1.

## Removals / Overrides
- `example-generic-caretesian.cfg` — not present in fork (upstream-only)
- `generic-mellow-fly-e3-v2.cfg` — not present in fork (added to upstream after fork)
- TMC2130 section removed from `generic-bigtreetech-skr-2.cfg`

## Risks / Compatibility Notes
- Users copying BTT Manta E3EZ config from fork will use software SPI instead of hardware SPI — functional but slower and less timing-accurate
- The missing `example-generic-caretesian.cfg` is documentation only; no runtime impact

## Raw Diff
<details>
<summary>View Diff (generic-bigtreetech-manta-e3ez.cfg excerpt)</summary>

```diff
 #[tmc2130 stepper_x]
 #cs_pin: PB8
-#spi_bus: spi3_PC11_PC12_PC10
+#spi_software_miso_pin: PC11
+#spi_software_mosi_pin: PC12
+#spi_software_sclk_pin: PC10
 ##diag1_pin: PF3
 #run_current: 0.800
 #stealthchop_threshold: 999999
```
</details>

---

# scripts/ — Script Changes

## Summary
The fork's `scripts/` directory is a snapshot of upstream Klipper scripts from the fork's base point, with three significant changes: `buildcommands.py` removes the `klippy/.version` file version fallback; `calibrate_shaper.py` is simplified to remove multi-dataset CSV support, matching the simplified `shaper_calibrate.py` API; and `graph_accelerometer.py` drops CSV output and simplifies its plotting API. Three upstream-only scripts are absent. All other scripts in the fork are functionally identical to their upstream counterparts at the fork's base commit.

## Changed From Upstream

### `scripts/buildcommands.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `file_version()` reads `klippy/.version` file to get version string | Removed; always uses `version = "?"` | Fork manages versioning differently; `.version` file may not exist in U1 deployment |

**Key diff:**
```diff
-def file_version():
-    if not os.path.exists('klippy/.version'):
-        return ""
-    ver = check_output("cat klippy/.version").strip()
-    return ver
-    version = file_version()
-    if not version:
-        version = "?"
+    version = "?"
```

### `scripts/calibrate_shaper.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Accepts CSV pre-processed frequency data or raw accelerometer data | Only accepts raw accelerometer data | Matches simplified `shaper_calibrate.py` API (no named datasets) |
| `import csv` | Removed | No CSV reading needed |
| `process_accelerometer_data(logname, data)` | `process_accelerometer_data(data)` — no `name` param | Matches fork's `shaper_calibrate.CalibrationData` API (name removed) |
| `CalibrationData(logname, ...)` named datasets | `CalibrationData(freq_bins, psd_sum, ...)` | API revert to match fork's `shaper_calibrate.py` |
| Multi-axis CSV output | Single-axis PSD only | Z-axis removed from resonance testing |

### `scripts/graph_accelerometer.py`
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `plot_accel(opts, datas, lognames)` | `plot_accel(datas, lognames)` — `opts` removed | Simplified CLI handling |
| `calc_freq_response(name, data, max_freq)` | `calc_freq_response(data, max_freq)` — no `name` | Matches shaper_calibrate name removal |
| `plot_frequency(opts, datas, lognames, max_freq, axis)` | `plot_frequency(datas, lognames, max_freq)` | No opts; no axis param (Z removed) |
| `plot_specgram(opts, data, logname, max_freq, axis)` | `plot_specgram(data, logname, max_freq, axis)` | No opts |
| `write_frequency_response(lognames, datas, output)` | Present but simplified | |
| `import csv, importlib, optparse, os, sys` | `import importlib, optparse, os, sys` — no `csv` | CSV writing removed |
| `plot_compare_frequency()` absent | `plot_compare_frequency(datas, lognames, max_freq, axis)` added | New comparison plot function for U1 multi-extruder shaper comparison |

### CI/Install Scripts (minor)
Several CI scripts (`scripts/ci-build.sh`, `scripts/install-*.sh`) have minor divergences from upstream reflecting the fork's build environment (AT32 cross-compiler instead of ARM Cortex-M):
- `PKGS` list adds `pv libmpfr-dev libgmp-dev libmpc-dev texinfo bison flex` for building the RISC-V cross-compiler
- PRU toolchain URL updated (different archive naming)
- OR1K toolchain changed to use musl-cross variant

## Additions
- `scripts/graph_accelerometer.py`: `plot_compare_frequency(datas, lognames, max_freq, axis)` — new function for comparing frequency responses across multiple extruders

## Removals / Overrides
- `scripts/buildcommands.py`: `file_version()` function removed
- `scripts/calibrate_shaper.py`: CSV reading path, multi-dataset handling, `import csv`
- `scripts/graph_accelerometer.py`: `opts` parameter from multiple functions

**Upstream-only scripts not present in fork:**
- `scripts/check-software-div.sh` — compiler software division check
- `scripts/filter_workbench.ipynb` — Jupyter notebook for filter analysis
- `scripts/tests-requirements.txt` — Python test dependencies list

## Risks / Compatibility Notes
- `buildcommands.py` always reports `version = "?"` — `FIRMWARE_VERSION` in Klipper's startup log will always show `?` on fork builds
- `calibrate_shaper.py` will not accept pre-processed frequency CSV files that upstream expects — Z-axis data is silently ignored
- The missing `tests-requirements.txt` means the fork's test suite (`scripts/test_klippy.py`) cannot be set up from the scripts directory alone
- Any user running `scripts/graph_accelerometer.py` with upstream-style arguments (passing `opts` as first arg) will get incorrect results

## Raw Diff
<details>
<summary>View Diff (buildcommands.py)</summary>

```diff
-# Obtain version info from "klippy/.version" file
-def file_version():
-    if not os.path.exists('klippy/.version'):
-        logging.debug("No 'klippy/.version' file/directory found")
-        return ""
-    ver = check_output("cat klippy/.version").strip()
-    logging.debug("Got klippy version: %s" % (repr(ver),))
-    return ver
 ...
-        version = file_version()
-        if not version:
-            version = "?"
+        version = "?"
```
</details>
