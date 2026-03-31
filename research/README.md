# Snapmaker U1 Klipper Fork — Research Index

## Analyses

### MCU C Source Analysis (AT32)

**Directory:** [`/research/mcu/`](mcu/)

Documents the AT32F403A/AT32F415RC MCU implementation that is disguised as STM32 variants within the Klipper build system. The AT32F403A (240 MHz, main board) masquerades as `stm32f103xe`; the AT32F415RC (144 MHz, extruder heads) masquerades as `stm32f105xc`.

**Scope:**
- 7 new files in `src/stm32/` (1,731 lines): clock setup, ACC calibration, inductance coil probing, power loss recovery
- 7 modified files in `src/stm32/`: CAN, SPI, serial, USB, and clock init conditionals for AT32
- 2 full HAL libraries (`lib/at32f403a/`, `lib/at32f415/`): ~103,500 lines from official Artery SDK
- Build system changes: Kconfig entries, Makefile source lists, compiler flags
- Python-C cross-reference: new MCU commands for U1 hardware features

**Key documents:**
- [Summary Report](mcu/README.md)
- [Architecture Overview](mcu/architecture-overview.md)
- [Upstream Contribution Path](mcu/upstream-path.md)

**Raw diffs:** [`/research/raw/mcu-*.diff`](raw/)

---

## Raw Diffs

All raw diffs are stored in [`/research/raw/`](raw/) with descriptive prefixes:

| File | Scope | Lines |
|------|-------|------:|
| `full.diff` | Complete unified diff | ~2 MB |
| `klippy.diff` | `klippy/` directory diff | — |
| `klippy-extras.diff` | `klippy/extras/` diff | — |
| `klippy-kinematics.diff` | kinematics diff | — |
| `klippy-chelper.diff` | chelper C code diff | — |
| `scripts.diff` | `scripts/` diff | — |
| `config.diff` | `config/` diff | — |
| `root-files.diff` | Root Makefile/README diff | — |
| `name-status.txt` | File manifest (all changed/added/removed) | — |
| `mcu-src-stm32.diff` | `src/stm32/` changes | 2,309 |
| `mcu-lib-at32f403a.diff` | `lib/at32f403a/` (full library) | 51,919 |
| `mcu-lib-at32f415.diff` | `lib/at32f415/` (full library) | 54,668 |
| `mcu-build.diff` | Makefile, Kconfig, scripts/ | 130 |
| `mcu-name-status.diff` | File manifest for `src/` and `lib/` | 286 |

---

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
| **Upstream-only extras removed from fork** | 14 | `ads1220`, `ads1x1x`, `bmi160`, `canbus_stats`, `garbage_collection`, `hx71x`, `icm20948`, `lis3dh`, `load_cell`, `load_cell_probe`, `motion_queuing`, `static_pwm_clock`, `temperature_probe`, `trigger_analog` |
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

4. **Missing upstream features** — 14 upstream extras are absent (load cell, garbage collection, new sensors, etc.); the chelper `steppersync` refactor and `kin_generic` are missing. Upstream configs referencing these will fail.

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
- [`research/raw/mcu-src-stm32.diff`](raw/mcu-src-stm32.diff) — src/stm32/ changes
- [`research/raw/mcu-lib-at32f403a.diff`](raw/mcu-lib-at32f403a.diff) — lib/at32f403a/ (full library)
- [`research/raw/mcu-lib-at32f415.diff`](raw/mcu-lib-at32f415.diff) — lib/at32f415/ (full library)
- [`research/raw/mcu-build.diff`](raw/mcu-build.diff) — Makefile, Kconfig, scripts/
- [`research/raw/mcu-name-status.diff`](raw/mcu-name-status.diff) — File manifest for src/ and lib/

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

#### MCU Analysis
| File | Coverage |
|------|---------|
| [mcu/README.md](mcu/README.md) | AT32 MCU summary report |
| [mcu/architecture-overview.md](mcu/architecture-overview.md) | Disguise mechanism, clock topology, build system integration |
| [mcu/upstream-path.md](mcu/upstream-path.md) | Upstream contributability assessment |

#### Configuration
| File | Coverage |
|------|---------|
| [lava-directory.md](modules/lava-directory.md) | Complete `lava/` production config; MCU configs; calibration macros |
| [config-changes.md](modules/config-changes.md) | Minor upstream config divergences; missing files |
| [scripts-changes.md](modules/scripts-changes.md) | `buildcommands.py`, `calibrate_shaper.py`, `graph_accelerometer.py` |

---

## Triage Results

Cross-referenced all 104 documented fork divergences against upstream Klipper
`HEAD` (`2f05309d`). Full triage report: **[triage/README.md](triage/README.md)**

### Tier Breakdown

| Tier | Label | Count | Description |
|------|-------|-------|-------------|
| **1** | **Drop** | 17 | Upstream fully covers this; restore from upstream |
| **2** | **Adapt** | 14 | Upstream covers the need differently; migrate to upstream approach |
| **3** | **Layer** | 23 | Upstream partially covers it; maintain a reduced shim |
| **4** | **Keep** | 52 | No upstream coverage; permanent fork divergence |
| | **Total** | **104** | |

### Quick Wins (Tier 1)
17 items can be addressed immediately with low risk:
- Restore 13 absent upstream extras files (none affect U1 hardware)
- Restore `chelper/kin_generic.c`
- Restore `reactor.py::assert_no_pause`
- Restore `buttons.py::DebounceButton`
- Restore `stepper_enable.py` mux command pattern

### Permanent Fork Surface (Tier 4 — 52 items)
The fork must maintain these indefinitely:
- **PLR system** — Power-loss recovery (no upstream equivalent)
- **Filament system** — 6 modules for U1's filament routing hardware
- **AT32 MCU support** — Firmware + HAL libraries for Artery Technology MCUs
- **Inductive probe** — Frequency-measurement probe architecture
- **App communication** — MQTT + JSON-RPC + exception system
- **Multi-extruder** — 4-head tool-change architecture

### Adaptation Documents
Tier 1 and 2 items have detailed migration paths:
- [triage/adaptations/](triage/adaptations/) — 13 adaptation documents covering every Drop/Adapt item
- [triage/inventory.md](triage/inventory.md) — Complete flat inventory of all 104 changes