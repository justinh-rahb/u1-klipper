# Upstream Triage — Master Report

**Upstream HEAD compared:** `2f05309d59743c1a20b271da3a8c481397c16424` — "stm32: usbotg block next bulk_in if buffer not empty"  
**Fork HEAD:** `6491ebab3831112a6549539a87c068ef34bc6583`  
**Triage Date:** 2026-03-30

---

## Tier Counts

| Tier | Label | Count | Meaning |
|------|-------|-------|---------|
| **1** | Drop | **17** | Upstream fully covers this; fork patch can be removed |
| **2** | Adapt | **14** | Upstream covers the need differently; replace fork patch with upstream approach |
| **3** | Layer | **23** | Upstream partially covers it; keep a reduced patch or shim |
| **4** | Keep | **52** | No upstream coverage; must maintain as fork patch |
| | **Total** | **104** | |

---

## Quick Wins — Tier 1 Drops (No Config Migration Complexity)

These items can be addressed immediately with near-zero risk. Each is an additive
file restore or a simple method restoration with no behavioural impact on U1 hardware.

| ID | Change | Action |
|----|--------|--------|
| **A4** | `chelper/kin_generic.c` absent | Copy from upstream; add to `SOURCE_FILES` and `Makefile` |
| **B7** | `reactor.py` `assert_no_pause` absent | Copy method from upstream; dormant until B3 is done |
| **C11** | `buttons.py` `DebounceButton` absent | Copy class from upstream; additive |
| **C12** | `stepper_enable.py` mux→plain reversion | Restore `register_mux_command` pattern |
| **C22–C31, C33–C35** | 13 upstream extras absent | Copy files from upstream; none referenced by U1 config |

**Combined estimated effort:** 1–2 developer days.  
**Risk:** Low for all. These add capabilities without changing existing behaviour.

---

## Full Triage Table

### A — chelper

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| A1 | `chelper/__init__.py` — steppersync API reversion | 2 | [chelper-steppersync.md](adaptations/chelper-steppersync.md) |
| A2 | `chelper/steppersync.c` — removed | 2 | [chelper-steppersync.md](adaptations/chelper-steppersync.md) |
| A3 | `chelper/steppersync.h` — removed | 2 | [chelper-steppersync.md](adaptations/chelper-steppersync.md) |
| A4 | `chelper/kin_generic.c` — removed | **1** | [chelper-kin-generic.md](adaptations/chelper-kin-generic.md) |
| A5 | `chelper/Makefile` — new AArch64 cross-compile | 4 | — |

### B — klippy/ core

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| B1 | `klippy.py` — SCHED_FIFO, MCU power, exception dispatch | 4 | — |
| B2 | `mcu.py` — removes MCURestartHelper, DummyResponse, ~500 lines | 2 | [mcu-restart-helper.md](adaptations/mcu-restart-helper.md) |
| B3 | `toolhead.py` — reverts MotionQueuing; minimum_cruise_ratio; U1 additions | 2 | [toolhead-motion-queuing.md](adaptations/toolhead-motion-queuing.md) |
| B4 | `gcode.py` — coded errors; Coord revert | 3 | — |
| B5 | `webhooks.py` — removes msgspec | 2 | [webhooks-msgspec.md](adaptations/webhooks-msgspec.md) |
| B6 | `stepper.py` — PLR type/index fields | 4 | — |
| B7 | `reactor.py` — removes assert_no_pause | **1** | [reactor-assert-no-pause.md](adaptations/reactor-assert-no-pause.md) |
| B8 | `configfile.py` — Snapmaker path helpers | 4 | — |
| B9 | `serialhdl.py` — AT32 serial minor changes | 4 | — |
| B10 | `pins.py` — pin alias minor changes | 4 | — |
| B11 | `util.py` — minor utility tweaks | 4 | — |
| B12 | `msgproto.py` — cosmetic changes | 3 | — |
| B13 | `queuelogger.py` — log format minor | 3 | — |
| B14 | `mathutil.py` — minor numerical changes | 3 | — |
| B15 | `coded_exception.py` — new structured error class | 4 | — |
| B16 | `exception_manager.py` — new error bus G-codes | 4 | — |
| B17 | `printer_device_scan.py` — MCU auto-detection | 4 | — |
| B18 | `queuefile.py` — async atomic file I/O | 4 | — |

