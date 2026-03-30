# Python ↔ C Cross-Reference: AT32 Changes

This document reconciles the C-layer AT32 HAL findings against the
Python-side host changes, establishing exactly where the two layers
interact and confirming that the Klipper command protocol itself is
unchanged.

---

## 1. Protocol Compatibility Summary

The AT32 C changes are **entirely at the HAL level**. The MCU command
protocol—message encoding, framing, CRC, and command registration via
`DECL_COMMAND`—is identical to upstream Klipper.

| Aspect | Status |
|--------|--------|
| Standard MCU commands (`config_stepper`, `stepper_queue`, `set_digital_out`, …) | **Unchanged** — work identically |
| Clock synchronization | **Unchanged** — `CLOCK_FREQ` (240 MHz / 144 MHz) reported correctly via `DECL_CONSTANT` |
| Python host awareness of AT32 | **Not required** for basic operation; `seconds_to_clock()` handles any frequency |
| 2-byte message IDs (commit `589bd64c`) | Upstream Klipper change, not AT32-specific |

**Bottom line:** the Python host code does not need to know it is talking
to AT32 hardware for any standard Klipper operation.

---

## 2. New MCU Commands Table

Two new C modules register commands that are consumed by corresponding
Python extras.

### 2.1 Inductance Coil (`src/stm32/inductance_coil.c`)

| Direction | Name | Purpose |
|-----------|------|---------|
| Host → MCU | `inductance_coil_config` | Configure sensor (cal_mode, capture_over_cnt, freq_cal_cycle, cal_time_out, trigger_mode, trigger_invert, trg_freq_ht, trg_freq_lt, cal_window_size) |
| Host → MCU | `query_inductance_coil` | Start / stop frequency capture |
| Host → MCU | `virtual_gpio_trigger` | Fire virtual GPIO (probing) |
| Host → MCU | `virtual_gpio_trigger_with_timer` | Timed virtual GPIO trigger |
| Host → MCU | `query_inductance_coil_status` | Poll sensor state |
| Host → MCU | `query_inductance_coil_config_info` | Read back active configuration |
| MCU → Host | `inductance_coil_info` | Config readback response |
| MCU → Host | *(bulk sensor data)* | Frequency samples via `sensor_bulk.h` framework |

### 2.2 Power Loss Check (`src/stm32/power_loss_check.c`)

| Direction | Name | Purpose |
|-----------|------|---------|
| Host → MCU | `config_power_loss_check` | Configure OID, clock, trigger timing, duty thresholds |
| Host → MCU | `enable_power_loss` | Arm / disarm detection |
| Host → MCU | `query_power_loss_stepper_info` | Read saved stepper positions by type index |
| Host → MCU | `query_power_loss_flash_valid` | Check whether flash-stored recovery data is valid |
| Host → MCU | `query_power_loss_status` | Poll current detection state |
| MCU → Host | `power_loss_stepper_info_result` | Stepper position readback |
| MCU → Host | `power_loss_flash_valid` | Flash validity response |
| MCU → Host | `power_loss_status` | Current detection state |
| MCU → Host | `report_power_loss_status` | Asynchronous loss event report |

Flash storage addresses (defined in C):

| Chip | Slot A | Slot B |
|------|--------|--------|
| AT32F415 | `0x0801F800` | `0x0801FC00` |
| AT32F403A | `0x080FF000` | `0x080FF800` |

---

## 3. Python–C Command Mapping

### 3.1 Inductance Coil

```
klippy/extras/inductance_coil.py
        │
        │  _build_config()
        │    mcu.lookup_command("inductance_coil_config oid=%c ...")
        │    mcu.lookup_command("query_inductance_coil oid=%c ...")
        │    ...
        │
        ▼
src/stm32/inductance_coil.c
        DECL_COMMAND(command_inductance_coil_config, ...)
        DECL_COMMAND(command_query_inductance_coil, ...)
```

- **Python → C parameter flow:**
  `freq_cal_cycle` defaults to `0.001 s` (1 ms). Converted to MCU ticks
  via `seconds_to_clock()`: 240 000 ticks at 240 MHz, 144 000 ticks at
  144 MHz (the actual sensor clock per the PA0 constraint). The
  conversion is automatic and frequency-agnostic.

- **Bulk sensor data** follows the standard `sensor_bulk.h` pattern;
  Python reads samples with the generic bulk-sensor helper.

- **Hardware constraint** (Python line 371): *"Currently only supports
  AT32415 PA0"* — the timer-capture hardware used for frequency
  measurement is specific to this pin/chip.

### 3.2 Power Loss Check

```
klippy/extras/power_loss_check.py
        │
        │  Sends config with oid, clock, trigger timing, duty thresholds
        │
        ▼
src/stm32/power_loss_check.c
        DECL_COMMAND(command_config_power_loss_check, ...)
        DECL_COMMAND(command_enable_power_loss, ...)
```

- **Trigger timing:** default `0.0109 s × 1e6 = 10 900 µs`, sent as an
  integer parameter. The C side converts to ticks using
  `CONFIG_CLOCK_FREQ`.

- **Stepper position tracking:** `stepper.py` defines the list
  `power_loss_need_save_steppers = ['stepper_x', 'stepper_y',
  'stepper_z', 'extruder']`, assigning type codes 0–3. These indices
  are used in `query_power_loss_stepper_info` requests. The C side
  stores positions indexed by the same codes — a clean, stable
  interface.