### C — klippy/extras/ (major modifications)

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| C1 | `virtual_sdcard.py` — full PLR subsystem | 4 | — |
| C2 | `heaters.py` — dynamic power limits, PID profiles | 4 | — |
| C3 | `probe.py` — removes ProbeResult | 2 | [probe-probe-result.md](adaptations/probe-probe-result.md) |
| C4 | `bed_mesh.py` — inductance coil integration | 4 | — |
| C5 | `resonance_tester.py` — 2D-only, SM_FAST_SHAPER_CALIBRATE | 3 | — |

### C — klippy/extras/ (minor/medium modifications)

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| C6 | `probe_eddy_current.py` — large reversion, removes trigger_analog | 2 | [probe-eddy-current.md](adaptations/probe-eddy-current.md) |
| C7 | `tmc.py` — removes TMCStallguardDump, coded errors | 2 | [tmc-stallguard-dump.md](adaptations/tmc-stallguard-dump.md) |
| C8 | `output_pin.py` — removes GCodeRequestQueue, template evaluator | 2 | [output-pin-gcode-request-queue.md](adaptations/output-pin-gcode-request-queue.md) |
| C9 | `print_stats.py` — multi-extruder state, exceptions | 4 | — |
| C10 | `shaper_calibrate.py` — simplified CalibrationData + zvd | 2 | [shaper-calibrate-api.md](adaptations/shaper-calibrate-api.md) |
| C11 | `buttons.py` — removes DebounceButton | **1** | [buttons-debounce.md](adaptations/buttons-debounce.md) |
| C12 | `stepper_enable.py` — mux→plain reversion | **1** | [stepper-enable-mux.md](adaptations/stepper-enable-mux.md) |
| C13 | `homing.py` — minor homing index changes | 3 | — |
| C14 | `fan.py` — minor changes | 3 | — |
| C15 | `led.py` — minor changes | 3 | — |
| C16 | `pause_resume.py` — minor changes | 3 | — |
| C17 | `temperature_sensor.py` — minor changes | 3 | — |
| C18 | `gcode_macro.py` — minor changes | 3 | — |
| C19 | `idle_timeout.py` — minor changes | 3 | — |
| C20 | `endstop_phase.py` — minor changes | 3 | — |
| C21 | ~65 other extras/*.py — API signature reversions | 3 | — |

### C — klippy/extras/ (upstream extras absent from fork)

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| C22 | `ads1220.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C23 | `ads1x1x.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C24 | `bmi160.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C25 | `canbus_stats.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C26 | `garbage_collection.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C27 | `hx71x.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C28 | `icm20948.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C29 | `lis3dh.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C30 | `load_cell.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C31 | `load_cell_probe.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C32 | `motion_queuing.py` — removed | 2 | [motion-queuing.md](adaptations/motion-queuing.md) |
| C33 | `static_pwm_clock.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C34 | `temperature_probe.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C35 | `trigger_analog.py` — removed | **1** | [removed-upstream-extras.md](adaptations/removed-upstream-extras.md) |
| C36 | `static_digital_output.py` — **present in fork** | 4 | — |

### D — Fork-Exclusive Extras (all Tier 4)

| ID | Module | Tier |
|----|--------|------|
| D1–D6 | Filament system (detect, feed, entangle, parameters, protocol, fac_test) | 4 |
| D7 | `mqtt.py` | 4 |
| D8 | `jsonrpc.py` | 4 |
| D9 | `machine_state_manager.py` | 4 |
| D10 | `print_task_config.py` | 4 |
| D11 | `timelapse.py` | 4 |
| D12–D13 | `inductance_coil.py`, `probe_inductance_coil.py` | 4 |
| D14 | `adc_current_sensor.py` | 4 |
| D15 | `park_detector.py` | 4 |
| D16 | `fm175xx_reader.py` | 4 |
| D17–D18 | `homing_precise_corexy.py`, `homing_xyz_override.py` | 4 |
| D19 | `auto_screws_tilt_adjust.py` | 4 |
| D20–D21 | `extruder_calibration.py`, `flow_calibrator.py` | 4 |
| D22 | `power_loss_check.py` | 4 |
| D23 | `purifier.py` | 4 |
| D24 | `defect_detection.py` | 4 |
| D25–D26 | `extruder_config_bak.py`, `setup.py` | 4 |

### E — kinematics/

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| E1 | `kinematics/extruder.py` — multi-extruder, park/pick | 4 | — |
| E2 | `kinematics/idex_modes.py` — simplified vs upstream | 3 | — |
| E3–E13 | 11 kinematics files — Coord/API reversions | 3 | [kinematics-coord-api.md](adaptations/kinematics-coord-api.md) |

### F — src/ firmware (all Tier 4)

| ID | Files | Tier |
|----|-------|------|
| F1–F4 | AT32F403A and AT32F415RC MCU support | 4 |
| F5–F6 | Inductance coil firmware (TMR2 + TMR5) | 4 |
| F7 | Power-loss check flash storage | 4 |

### G — lib/ (all Tier 4)

| ID | Libraries | Tier |
|----|-----------|------|
| G1 | `lib/at32f403a/` — AT32F403A HAL | 4 |
| G2 | `lib/at32f415/` — AT32F415RC HAL | 4 |

### H — Config (all Tier 3–4)

| ID | Path | Tier |
|----|------|------|
| H1 | `lava/` — U1 production config | 4 |
| H2 | `config/` divergences | 3 |

### I — Scripts

| ID | File | Tier | Adaptation Doc |
|----|------|------|----------------|
| I1 | `scripts/buildcommands.py` — AT32 build support | 4 | — |
| I2 | `scripts/calibrate_shaper.py` — simplified CalibrationData API | 2 | [scripts-shaper.md](adaptations/scripts-shaper.md) |
| I3 | `scripts/graph_accelerometer.py` — simplified CalibrationData API | 2 | [scripts-shaper.md](adaptations/scripts-shaper.md) |

---

## Recommended Sequencing

Items are ordered to minimise blocking dependencies and maximise risk reduction
per unit of effort.

### Sprint 1 — Quick Wins (1–2 days, Low Risk)
Address all Tier 1 items independently. No architecture changes required.

1. **C22–C31, C33–C35**: Restore 13 absent upstream extras files
   — see [removed-upstream-extras.md](adaptations/removed-upstream-extras.md)
2. **A4**: Restore `kin_generic.c`
   — see [chelper-kin-generic.md](adaptations/chelper-kin-generic.md)
3. **B7**: Restore `reactor.py::assert_no_pause`
   — see [reactor-assert-no-pause.md](adaptations/reactor-assert-no-pause.md)
4. **C11**: Restore `buttons.py::DebounceButton`
   — see [buttons-debounce.md](adaptations/buttons-debounce.md)
5. **C12**: Restore `stepper_enable.py` mux command
   — see [stepper-enable-mux.md](adaptations/stepper-enable-mux.md)

### Sprint 2 — Isolated Adapt Items (2–4 days, Low-Medium Risk)
These Tier 2 items have minimal dependencies on the large architecture changes.

6. **B5**: Restore `webhooks.py` msgspec import
   — see [webhooks-msgspec.md](adaptations/webhooks-msgspec.md)
7. **C7**: Restore `tmc.py::TMCStallguardDump`
   — see [tmc-stallguard-dump.md](adaptations/tmc-stallguard-dump.md)
8. **E3–E13**: Migrate 11 kinematics files to upstream Coord/API
   — see [kinematics-coord-api.md](adaptations/kinematics-coord-api.md)
   *(Best done with `corexy.py` first; U1 is CoreXY)*

### Sprint 3 — Probe + Shaper API (3–5 days, Medium Risk)
Dependencies: Sprint 2 complete; C35 (trigger_analog) restored.

9. **C3**: Adopt `ProbeResult` in `probe.py`
   — see [probe-probe-result.md](adaptations/probe-probe-result.md)
10. **C6**: Restore `probe_eddy_current.py` (after C3 and C35)
    — see [probe-eddy-current.md](adaptations/probe-eddy-current.md)
11. **C10**: Restore `CalibrationData` API + retain `zvd`
    — see [shaper-calibrate-api.md](adaptations/shaper-calibrate-api.md)
12. **I2, I3**: Update scripts to match restored CalibrationData API
    — see [scripts-shaper.md](adaptations/scripts-shaper.md)

### Sprint 4 — Architecture Migration (2–4 weeks, High Risk)
These are the highest-complexity items. Sequence as a dedicated sprint with
full regression testing.

13. **A1/A2/A3** + **B2**: Migrate chelper steppersync API + mcu.py restoration
    — see [chelper-steppersync.md](adaptations/chelper-steppersync.md),
       [mcu-restart-helper.md](adaptations/mcu-restart-helper.md)
14. **B3** + **C32** + **C8**: Migrate toolhead to minimum_cruise_ratio +
    MotionQueuing + restore output_pin
    — see [toolhead-motion-queuing.md](adaptations/toolhead-motion-queuing.md),
       [motion-queuing.md](adaptations/motion-queuing.md),
       [output-pin-gcode-request-queue.md](adaptations/output-pin-gcode-request-queue.md)

---

## Remaining Fork Surface — Tier 3 & 4 Summary

### What Must Stay Divergent Indefinitely

The 51 Tier 4 items represent the irreducible fork surface. They fall into
six categories:

**1. Power-Loss Recovery (PLR) System** (C1, B6, B18, D22, F7)  
`virtual_sdcard.py` PLR engine + `queuefile.py` atomic I/O + `stepper.py`
PLR fields + `power_loss_check.py` coordinator + `src/power_loss_check.c`
MCU flash storage. This is the most extensive fork addition. No upstream
equivalent exists or is planned. Tightly coupled to `/home/lava/` paths.
**Will require permanent maintenance.**

**2. Filament System** (D1–D6)  
6 modules covering filament presence detection, motorised feeding, tangle
detection, NFC-based material identification, and multi-slot routing protocol.
Entirely U1-specific. No upstream equivalent.
**Will require permanent maintenance.**

**3. Hardware Support** (F1–F7, G1–G2, B9, B10)  
AT32F403A/AT32F415RC MCU firmware, HAL libraries, inductance coil firmware,
serialhdl/pins AT32 adaptations. Until Artery Technology AT32 support is
contributed to upstream Klipper (no current upstream plan), these must remain.
**Will require permanent maintenance.**

**4. Inductive Probe Architecture** (D12–D13, C4)  
`inductance_coil.py`, `probe_inductance_coil.py`, `bed_mesh.py` integration.
The U1's per-head inductive probe is unique. Upstream has eddy current and
BLTouch probes but not frequency-measurement inductive probes.
**Will require permanent maintenance.**

**5. App Communication Layer** (D7–D11, D9, B15–B18)  
MQTT + JSON-RPC + machine state manager + print task config + exception system.
This is Snapmaker's proprietary app protocol. Not suitable for upstream.
**Will require permanent maintenance.**

**6. Multi-Extruder 4-Head Architecture** (E1, C9, B1, B8)  
4-extruder kinematics, park/pick G-codes, print_stats extensions, klippy.py
SCHED_FIFO, configfile paths. Partly overlaps with upstream IDEX but is a
distinct, more complex system.
**Will require permanent maintenance.**

### Tier 3 Summary — Layers That Can Shrink Over Time

The 23 Tier 3 items are cases where the fork maintains a layer on top of
upstream functionality. These do not need to be maintained in isolation but
will need to be refreshed whenever upstream changes the underlying code:

- **`gcode.py`** (B4): Coded error IDs on top of upstream Coord — shrinks if
  exception system is ever contributed to upstream.
- **`resonance_tester.py`** (C5): 2D-only + `SM_FAST_SHAPER_CALIBRATE` —
  the 2D simplification could be replaced by a config option upstream.
- **Kinematics minor changes** (E2–E13): The Tier 3 (not Tier 2) kinematics
  items are those with genuine U1-specific behaviour on top of snapshot drift.
  After the Coord/API migration (Adapt E3–E13), these will collapse to just
  `idex_modes.py` (E2).
- **`msgproto.py`, `queuelogger.py`, `mathutil.py`** (B12–B14): Cosmetic.
  Should converge with upstream over time as other migrations proceed.
- **Config divergences** (H2): Minor; expected to drift as upstream adds
  example configs.

**Long-term maintenance forecast:** After completing all Sprint 1–3 items
(low-to-medium risk), the Tier 3 surface reduces to approximately 8 files
(gcode.py, resonance_tester.py, idex_modes.py, 5 cosmetic core files).
The Tier 4 surface of ~51 items is permanent by design — it represents the
reason this fork exists.