---

## 4. Workaround Analysis

| Concern | Workaround Needed? | Explanation |
|---------|--------------------|-------------|
| Clock frequency mismatch | **No** | `seconds_to_clock()` uses `CLOCK_FREQ` generically. No hard-coded 72 MHz assumptions found anywhere in the Python layer. |
| Inductance coil tick conversion | **No** | `freq_cal_cycle` is expressed in seconds; tick conversion happens automatically at whatever `CLOCK_FREQ` the MCU reports. |
| Power loss trigger timing | **No** | Raw time value sent to MCU; tick conversion done in C using `CONFIG_CLOCK_FREQ`. |
| Stepper position indexing | **No** | Clean type-code interface (0–3) shared between Python and C. No MCU-specific branching. |
| USB product identification | **No** | `USB_PRODUCT_SUFFIX` (added via `src/Kconfig`, consumed in `src/generic/usb_cdc.c`) is invisible to `klippy/`; it exists for host-level device enumeration only. |

**No timing workarounds, clock hacks, or AT32-conditional branches exist
in the Python host code.** The abstraction boundary is clean.

---

## 5. Feature Classification

### 5.1 AT32-Specific Features

These features depend on AT32 hardware capabilities and have matching
C implementations:

| Python Extra | C Counterpart | Why AT32-Specific |
|-------------|--------------|-------------------|
| `inductance_coil.py` | `inductance_coil.c` | Uses AT32 timer-capture for frequency measurement |
| `power_loss_check.py` | `power_loss_check.c` | Uses AT32 GPIO + timer for voltage monitoring; AT32 flash for persistent storage |
| `probe_inductance_coil.py` | *(uses `inductance_coil.py`)* | Probe logic built on AT32-specific sensor |
| `virtual_sdcard.py` (mods) | *(uses `power_loss_check.py`)* | Power-loss recovery integration |
| `stepper.py` (mods) | `stepper.c` (mods) | `type` / `index` fields for power-loss position tracking |
| `extruder.py` (mods) | *(uses `inductance_coil.py`)* | Binds extruder to inductance-coil probe |
| `heater_fan.py` (mods) | *(none — pure Python)* | Pauses fan during inductive probing to avoid EMI |

### 5.2 Generic Features (Not AT32-Specific)

These Python changes use only standard Klipper MCU commands and would
work on any MCU platform. They are in this fork because they are
Snapmaker U1 features, not because they require AT32:

| Module | Nature of Change |
|--------|-----------------|
| `bed_mesh.py` | Enhanced mesh features |
| `exclude_object.py` | Object exclusion improvements |
| `gcode_move.py` | Movement command extensions |
| `defect_detection.py` | Print defect detection (pure Python / camera) |
| `flow_calibrator.py` | Flow calibration routines |
| Other `klippy/extras/` additions | Various Snapmaker-specific UX features |

---

## 6. Confirmed Unchanged Protocol Elements

The following protocol elements have been verified as identical to
upstream Klipper:

| Element | Verification |
|---------|-------------|
| **Message framing** | Header byte, length field, trailing CRC — no changes in `src/generic/serial_irq.c` or `klippy/serialhdl.py` |
| **Command registration** | `DECL_COMMAND` and `DECL_CONSTANT` macros used identically |
| **Response formatting** | `sendf()` calls follow upstream conventions |
| **Bulk sensor data** | `sensor_bulk.h` / `sensor_bulk.c` framework used without modification |
| **Clock synchronization** | `uptime` / `clock` exchange unchanged; `CLOCK_FREQ` advertised via `DECL_CONSTANT` |
| **Config / init flow** | `identify`, `config`, `finalize_config` sequence unchanged |
| **2-byte message IDs** | Present (commit `589bd64c`) but this is an upstream Klipper change, not AT32-specific |

---

## 7. Cross-Layer Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Host (klippy/)                     │
│                                                             │
│  inductance_coil.py ──┐                                     │
│  probe_inductance_coil.py ─┤  mcu.lookup_command()          │
│  power_loss_check.py ─┤  mcu.lookup_query_command()         │
│  stepper.py (mods) ───┤  seconds_to_clock(CLOCK_FREQ)       │
│  virtual_sdcard.py ───┘                                     │
│                                                             │
│  bed_mesh.py, gcode_move.py, ...  ← standard MCU commands   │
├─────────────────────── serial protocol ─────────────────────┤
│         (unchanged: framing, CRC, command IDs)              │
├─────────────────────────────────────────────────────────────┤
│                   C Firmware (src/)                          │
│                                                             │
│  ┌─── AT32-specific ───────────────────────────────────┐    │
│  │  stm32/inductance_coil.c  — timer capture, ADC      │    │
│  │  stm32/power_loss_check.c — GPIO, timer, flash      │    │
│  │  stm32/at32f415.c / at32f403a.c — HAL setup         │    │
│  │  stm32/stm32f4_adc.c (AT32 ADC support)             │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─── Generic (unchanged) ─────────────────────────────┐    │
│  │  generic/serial_irq.c  — message framing            │    │
│  │  command.c             — DECL_COMMAND dispatch       │    │
│  │  stepper.c             — step generation             │    │
│  │  sensor_bulk.c         — bulk data framework         │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

*Generated from verified cross-layer analysis of the u1-klipper fork.*
